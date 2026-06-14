"""
Pattern Mirror — MCP server.

Exposes the pattern analysis pipeline as an MCP tool so any MCP-compatible
client (Claude Code, Claude Desktop, custom apps) can run an analysis without
going through the Streamlit UI.

Tools exposed:
  analyse_reflection — run the full pipeline on 5 reflection answers

Transport: stdio (spawned as a subprocess by the MCP client)

Run:  python mcp_server.py
Test: python test_mcp_server.py
"""

import asyncio
import os
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from validator import validate_answers
from analyser import analyse_structured, PipelineError
from middleware import pre_process, post_process
from config import SONNET_MODEL


# ── Load env + build Anthropic client once at startup ────────
load_dotenv()
_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── MCP server instance ──────────────────────────────────────
app = Server("pattern-mirror")


# ── Tool definitions ─────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyse_reflection",
            description=(
                "Run a full Pattern Mirror analysis on a set of reflection answers. "
                "Identifies unconscious psychological patterns, generates follow-up questions "
                "to confirm the pattern across life domains, and returns a structured analysis "
                "with a deployable protocol. "
                "Provide exactly 5 answers as a list of strings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 5,
                        "maxItems": 5,
                        "description": (
                            "Answers to the 5 reflection questions, in order. "
                            "Each answer should be at least a sentence."
                        ),
                    },
                    "extended_thinking": {
                        "type": "boolean",
                        "description": "Enable extended thinking on the analysis call. Slower but deeper. Default false.",
                        "default": False,
                    },
                },
                "required": ["answers"],
            },
        ),
    ]


# ── Tool handler ─────────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "analyse_reflection":
        return await _handle_analyse_reflection(arguments)
    raise ValueError(f"Unknown tool: {name}")


async def _handle_analyse_reflection(arguments: dict) -> list[TextContent]:
    """Run the full pipeline and return the analysis as structured text."""

    # Build the answers list in the format the pipeline expects
    raw_answers = arguments["answers"]
    extended_thinking = arguments.get("extended_thinking", False)

    answers = [
        {"question": f"Q{i}", "answer": ans.strip() or "[no answer given]"}
        for i, ans in enumerate(raw_answers, 1)
    ]

    # Pre-processing — deterministic checks, no Claude calls
    pre = pre_process(answers)
    if pre.blocked:
        error_text = "Pipeline blocked:\n" + "\n".join(pre.errors)
        return [TextContent(type="text", text=error_text)]

    warnings_text = ""
    if pre.warnings:
        warnings_text = "Warnings:\n" + "\n".join(pre.warnings) + "\n\n"

    # Validation — Haiku quality check
    errors = validate_answers(_client, answers)
    if errors:
        error_text = "Validation failed:\n" + "\n".join(errors)
        return [TextContent(type="text", text=error_text)]

    # Single-shot MCP pattern: run analysis on initial answers only.
    # Follow-up question generation is skipped — the interactive round-trip
    # doesn't map to a single tool call. Interactive follow-up is a v2 feature.
    try:
        result = analyse_structured(
            _client,
            answers,
            extended_thinking=extended_thinking,
        )
    except PipelineError as e:
        return [TextContent(type="text", text=f"Analysis failed: {e}")]

    if not result.data:
        return [TextContent(type="text", text="Analysis returned no data. Please try again.")]

    # Post-processing — cost log
    post = post_process(result.data, result.usage, SONNET_MODEL)

    # Format output as readable text
    output = warnings_text + _format_result(result, post)
    return [TextContent(type="text", text=output)]


def _format_result(result, post) -> str:
    """Render the analysis result as clean plain text for terminal MCP clients."""
    data = result.data
    lines = []

    def section(title: str) -> None:
        lines.append("")
        lines.append(title.upper())
        lines.append("─" * len(title))

    # ── Core pattern ──────────────────────────────────────────
    core = data.get("core_pattern", {})
    name = core.get("name", "Pattern")
    lines.append("=" * (len(name) + 4))
    lines.append(f"  {name}")
    lines.append("=" * (len(name) + 4))
    lines.append(core.get("plain_summary", ""))
    lines.append("")
    lines.append(core.get("description", ""))

    # ── Secondary pattern ─────────────────────────────────────
    secondary = data.get("secondary_pattern")
    if secondary:
        section(f"Secondary Pattern — {secondary.get('name', '')}")
        lines.append(secondary.get("description", ""))

    # ── Evidence ──────────────────────────────────────────────
    section("Evidence")
    for quote in data.get("evidence", []):
        lines.append(f'  "{quote}"')

    # ── Domains ───────────────────────────────────────────────
    section("Where It Shows Up")
    lines.append("  " + "  ·  ".join(data.get("domains", [])))

    # ── Payoff ────────────────────────────────────────────────
    section("What It's Protecting You From")
    lines.append(data.get("payoff", ""))

    # ── Protocol ──────────────────────────────────────────────
    protocol = data.get("protocol", {})
    section("Protocol")
    lines.append(f"Detection:  {protocol.get('detection_trigger', '')}")
    lines.append("")
    for i, step in enumerate(protocol.get("steps", []), 1):
        lines.append(f"  {i}. {step}")
    lines.append("")
    lines.append(f"If stuck mid-moment:  {protocol.get('fallback_mid_activation', '')}")
    lines.append(f"If overwhelmed:       {protocol.get('fallback_shutdown', '')}")

    fc = protocol.get("failure_condition", {})
    if isinstance(fc, dict):
        lines.append("")
        lines.append(f"If it goes wrong:  {fc.get('if_wrong', '')}")
        lines.append(f"If it goes right:  {fc.get('if_right', '')}")

    # ── Cross-domain verdict ───────────────────────────────────
    cross_domain = data.get("cross_domain_evidence", "")
    if cross_domain:
        lines.append("")
        lines.append(f"Cross-domain evidence: {cross_domain}")

    # ── Citations ─────────────────────────────────────────────
    if result.citations:
        section("Further Reading")
        for c in result.citations:
            lines.append(f"  {c['title']}")
            lines.append(f"  {c['url']}")
            lines.append("")

    # ── Cost ──────────────────────────────────────────────────
    lines.append("")
    lines.append(f"[ {post.cost_summary} ]")

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
