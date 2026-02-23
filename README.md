# music-mcp

MCP server that generates instrumental music from a text description using [Google Lyria RealTime](https://ai.google.dev/gemini-api/docs/music-generation).

## Setup

```bash
pip install -e .
```

Set your Google API key:

```bash
export GOOGLE_API_KEY="your-key-here"
```

## Usage

**stdio** (default):

```bash
music-mcp
```

**SSE / HTTP**:

```bash
music-mcp --sse
# or
MCP_TRANSPORT=sse music-mcp
```

## Docker

```bash
docker build -t music-mcp:latest .
docker run -p 8000:8000 -e GOOGLE_API_KEY="your-key" music-mcp:latest
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | *(required)* | Google API key with Gemini access |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio`, `sse`, or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | Host to bind (SSE/HTTP) |
| `MCP_PORT` | `8000` | Port to bind (SSE/HTTP) |
| `MUSIC_OUTPUT_DIR` | system temp dir | Directory for generated WAV files |

## Tool

### `music.generate`

Generate instrumental music from a text description.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `description` | string | *(required)* | Genre, mood, instruments, style, etc. |
| `duration_seconds` | int | `30` | Duration in seconds (1–120) |
| `bpm` | int | *auto* | Beats per minute (60–200) |
| `temperature` | float | `1.0` | Creativity (0.0–3.0) |

**Output**: Path to a generated WAV file (48 kHz, stereo, 16-bit PCM).

**Example prompts:**
- `"chill lo-fi hip hop with warm piano and vinyl crackle"`
- `"epic orchestral score with dramatic strings and brass"`
- `"minimal techno with deep bass and sparse percussion"`
- `"acoustic folk with fingerpicked guitar and harmonica"`

> **Note:** Lyria RealTime generates **instrumental music only** — no vocals or sung lyrics.
