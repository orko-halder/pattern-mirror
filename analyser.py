"""
Pattern Mirror — analysis pipeline.

Sends validated answers to Claude and returns the pattern analysis.
Two modes: structured JSON (default) and streaming text (kept for future toggle).
"""

from anthropic import Anthropic
from prompts import SYSTEM_PROMPT, ANALYSIS_TOOL
from validator import format_answers
from tools import LOOKUP_FRAMEWORK_TOOL, WEB_SEARCH_TOOL, handle_tool_call


def analyse_structured(client: Anthropic, answers: list[dict]) -> tuple[dict, str, list[dict]]:
    """Send answers to Claude, get back structured JSON.
    Returns (data_dict, formatted_string, citations).

    Tool use loop:
    1. Claude may call lookup_framework or web_search before producing the final analysis
    2. We execute the tool and send the result back
    3. Claude continues until it calls pattern_analysis to return the structured output
    """
    user_content = format_answers(answers)
    messages = [{"role": "user", "content": user_content}]
    tools = [LOOKUP_FRAMEWORK_TOOL, WEB_SEARCH_TOOL, ANALYSIS_TOOL]
    citations = []
    force_final = False

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            tool_choice={"type": "tool", "name": "pattern_analysis"} if force_final else {"type": "auto"},
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            break

        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            break

        # If Claude called pattern_analysis — we're done
        for block in tool_calls:
            if block.name == "pattern_analysis":
                formatted = format_structured_output(block.input)
                return block.input, formatted, citations

        # Claude called a lookup tool — execute it, collect citations, add to history
        for b in tool_calls:
            print(f"\n🔧 Tool called: {b.name} | input: {b.input}")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_calls:
            envelope = handle_tool_call(block.name, block.input)
            citations.extend(envelope["metadata"].get("citations", []))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": envelope["content"]
            })

        messages.append({"role": "user", "content": tool_results})
        force_final = True

    return {}, "", []


def format_structured_output(data: dict) -> str:
    """Render a structured analysis dict as readable CLI output."""
    lines = []

    core = data.get("core_pattern", {})
    lines.append("**Core Pattern**")
    lines.append(core.get("name", ""))
    lines.append(core.get("plain_summary", ""))
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

    lines.append("\n**What It's Protecting You From**")
    lines.append(data.get("payoff", ""))

    protocol = data.get("protocol", {})
    lines.append("\n**The Protocol**")
    lines.append(f"Detection: {protocol.get('detection_trigger', '')}")
    for i, step in enumerate(protocol.get("steps", []), 1):
        lines.append(f"  {i}. {step}")
    lines.append(f"If you can't stop right now: {protocol.get('fallback_mid_activation', '')}")
    lines.append(f"If you're completely overwhelmed: {protocol.get('fallback_shutdown', '')}")
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
        max_tokens=2048,
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
