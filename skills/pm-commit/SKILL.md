---
name: pm-commit
description: >
  Pattern Mirror commit message generator. Reads staged changes and writes
  a commit message in the project's format. Use this skill whenever the user
  is ready to commit Pattern Mirror changes: "ready to commit", "commit message",
  "let's commit", "what should the commit message be", "commit the changes".
  Also triggers when the user says "commit" in the context of the pattern-mirror
  project.
---

# Pattern Mirror Commit Helper

The pre-commit git hook already handles linting — ruff runs automatically on
staged `.py` files when you commit. This skill's job is to read what's staged
and write the commit message in the right format.

## Step 1 — See what's staged

```bash
git -C /Users/arkahalder/Documents/Claude/Projects/pattern-mirror diff --staged --name-only
git -C /Users/arkahalder/Documents/Claude/Projects/pattern-mirror diff --staged --stat
```

If nothing is staged, tell the user and stop.

## Step 2 — Generate the commit message

Read the staged diff to understand what changed:
```bash
git -C /Users/arkahalder/Documents/Claude/Projects/pattern-mirror diff --staged
```

Write a commit message in this format:

```
<type>: <short summary in imperative form>

<body — bullet points, one per logical change>
<each bullet explains what changed AND why if non-obvious>
```

Types: `feat` (new feature), `fix` (bug fix), `refactor` (restructure, no behaviour change),
`docs` (docs/comments only), `chore` (config, tooling).

Keep the summary under 72 characters. Body bullets are concise — not exhaustive.

**Example:**
```
feat: add pre/post processing middleware

- token_estimate: chars/4 heuristic, warns at 3k tokens, blocks at 5k
- crisis_check: regex keyword scan — hard block with crisis resources
- pii_detect: email/phone/SSN scan — warn-only, pipeline continues
- log_cost: accumulates input/output tokens across tool loop, prints cost
- safety_filter: scans protocol steps only, one warning if flagged
- AnalysisResult gains usage: dict; app.py wires pre/post around pipeline
```

## Step 4 — Print the command

Print exactly this, substituting the message:

```
Run in your terminal:

git add <staged files>
git commit -m "<first line>" \
  -m "<body as single string with \n separators>"
```

Or if it's a single-line message:
```
git commit -m "<message>"
```

Note: the pre-commit hook runs ruff on staged files automatically. If the hook fails
with an `index.lock` error, run `rm .git/index.lock` and try again.
