# Pattern Mirror — Claude Code Reference

## What This Project Is

A psychological pattern analysis tool. Users answer 6 structured reflection questions. The system identifies unconscious recurring patterns and returns a structured analysis with a deployable protocol.

This is also a learning project for the Claude Certified Architect exam. Every module demonstrates a specific Claude API concept.

---

## Architecture

```
app.py           Streamlit UI — gatekeeper, renders results
middleware.py    Pre/post processing — token estimate, crisis check, PII, cost log, safety filter
file_context.py  Files API — upload/delete context documents, build document blocks
validator.py     Input quality check (Haiku) — runs before analysis
classifier.py    Readiness classifier (Haiku) — shapes delivery mode
analyser.py      Main pipeline (Sonnet) — tool use loop, returns AnalysisResult
prompts.py       All prompts, tool schemas, delivery variants — no logic here
tools.py         Tool handlers + schemas — framework lookup, web search
evaluator.py     Output quality scorer (Haiku) — runs after analysis
frameworks.json  Local knowledge base of psychological frameworks
```

**Flow:** `app.py` → `pre_process()` → `upload_context_file()` (optional) → `validate_answers()` → `classify_readiness()` → `analyse_structured()` → `post_process()` → `evaluate_output()`

---

## Module Responsibilities

**`file_context.py`** — Files API wrapper. No Claude inference calls.
- `upload_context_file(client, file_bytes, filename) → UploadedFile` — validates type/size, uploads, returns `file_id`.
- `delete_file(client, file_id)` — swallows errors so pipeline cleanup is never interrupted.
- `build_document_block(file_id) → dict` — returns the document content block for use in `messages`.
- Supported types: `.txt`, `.md`, `.pdf`. Max size: 5 MB.
- Files are ephemeral — always call `delete_file()` after use (app.py does this in a `finally` block).

**`middleware.py`** — no Claude calls. All checks are deterministic (regex, arithmetic).
- Pre-processing: `pre_process(answers) → PreCheckResult`. Runs before `validate_answers()`. `blocked=True` stops the pipeline; `warnings` are shown but don't block.
- Post-processing: `post_process(result_data, usage, model) → PostCheckResult`. Runs after `analyse_structured()`. Logs cost to console and returns it in `cost_summary`.
- Crisis check is a hard block. PII detection is warn-only — users may mention contact details in context.
- `AnalysisResult.usage` accumulates `input_tokens` + `output_tokens` across all API calls in the tool use loop.

**`prompts.py`** — single source of truth for all prompt text and tool schemas. Change prompts here, not in the pipeline. `build_system_prompt(delivery_mode)` appends delivery instructions to the base system prompt.

**`tools.py`** — every tool handler returns a standard envelope: `{"status": "success"|"error", "content": str, "metadata": dict}`. Claude never sees `metadata` — only `content`. Add new tools here: write a handler, add a schema constant, register in `handle_tool_call()`.

**`classifier.py`** — Claude classifies `self_awareness` and `fragility_risk`. Python derives `delivery_mode` deterministically in `derive_delivery_mode()`. Do not ask Claude to derive the delivery mode — it's inconsistent at boundaries.

**`analyser.py`** — the tool use loop. `force_final=True` after the first tool call forces `pattern_analysis`. Extended thinking is enabled on the first call only, disabled when `force_final=True`. Truncation is handled via retry — messages are never modified, only `max_tokens` changes.

---

## Model Usage

| Component | Model | Why |
|---|---|---|
| `validate_answers` | `claude-haiku-4-5-20251001` | Binary check — fast, cheap |
| `classify_readiness` | `claude-haiku-4-5-20251001` | Pattern matching — upgrade to Sonnet when ready |
| `analyse_structured` | `claude-sonnet-4-5` | Core product — quality matters |
| `evaluate_output` | `claude-haiku-4-5-20251001` | Rubric scoring — mechanical task |

---

## Key Constraints

- **`prompts.py` is logic-free.** No imports, no conditionals. Strings and dicts only.
- **`validator.py` returns `list[str]`** — empty = valid. Never `bool`.
- **`classifier.py` never blocks the pipeline.** On any failure it returns a safe default (`medium/medium/paced`).
- **Tool handlers always return the envelope shape.** Never return raw strings from a tool handler.
- **Delivery mode only affects framing sections** (core_pattern, secondary_pattern, evidence, payoff). The protocol must be concrete regardless of delivery mode — see `_PROTOCOL_SCOPE_NOTE` in `prompts.py`.
- **`extended_thinking` on `claude-sonnet-4-5` requires `thinking.type: "enabled"` + `budget_tokens`.** When upgrading to Sonnet 4.6+, migrate to `thinking.type: "adaptive"` + `effort`.
- **Files API requires `client.beta.messages.create` with `betas=["files-api-2025-04-14"]`.** When `context_file_id` is set, `analyser.py` uses this for all calls in the loop — the document block lives in the first user message which is replayed every turn.
- **Context files must be deleted after use.** `app.py` wraps the full pipeline in `try/finally` to ensure `delete_file()` is always called, even when `st.stop()` is raised mid-pipeline.

---

## Adding a New Framework

1. Add an entry to `frameworks.json`
2. Add the key to the `framework_key` description in `LOOKUP_FRAMEWORK_TOOL` in `tools.py`
3. No other changes needed

## Adding a New Tool

1. Write a handler in `tools.py` that returns `_ok(content, **metadata)` or `_err(content)`
2. Add a tool schema constant
3. Register in `handle_tool_call()`
4. Add to the `tools` list in `analyser.py`

## Adding a New Delivery Mode Parameter

See the checklist in `classifier.py` module docstring. Future parameters (`psychological_vocabulary`, `resistance`) are tracked in the project backlog.

---

## Running Locally

```bash
cd pattern-mirror
source .venv/bin/activate
streamlit run app.py
```

Requires `.env` with:
```
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...   # optional — web search disabled if missing
```

## Skills

Project-specific skills live in `skills/`. Install them by double-clicking the `.skill` files in the Antarjyoti folder — they install globally in Claude, not per-project.

| Skill | Trigger | What it does |
|---|---|---|
| `pm-code-review` | "review the code", "any concerns" | Checks files against CLAUDE.md constraints |
| `cca-sprint-debrief` | "debrief the sprint", "update exam doc" | Extracts Claude API concepts → CCA_Exam_Reference.md |
| `pm-commit` | "ready to commit", "commit message" | Lints staged files, generates commit message |

When CLAUDE.md rules change, update the corresponding skill source in `skills/` and repackage.

---

## First-Time Setup (after cloning)

```bash
source .venv/bin/activate
pip install ruff
sh scripts/install-hooks.sh   # installs git pre-commit hook
```

The pre-commit hook runs `ruff check` on staged `.py` files and blocks commits on lint failures. Run `.venv/bin/ruff check --fix <file>` to auto-fix where possible.

---

## What Not To Do

- Do not add prompt text directly in `analyser.py` or `app.py` — it goes in `prompts.py`
- Do not change `delivery_mode` derivation logic in the classifier tool schema — it belongs in `derive_delivery_mode()` in Python
- Do not modify `messages[]` on a truncation retry — the retry works precisely because messages are unchanged
- Do not show `ThinkingBlock` content to the user — it is Claude's internal monologue
- Do not raise exceptions from tool handlers — return `_err(content)` instead
- Do not degrade silently — if a pipeline step fails or is skipped, surface it to the user rather than producing a lower-quality result without them knowing
