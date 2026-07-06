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
    # Q1: Tell me about a recent piece of work that went really well — something you're
    # genuinely proud of. What made it successful, and who knows about the impact you had?
    "I redesigned the onboarding flow for our app — it dropped drop-off by 30%. "
    "It worked because I got deep into the analytics before anyone else noticed the problem. "
    "My manager knows I built it but I don't think the wider team really knows it was my work.",

    # Q2: Think of a moment at work where you held back — didn't speak up in a meeting,
    # didn't push back on a decision, or let something go when you had a view.
    # What was going through your mind?
    "We were discussing the new feature roadmap and I could see an architectural issue "
    "that would cause problems later. I started to say something, then thought — "
    "they've been here longer than me, maybe I'm missing context. I said nothing. "
    "The issue came up three months later exactly as I'd expected.",

    # Q3: Is there something you've been meaning to go for at work — a promotion conversation,
    # a stretch project, a new responsibility — but haven't started yet?
    # What's in the way?
    "I've been thinking about asking for a lead role for about a year. "
    "I keep telling myself I need to demonstrate a bit more first — "
    "finish this project, get that feedback, build one more thing. "
    "There's always one more thing I need to prove before I feel ready.",

    # Q4: Think of a time you took on more than you should have. What made it hard to say no,
    # and what did you tell yourself about it at the time?
    "Last quarter I said yes to three parallel projects. I told myself I could manage it "
    "and that saying no would signal I wasn't committed. I burned out by week six. "
    "I still didn't ask for help — I just worked weekends until it was done.",

    # Q5: Finish this sentence with the first thing that comes to mind:
    # 'I'll be ready to [take that next step / put myself forward / speak up] when...'
    "I'll be ready to put myself forward for a lead role when I've proven I can handle "
    "the really complex stuff without needing any support.",
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
