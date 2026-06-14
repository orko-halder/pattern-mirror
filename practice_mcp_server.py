"""
Practice MCP server — text tools.

A minimal standalone MCP server with two tools:
  - word_count:    count words, sentences, paragraphs in a text
  - reading_time:  estimate reading time at a given words-per-minute

Purpose: learn the MCP SDK pattern (server, tool decorator, stdio transport)
before wiring it to the Pattern Mirror pipeline.

Run:  python practice_mcp_server.py
Test: echo '{"method":"tools/list","id":1}' | python practice_mcp_server.py
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# ── Server instance ──────────────────────────────────────────
app = Server("text-tools")


# ── Tool: word_count ─────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[Tool]:
    """Declare the tools this server exposes."""
    return [
        Tool(
            name="word_count",
            description=(
                "Count words, sentences, and paragraphs in a piece of text. "
                "Returns a summary with counts and a character total."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to analyse.",
                    }
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="reading_time",
            description=(
                "Estimate how long it takes to read a piece of text. "
                "Default reading speed is 200 words per minute."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to estimate.",
                    },
                    "wpm": {
                        "type": "integer",
                        "description": "Reading speed in words per minute. Default 200.",
                        "default": 200,
                    },
                },
                "required": ["text"],
            },
        ),
    ]


# ── Tool handlers ─────────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to the right handler."""
    if name == "word_count":
        return _word_count(arguments["text"])
    if name == "reading_time":
        return _reading_time(arguments["text"], arguments.get("wpm", 200))
    raise ValueError(f"Unknown tool: {name}")


def _word_count(text: str) -> list[TextContent]:
    words = len(text.split())
    sentences = text.count(".") + text.count("!") + text.count("?")
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    chars = len(text)
    result = (
        f"Words: {words}\n"
        f"Sentences: {sentences}\n"
        f"Paragraphs: {paragraphs}\n"
        f"Characters: {chars}"
    )
    return [TextContent(type="text", text=result)]


def _reading_time(text: str, wpm: int) -> list[TextContent]:
    words = len(text.split())
    minutes = words / wpm
    if minutes < 1:
        time_str = f"under 1 minute ({int(minutes * 60)} seconds)"
    else:
        time_str = f"{minutes:.1f} minutes"
    result = f"Estimated reading time: {time_str}\n({words} words at {wpm} wpm)"
    return [TextContent(type="text", text=result)]


# ── Entry point ───────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
