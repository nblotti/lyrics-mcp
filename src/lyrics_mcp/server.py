"""MCP server that generates song lyrics from a description using LangChain + Gemini."""
from __future__ import annotations

import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp.server.fastmcp import FastMCP

log = logging.getLogger("lyrics_mcp")

mcp = FastMCP(
    "lyrics-mcp",
    instructions=(
        "Song lyrics generator.  Provide a description of an existing song "
        "(title, artist, mood, theme, genre, etc.) and receive original lyrics "
        "inspired by that description."
    ),
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_SYSTEM_PROMPT = """\
You are a talented songwriter and lyricist.  The user will describe an existing \
song — its title, artist, mood, theme, genre, or any combination of these.  \
Your job is to compose **original** lyrics inspired by that description.

Guidelines:
- Write complete lyrics with verses, a chorus, and optionally a bridge.
- Label each section (e.g. [Verse 1], [Chorus], [Bridge]).
- Match the mood, theme, and genre described.
- The lyrics must be **original** — do NOT reproduce copyrighted lyrics.
- Keep it concise: aim for 3-4 minutes of singing time.
"""


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=_GEMINI_MODEL,
        temperature=0.9,
    )


@mcp.tool(name="lyrics.generate")
def generate_lyrics(description: str) -> str:
    """Generate original song lyrics inspired by the given description.

    Args:
        description: A description of the song to draw inspiration from.
                     Can include title, artist, mood, theme, genre, tempo,
                     or any other musical characteristics.

    Returns:
        Original lyrics with labeled sections (Verse, Chorus, Bridge, etc.).
    """
    log.info("Generating lyrics for: %s", description[:120])
    llm = _get_llm()
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=description),
    ]
    response = llm.invoke(messages)
    return response.content
