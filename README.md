# Pattern Mirror

A career progression pattern analysis tool for the Cognizant Bluebolt initiative. Users answer structured questions about how they operate at work, and the tool identifies the specific recurring behaviour that is limiting their career progression — then gives them a deployable protocol to interrupt it.

Secondary purpose: hands-on vehicle for the Claude Certified Architect (CCA-F) exam — every Claude API concept is demonstrated in practice here.

## What it does

Most employees who plateau describe a symptom ("I need to work on my visibility"). Pattern Mirror asks the question underneath: what is the recurring behaviour that produces that symptom, why does it exist, and what does operating without it actually look like?

The tool runs a four-layer pipeline:

1. **Reflection** — 5 structured questions about how the employee operates at work
2. **Investigation** — Sonnet generates 3-7 targeted follow-up questions, testing hypotheses across different work domains (manager relationship, peer dynamics, high-stakes moments, workload, decisions)
3. **Mirror** — Sonnet forms an internal hypothesis and reflects 1-2 soft observations back to the employee; their response shapes the final analysis
4. **Analysis** — Sonnet returns a named pattern with evidence drawn directly from the employee's answers, a career cost assessment, and a concrete protocol specific enough to use in a meeting the next morning

## Status

Working prototype. The full four-layer pipeline runs end-to-end in the Streamlit UI and via the MCP server.

What's live: all four pipeline layers, readiness classifier, three delivery modes, prompt caching, extended thinking, Files API, output quality evaluator, MCP server.

What's pending: career-progression frameworks library (RAG pipeline built but content reset), validated pattern taxonomy.

## Stack

- Python 3.11+
- `anthropic` SDK — Claude Sonnet 4.6 (analysis, investigation, mirror), Claude Haiku 4.5 (validation, classification, evaluation)
- Streamlit — browser UI
- ChromaDB + sentence-transformers — RAG pipeline (built; awaiting content rebuild)
- MCP SDK — stdio server exposing the full pipeline as a single tool

## Running locally

**Streamlit UI:**

```bash
cd pattern-mirror
source .venv/bin/activate
streamlit run app.py
```

**MCP server (terminal / Claude Code integration):**

```bash
# Test the practice server (no API key needed)
python test_mcp_client.py

# Test the Pattern Mirror MCP server (runs full pipeline, costs tokens)
python test_mcp_server.py
```

Requires `.env`:

```
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...   # optional — web search disabled if missing
```

## Project layout

```
app.py                Streamlit UI — four-layer flow
middleware.py         Pre/post processing — token estimate, crisis check, PII, cost log
file_context.py       Files API — upload/delete context documents
validator.py          Input quality check (Haiku) + format_answers()
investigation.py      Investigation question generator (Sonnet) — layer 2
mirror.py             Mirror question generator (Sonnet) — layer 3
classifier.py         Readiness classifier (Haiku) — shapes delivery mode
analyser.py           Main pipeline (Sonnet) — tool use loop, returns AnalysisResult
prompts.py            All prompts and tool schemas — no logic
tools.py              Tool handlers + schemas
rag.py                RAG pipeline — ChromaDB + sentence-transformers
evaluator.py          Output quality scorer (Haiku)
frameworks.json       Knowledge base — pending rebuild with career-progression content

mcp_server.py         MCP server — exposes analyse_reflection as a tool over stdio
practice_mcp_server.py  Practice MCP server — word_count + reading_time (learning exercise)
test_mcp_server.py    Integration test for Pattern Mirror MCP server
test_mcp_client.py    Integration test for practice MCP server
```

## First-time setup (after cloning)

```bash
source .venv/bin/activate
pip install ruff
sh scripts/install-hooks.sh
```

The pre-commit hook runs `ruff check` on staged `.py` files and blocks commits on lint failures.

## License

Private. Not for redistribution.
