---
name: pm-code-review
description: >
  Pattern Mirror code reviewer. Checks Python files against the architectural
  constraints defined in CLAUDE.md. Use this skill whenever the user asks to
  review Pattern Mirror code, check staged changes before committing, audit a
  refactor, or verify that a file follows project rules. Trigger on: "review
  the code", "check this before commit", "does this follow the rules", "audit
  the refactor", "any concerns with the changes".
---

# Pattern Mirror Code Reviewer

You are reviewing Pattern Mirror code against the architectural constraints in CLAUDE.md.
Your job is to find real violations — not style preferences, not suggestions. Only flag
things that break a stated rule.

## Step 1 — Get the files to review

If the user specified files, use those. Otherwise:
- Run `git -C <pattern-mirror-path> diff --staged --name-only` to see staged files
- If nothing staged, run `git -C <pattern-mirror-path> diff HEAD~1 --name-only` for last commit
- Filter to `.py` files only

Read CLAUDE.md from the pattern-mirror project first — it is the source of truth.
The rules below are extracted from it, but CLAUDE.md wins if there's any discrepancy.

Pattern Mirror project path: `/Users/arkahalder/Documents/Claude/Projects/pattern-mirror`

## Step 2 — Check each file against these rules

### prompts.py
- No imports (no `import`, no `from X import`)
- No conditionals (`if`, `elif`, `else`, `match`)
- No function definitions that contain logic — only string assembly
- Only strings, dicts, and list literals

### validator.py
- `validate_answers()` must return `list[str]`, never `bool`
- Empty list = valid. Non-empty = errors to show user.

### classifier.py
- `classify_readiness()` must never raise an exception — any failure path must return a safe default (`{"self_awareness": "medium", "fragility_risk": "medium", "delivery_mode": "paced"}`)
- `delivery_mode` must NOT be derived inside Claude's tool schema — it must be computed in `derive_delivery_mode()` in Python after the tool call returns

### tools.py
- Every tool handler must return the envelope shape: `{"status": "success"|"error", "content": str, "metadata": dict}`
- Handlers must never return raw strings
- Handlers must never raise exceptions — use `_err(content)` instead

### analyser.py / app.py
- No prompt text inline — all prompts belong in `prompts.py`
- `messages[]` must never be modified on a truncation retry — only `max_tokens` changes
- `ThinkingBlock` content (block.type == "thinking") must never be surfaced to the user
- The tool use loop must have an iteration cap — no bare `while True`

### Any pipeline module
- Silent degradation is a violation. If a step fails or is skipped, the failure must be surfaced to the user. Never produce a lower-quality result without saying so.
- Do not call `st.error()` / `st.warning()` and then silently continue — stop the pipeline when appropriate.

### delivery_mode
- Derivation logic belongs only in `derive_delivery_mode()` in `classifier.py`
- Never ask Claude to pick the delivery mode inside a tool schema or prompt

## Step 3 — Report findings

Format: one violation per line. Be specific — file, line number if possible, what rule it breaks.

If nothing is wrong: say "No violations found." and stop. Do not add suggestions, style notes,
or "nice to have" improvements unless the user asks.

Example output:
```
prompts.py:34 — conditional found (`if delivery_mode == "direct"`). prompts.py must be logic-free.
tools.py:88 — handler returns raw string instead of envelope.
analyser.py:102 — prompt text inline (hardcoded system string). Move to prompts.py.
```

If you find violations, also state which CLAUDE.md rule each one breaks so the user
can cross-reference.
