"""CLI entry-point for lyrics-mcp.

Usage:
    lyrics-mcp             — start the MCP server (stdio transport)
    lyrics-mcp --sse       — start the MCP server (SSE / HTTP transport)

The transport can also be set via the MCP_TRANSPORT environment variable
(values: "stdio", "sse", "streamable-http").  The --sse flag takes precedence.
"""
from __future__ import annotations

import logging
import os
import sys


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    transport: str = "stdio"
    if "--sse" in sys.argv:
        transport = "sse"
    else:
        transport = os.environ.get("MCP_TRANSPORT", "stdio")

    from .server import mcp

    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
