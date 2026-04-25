"""
Pattern Mirror — analysis pipeline.

Sends validated answers to Claude and returns the pattern analysis.
Two modes: structured JSON (default) and streaming text (kept for future toggle).
"""

from anthropic import Anthropic
from prompts import SYSTEM_PROMPT, ANALYSIS_TOOL
from validator import format_answers


def analyse_structured(client: Anthropic, answers: list[dict]) -> tuple[dict, str]:
    """Send answers to Claude, get back structured JSON. Returns (data_dict, formatted_string)."""
    user_content = format_answers(answers)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "pattern_analysis"},
        messages=[{"role": "user", "content": user_content}],
    )

    # Extract the tool_use block — it's the only block when tool_choice forces it
    analysis_data = {}
    for block in response.content:
        if block.type == "tool_use":
            analysis_data = block.input
            break

    formatted = format_structured_output(analysis_data)
    return analysis_data, formatted


def format_structured_output(data: dict) -> str:
    """Render a structured analysis dict as readable CLI output."""
    lines = []

    core = data.get("core_pattern", {})
    lines.append("**Core Pattern**")
    lines.append(core.get("name", ""))
    lines.append(core.get("description", ""))

    secondary = data.get("secondary_pattern")
    if secondary:
        lines.append("\n**Secondary Pattern**")
        lines.append(secondary.get("name", ""))
        lines.append(secondary.get("description", ""))

    lines.append("\n**Evidence**")
    for quote in data.get("evidence", []):
        lines.append(f'  "{quote}"')

    lines.append("\n**Where It Shows Up**")
    lines.append("  " + ", ".join(data.get("domains", [])))

    lines.append("\n**The Payoff**")
    lines.append(data.get("payoff", ""))

    protocol = data.get("protocol", {})
    lines.append("\n**The Protocol**")
    lines.append(f"Detection: {protocol.get('detection_trigger', '')}")
    for i, step in enumerate(protocol.get("steps", []), 1):
        lines.append(f"  {i}. {step}")
    fc = protocol.get("failure_condition", {})
    if isinstance(fc, dict):
        lines.append(f"If it goes wrong: {fc.get('if_wrong', '')}")
        lines.append(f"If it goes right: {fc.get('if_right', '')}")
    else:
        lines.append(f"Failure condition: {fc}")

    return "\n".join(lines)


def analyse(client: Anthropic, answers: list[dict]) -> str:
    """Send answers to Claude and stream the pattern analysis. Returns full output.

    Kept for the Week 3 streaming toggle in Streamlit.
    """
    user_content = format_answers(answers)
    full_output = []

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_content}
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_output.append(text)

    print("\n")
    return "".join(full_output)
