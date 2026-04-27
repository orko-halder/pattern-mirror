"""
Pattern Mirror — tool definitions and handlers.

Every tool returns a standard envelope:
{
    "status":   "success" | "error",
    "content":  str,        # text Claude reads
    "metadata": dict        # tool-specific extras — citations, keys, etc.
                            # Claude never sees this, only the pipeline does
}

Adding a new tool: write a handler that returns an envelope, add a schema constant,
register it in handle_tool_call.
"""

import os
import json
from pathlib import Path
from tavily import TavilyClient

FRAMEWORKS_PATH = Path(__file__).parent / "frameworks.json"


# ── Envelope builder ─────────────────────────────────────────
def _ok(content: str, **metadata) -> dict:
    return {"status": "success", "content": content, "metadata": metadata}

def _err(content: str) -> dict:
    return {"status": "error", "content": content, "metadata": {}}


# ── Handlers ─────────────────────────────────────────────────
def handle_lookup_framework(framework_key: str) -> dict:
    """Look up a psychological framework by key."""
    with open(FRAMEWORKS_PATH) as f:
        frameworks = json.load(f)

    if framework_key not in frameworks:
        available = ", ".join(frameworks.keys())
        return _err(f"Framework '{framework_key}' not found. Available: {available}")

    fw = frameworks[framework_key]
    content = (
        f"Framework: {fw['name']} ({fw['tradition']})\n"
        f"Description: {fw['description']}\n"
        f"Protocol note: {fw['protocol_note']}\n"
        f"Pattern tags: {', '.join(fw['pattern_tags'])}"
    )
    return _ok(content, framework_name=fw["name"], tradition=fw["tradition"])


ALLOWED_DOMAINS = [
    "psychologytoday.com",
    "apa.org",
    "simplypsychology.org",
    "ncbi.nlm.nih.gov",
]

def handle_web_search(query: str) -> dict:
    """Search pre-approved psychology sources only."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return _err("Web search unavailable — TAVILY_API_KEY not set.")

    try:
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(
            query=query,
            include_domains=ALLOWED_DOMAINS,
            max_results=3,
            search_depth="basic"
        )

        results = response.get("results", [])
        if not results:
            return _err(f"No results found for '{query}' on approved sources.")

        text_blocks = []
        for r in results:
            text_blocks.append(
                f"Source: {r.get('url', '')}\n"
                f"Title: {r.get('title', '')}\n"
                f"Summary: {r.get('content', '')[:400]}"
            )

        content = "\n\n---\n\n".join(text_blocks)
        citations = [{"title": r.get("title", ""), "url": r.get("url", "")} for r in results]

        print(f"\n🌐 Web search results:\n{content}\n")
        return _ok(content, citations=citations)

    except Exception as e:
        return _err(f"Web search failed: {str(e)}")


# ── Tool dispatcher ───────────────────────────────────────────
def handle_tool_call(tool_name: str, tool_input: dict) -> dict:
    """Route a tool call to the correct handler. Always returns a standard envelope."""
    if tool_name == "lookup_framework":
        return handle_lookup_framework(tool_input["framework_key"])
    if tool_name == "web_search":
        return handle_web_search(tool_input["query"])
    return _err(f"Unknown tool: {tool_name}")


# ── Tool schemas — what Claude sees ──────────────────────────
LOOKUP_FRAMEWORK_TOOL = {
    "name": "lookup_framework",
    "description": (
        "Look up a psychological framework from the Pattern Mirror database. "
        "Only call this when the pattern maps EXACTLY to one of the available keys — "
        "do not call it for partial matches or related concepts. "
        "If the specific named concept (e.g. rejection sensitive dysphoria, alexithymia, "
        "C-PTSD emotional flashbacks) is not in the keys list, use web_search instead."
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

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search trusted psychology and mental health sources for information about "
        "a specific named clinical concept or condition. Use this when the pattern "
        "involves a concept not in the lookup_framework keys list — for example: "
        "rejection sensitive dysphoria, alexithymia, C-PTSD emotional flashbacks, "
        "pathological demand avoidance, or other specific named conditions. "
        "Searches are restricted to: psychologytoday.com, apa.org, "
        "simplypsychology.org, ncbi.nlm.nih.gov. Use the specific clinical name as the query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Specific search query — e.g. 'rejection sensitive dysphoria ADHD protocol' not 'emotional sensitivity'."
            }
        },
        "required": ["query"]
    }
}
