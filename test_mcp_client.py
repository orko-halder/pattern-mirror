"""
Minimal MCP test client.

Spawns the practice server as a subprocess, performs the initialization
handshake, then calls tools/list and tools/call to verify both work.

Run: python test_mcp_client.py
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = StdioServerParameters(
    command="python",
    args=["practice_mcp_server.py"],
)


async def main():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:

            # Handshake — required before any other request
            await session.initialize()
            print("✅ Connected and initialized\n")

            # List available tools
            tools = await session.list_tools()
            print("🔧 Tools available:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()

            # Call word_count
            result = await session.call_tool(
                "word_count",
                {"text": "Hello world. This is a test. How does it work?"},
            )
            print("📊 word_count result:")
            for block in result.content:
                print(f"  {block.text}")
            print()

            # Call reading_time
            result = await session.call_tool(
                "reading_time",
                {"text": "Hello world. This is a test. How does it work?", "wpm": 200},
            )
            print("⏱️  reading_time result:")
            for block in result.content:
                print(f"  {block.text}")


if __name__ == "__main__":
    asyncio.run(main())
