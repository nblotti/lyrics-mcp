"""MCP server that generates instrumental music using Google Lyria RealTime."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import uuid
import wave
from pathlib import Path
from tempfile import gettempdir

from google import genai
from google.genai import types
from mcp.server.fastmcp import FastMCP
from minio import Minio

log = logging.getLogger("music_mcp")

SAMPLE_RATE = 48_000
CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit PCM
BYTES_PER_SECOND = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio.nblotti.org")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "music-mcp")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "true").lower() == "true"

mcp = FastMCP(
    "music-mcp",
    instructions=(
        "Instrumental music generator powered by Google Lyria RealTime. "
        "Describe the music you want — genre, mood, instruments, style — "
        "and receive a downloadable link to the generated WAV audio file."
    ),
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)

_OUTPUT_DIR = Path(os.environ.get("MUSIC_OUTPUT_DIR", gettempdir())) / "music_mcp"


def _write_wav(pcm_data: bytes, filepath: Path) -> None:
    """Write raw PCM data to a WAV file."""
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)


def _upload_to_minio(filepath: Path) -> str:
    """Upload a file to MinIO and return the public URL."""
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)

    object_name = filepath.name
    file_size = filepath.stat().st_size
    with open(filepath, "rb") as f:
        client.put_object(
            MINIO_BUCKET,
            object_name,
            f,
            length=file_size,
            content_type="audio/wav",
        )

    scheme = "https" if MINIO_SECURE else "http"
    url = f"{scheme}://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
    log.info("Uploaded to MinIO: %s", url)
    return url


@mcp.tool(name="music.generate")
async def generate_music(
    description: str,
    duration_seconds: int = 30,
    bpm: int | None = None,
    temperature: float = 1.0,
) -> str:
    """Generate instrumental music from a text description using Lyria RealTime.

    Args:
        description: Text describing the desired music — genre, mood, instruments,
                     style, tempo feel, etc.
                     Examples: "chill lo-fi hip hop with warm piano and vinyl crackle",
                     "epic orchestral score with dramatic strings",
                     "minimal techno with deep bass and sparse percussion".
        duration_seconds: How many seconds of audio to generate (1–120, default 30).
        bpm: Beats per minute (60–200). If omitted the model decides.
        temperature: Creativity / randomness (0.0–3.0, default 1.0). Higher = more varied.

    Returns:
        Path to the generated WAV file with basic metadata.
    """
    duration_seconds = max(1, min(120, duration_seconds))
    log.info("Generating %ds of music for: %s", duration_seconds, description[:120])

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = genai.Client(http_options={"api_version": "v1alpha"})
    audio_buffer = bytearray()
    target_bytes = duration_seconds * BYTES_PER_SECOND

    async with client.aio.live.music.connect(
        model="models/lyria-realtime-exp",
    ) as session:
        await session.set_weighted_prompts(
            prompts=[types.WeightedPrompt(text=description, weight=1.0)]
        )

        config_kwargs: dict = {"temperature": temperature}
        if bpm is not None:
            config_kwargs["bpm"] = max(60, min(200, bpm))

        await session.set_music_generation_config(
            config=types.LiveMusicGenerationConfig(**config_kwargs),
        )

        await session.play()

        try:
            async with asyncio.timeout(duration_seconds + 5):
                async for message in session.receive():
                    if message.filtered_prompt:
                        log.warning("Prompt was filtered: %s", message.filtered_prompt)
                        await session.stop()
                        return (
                            "Error: your prompt was blocked by the safety filter. "
                            "Avoid referencing real artist names, copyrighted song "
                            "titles, or trademarked terms. Describe the musical style "
                            "instead (e.g. genre, mood, instruments, tempo)."
                        )
                    if not message.server_content or not message.server_content.audio_chunks:
                        continue
                    for chunk in message.server_content.audio_chunks:
                        data = chunk.data
                        if isinstance(data, str):
                            data = base64.b64decode(data)
                        audio_buffer.extend(data)
                    if len(audio_buffer) >= target_bytes:
                        break
        except TimeoutError:
            if not audio_buffer:
                log.error("No audio received — prompt may have been silently filtered")
                return (
                    "Error: no audio was generated. The prompt may have been "
                    "silently filtered. Avoid referencing real artist names or "
                    "song titles. Describe the musical style instead."
                )
            log.warning("Timed out after collecting %d bytes", len(audio_buffer))

        await session.stop()

    pcm_data = bytes(audio_buffer[:target_bytes])

    filename = f"music_{uuid.uuid4().hex[:8]}.wav"
    filepath = _OUTPUT_DIR / filename
    _write_wav(pcm_data, filepath)

    actual_duration = len(pcm_data) / BYTES_PER_SECOND
    size_kb = (len(pcm_data) + 44) / 1024  # +44 for WAV header
    log.info("Saved %s (%.1fs, %.0f KB)", filepath, actual_duration, size_kb)

    try:
        minio_url = _upload_to_minio(filepath)
        filepath.unlink(missing_ok=True)
    except Exception:
        log.exception("MinIO upload failed — returning local path as fallback")
        return (
            f"Generated music saved to: {filepath}\n"
            f"Duration: {actual_duration:.1f}s | "
            f"Format: WAV {SAMPLE_RATE // 1000}kHz stereo 16-bit | "
            f"Size: {size_kb:.0f} KB\n"
            f"Warning: MinIO upload failed; file is only available locally."
        )

    return (
        f"Download your music: {minio_url}\n"
        f"Duration: {actual_duration:.1f}s | "
        f"Format: WAV {SAMPLE_RATE // 1000}kHz stereo 16-bit | "
        f"Size: {size_kb:.0f} KB"
    )
