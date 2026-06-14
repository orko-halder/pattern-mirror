"""
Test client for the Pattern Mirror MCP server.

Connects via stdio, lists tools, then calls analyse_reflection with
a set of sample answers. Prints the full result.

Run: python test_mcp_server.py
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],
)

SAMPLE_ANSWERS = [
    # Q1: Think of something that didn't go the way you wanted recently.
    # What did you tell yourself about why it happened?
    "A project I worked hard on got shelved. I told myself I should have seen it coming — "
    "I always overestimate how much people actually care about the work.",

    # Q2: Think of someone who's annoyed or frustrated you lately.
    # What did they do — and what went through your mind when they did it?
    "A colleague took credit for an idea I shared in a meeting. I thought — of course, "
    "that's what happens when you speak up. Better to stay quiet next time.",

    # Q3: Is there something about you that you'd prefer people didn't notice?
    # What do you do to make sure they don't — and what are you worried would happen if they did?
    "How much I second-guess myself. I talk confidently even when I'm unsure, "
    "and I'm worried that if people saw the doubt they'd stop trusting my judgment entirely.",

    # Q4: What's a feeling that makes you want to get busy or change the subject?
    # When did you last feel it?
    "Feeling overlooked. Last week in a team meeting where decisions got made without anyone "
    "asking my view, even on things I know well. I went straight to my task list afterwards.",

    # Q5: Finish this with the first thing that comes to mind:
    # 'I'm just not someone who...'
    "I'm just not someone who makes a fuss about things.",
]


async def main():
    print("Connecting to Pattern Mirror MCP server...")
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected\n")

            # List tools
            tools = await session.list_tools()
            print("🔧 Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}")
            print()

            # Call analyse_reflection
            print("🔍 Running analysis (this takes ~30 seconds)...\n")
            result = await session.call_tool(
                "analyse_reflection",
                {"answers": SAMPLE_ANSWERS, "extended_thinking": False},
            )

            print("=" * 60)
            for block in result.content:
                print(block.text)
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
