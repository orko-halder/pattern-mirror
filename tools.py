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
from tavily import TavilyClient

import rag


# ── Envelope builder ─────────────────────────────────────────
def _ok(content: str, **metadata) -> dict:
    return {"status": "success", "content": content, "metadata": metadata}

def _err(content: str) -> dict:
    return {"status": "error", "content": content, "metadata": {}}


# ── Handlers ─────────────────────────────────────────────────
def handle_lookup_framework(query: str) -> dict:
    """Semantic search for the most relevant psychological framework(s)."""
    try:
        matches = rag.search_frameworks(query, n_results=2)
    except Exception as e:
        return _err(f"Framework search failed: {str(e)}")

    if not matches:
        return _err("No matching frameworks found.")

    parts = [f"Match {i}:\n{m['content']}" for i, m in enumerate(matches, 1)]
    return _ok("\n\n---\n\n".join(parts))


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
        query = tool_input.get("query")
        if not query:
            return _err("Missing required input: query")
        return handle_lookup_framework(query)
    if tool_name == "web_search":
        query = tool_input.get("query")
        if not query:
            return _err("Missing required input: query")
        return handle_web_search(query)
    return _err(f"Unknown tool: {tool_name}")


# ── Tool schemas — what Claude sees ──────────────────────────
LOOKUP_FRAMEWORK_TOOL = {
    "name": "lookup_framework",
    "description": (
        "Search the Pattern Mirror framework database for the most relevant psychological framework. "
        "Describe the pattern in natural language — the search is semantic, not keyword-based. "
        "Always call this before producing the final analysis to ground the pattern in established psychology. "
        "Use web_search instead for specific named clinical conditions not covered by general frameworks "
        "(e.g. rejection sensitive dysphoria, alexithymia, C-PTSD emotional flashbacks)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A natural language description of the pattern you've identified — "
                    "e.g. 'person avoids asking for help and prides themselves on self-sufficiency' "
                    "or 'hypervigilant to social rejection, amplifies reassurance-seeking when uncertain'."
                )
            }
        },
        "required": ["query"]
    }
}

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search trusted psychology and mental health sources for information about "
        "a specific named clinical concept or condition. Use this when the pattern "
        "involves a specific named condition not well-covered by general frameworks — for example: "
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
