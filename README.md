# lyrics-mcp

MCP server that generates original song lyrics from a description using LangChain + Google Gemini.

## Setup

```bash
pip install -e .
```

Set your Gemini API key:

```bash
export GOOGLE_API_KEY="your-key-here"
```

## Usage

**stdio** (default):

```bash
lyrics-mcp
```

**SSE / HTTP**:

```bash
lyrics-mcp --sse
# or
MCP_TRANSPORT=sse lyrics-mcp
```

## Docker

```bash
docker build -t lyrics-mcp:latest .
docker run -p 8000:8000 -e GOOGLE_API_KEY="your-key" lyrics-mcp:latest
```

## Tool

### `lyrics.generate`

Generate original lyrics inspired by a song description.

**Input**: `description` — free-text description of a song (title, artist, mood, theme, genre, etc.)

**Output**: Original lyrics with labeled sections (Verse, Chorus, Bridge).
