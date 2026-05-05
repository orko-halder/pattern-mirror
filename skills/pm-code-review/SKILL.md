---
name: pm-code-review
description: >
  Pattern Mirror code reviewer. Checks Python files against the architectural
  constraints defined in CLAUDE.md and the Python best practices standards.
  Use this skill whenever the user asks to review Pattern Mirror code, check
  staged changes before committing, audit a refactor, or verify that a file
  follows project rules. Trigger on: "review the code", "check this before
  commit", "does this follow the rules", "audit the refactor", "any concerns
  with the changes".
---

# Pattern Mirror Code Reviewer

Two-pass review: architectural constraints (CLAUDE.md) then Python style
(python-core.md). Report real violations only — not suggestions, not "consider"
items. Only flag things that break a stated rule.

## Step 1 — Get the files to review

If the user specified files, use those. Otherwise:
- Run `git -C <pattern-mirror-path> diff --staged --name-only` to see staged files
- If nothing staged, run `git -C <pattern-mirror-path> diff HEAD~1 --name-only` for last commit
- Filter to `.py` files only

Pattern Mirror project path: `/Users/arkahalder/Documents/Claude/Projects/pattern-mirror`

Read both standards before reviewing:
- `CLAUDE.md` — architectural source of truth
- `skills/python-best-practices/standards/python-core.md` — Python style rules

CLAUDE.md and python-core.md win over anything below if there's a discrepancy.

---

## Pass 1 — Architectural constraints (from CLAUDE.md)

### prompts.py
- No imports (`import`, `from X import`)
- No conditionals (`if`, `elif`, `else`, `match`)
- No function definitions containing logic — only string assembly
- Only strings, dicts, and list literals

### validator.py
- `validate_answers()` must return `list[str]`, never `bool`
- Empty list = valid. Non-empty = errors to show user.

### classifier.py
- `classify_readiness()` must never raise — any failure path returns the safe default
  `{"self_awareness": "medium", "fragility_risk": "medium", "delivery_mode": "paced"}`
- `delivery_mode` must NOT be derived inside Claude's tool schema — belongs in `derive_delivery_mode()` in Python

### tools.py
- Every tool handler must return `{"status": "success"|"error", "content": str, "metadata": dict}`
- Handlers must never return raw strings
- Handlers must never raise exceptions — use `_err(content)` instead

### analyser.py / app.py
- No prompt text inline — all prompts belong in `prompts.py`
- `messages[]` must never be modified on a truncation retry — only `max_tokens` changes
- `ThinkingBlock` content (`block.type == "thinking"`) must never be surfaced to the user
- The tool use loop must have an iteration cap — no bare `while True`

### file_context.py
- No Claude inference calls — upload/delete/build only
- `delete_file()` must swallow exceptions (never interrupt pipeline cleanup)
- `app.py` must call `delete_file()` in a `finally` block

### Any pipeline module
- Silent degradation is a violation. Failures must surface to the user.
- Do not call `st.error()` / `st.warning()` and silently continue — stop when appropriate.

---

## Pass 2 — Python style (from python-core.md)

Read `skills/python-best-practices/standards/python-core.md` in full before this pass.

Key violations to flag:

**Type hints**
- Old-style generics: `List[X]`, `Dict[X, Y]`, `Optional[X]`, `Tuple[X]` — use `list[X]`, `dict[X, Y]`, `X | None`, `tuple[X]`
- `typing.Union[X, Y]` — use `X | Y`

**Error handling**
- Bare `except:` — must catch a specific exception
- `except Exception:` that silently passes or returns a default — hides bugs

**Mutable defaults**
- Function parameter with a mutable default (`def f(x, items=[])`) — use `None` + create inside

**Imports**
- Wildcard imports (`from module import *`) — never allowed
- `lambda` assigned to a variable (E731) — use `def` or `functools.partial`

**Resources**
- File opened with `open()` outside a `with` block — must use context manager

Only flag these if they appear in the files being reviewed. Do not audit the whole codebase.

---

## Step 3 — Report findings

Two sections, only shown if there are violations in that category:

```
### Architectural violations
analyser.py:34 — prompt text inline. Move to prompts.py. [CLAUDE.md: no inline prompts]

### Python style violations  
validator.py:12 — Optional[str] should be str | None [python-core.md: modern type hints]
```

If a section is clean, omit it.
If everything is clean: say `No violations found.` and stop.

Do not add suggestions, "consider" items, or style preferences unless the user asks.
