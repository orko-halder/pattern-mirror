"""
Pattern Mirror — tool definitions and handlers.

Tools Claude can call during analysis. Each tool has:
- A schema (what Claude sees and uses to decide when/how to call it)
- A handler (what actually runs when Claude calls it)
"""

import json
from pathlib import Path

FRAMEWORKS_PATH = Path(__file__).parent / "frameworks.json"


def _load_frameworks() -> dict:
    with open(FRAMEWORKS_PATH) as f:
        return json.load(f)


def handle_lookup_framework(framework_key: str) -> str:
    """Look up a psychological framework by key. Returns formatted string for Claude."""
    frameworks = _load_frameworks()

    if framework_key not in frameworks:
        # Return available keys so Claude can retry with the right one
        available = ", ".join(frameworks.keys())
        return f"Framework '{framework_key}' not found. Available frameworks: {available}"

    fw = frameworks[framework_key]
    return (
        f"Framework: {fw['name']} ({fw['tradition']})\n"
        f"Description: {fw['description']}\n"
        f"Protocol note: {fw['protocol_note']}\n"
        f"Pattern tags: {', '.join(fw['pattern_tags'])}"
    )


# ── Tool schema — what Claude sees ───────────────────────────
LOOKUP_FRAMEWORK_TOOL = {
    "name": "lookup_framework",
    "description": (
        "Look up a psychological framework from the Pattern Mirror database. "
        "Call this when the pattern you are identifying maps to a known framework "
        "and the framework's protocol note would improve the specificity of your intervention. "
        "Do not call this for general knowledge you already have — only call it when "
        "the database entry would add a protocol note or tradition-specific nuance "
        "that you would not otherwise include."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "framework_key": {
                "type": "string",
                "description": (
                    "The framework key to look up. Available keys: "
                    "jungian_shadow, attachment_anxious, attachment_avoidant, "
                    "fawn_response, inner_critic, cognitive_distortion_catastrophising, "
                    "core_belief_unworthiness, identity_foreclosure, hypervigilance"
                )
            }
        },
        "required": ["framework_key"]
    }
}


# ── Tool dispatcher ───────────────────────────────────────────
def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Route a tool call from Claude to the correct handler."""
    if tool_name == "lookup_framework":
        return handle_lookup_framework(tool_input["framework_key"])
    return f"Unknown tool: {tool_name}"
