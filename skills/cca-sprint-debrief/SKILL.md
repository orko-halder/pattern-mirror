---
name: cca-sprint-debrief
description: >
  Claude Certified Architect (CCA-F) sprint debrief. After each Pattern Mirror
  sprint, reads the new code and extracts the Claude API concepts demonstrated,
  then writes new entries to CCA_Exam_Reference.md with concrete examples pulled
  directly from the codebase. Use this skill whenever the user says "update the
  exam doc", "debrief the sprint", "what did we learn this sprint", "add this to
  the exam reference", or after completing a sprint on Pattern Mirror.
---

# CCA Sprint Debrief

You are updating the CCA-F exam reference document after a Pattern Mirror sprint.
The goal: extract the Claude API concepts demonstrated by the new code and write
them up as exam-ready notes with concrete examples from the codebase.

## Arka's learning style (apply this throughout)

- Why before what. Don't just name a concept — explain the problem it solves first.
- Once the pattern is clear, he applies it himself. Don't over-explain the application.
- Concrete over abstract. Every concept needs a code example, not a definition.
- Short and precise. If it can be said in two sentences, say it in two sentences.

## Step 1 — Identify what changed this sprint

Paths:
- Pattern Mirror: `/Users/arkahalder/Documents/Claude/Projects/pattern-mirror`
- Exam reference: `/Users/arkahalder/Documents/Claude/Projects/Antarjyoti/CCA_Exam_Reference.md`

If the user named specific files or a sprint number, use those. Otherwise:
```bash
git -C <pattern-mirror-path> diff HEAD~1 --name-only
```
Read the changed `.py` files.

## Step 2 — Read the existing exam reference

Read `CCA_Exam_Reference.md` to see what's already covered. Don't duplicate existing entries.
Look for gaps — concepts demonstrated in the new code that aren't yet in the doc.

## Step 3 — Extract concepts

For each changed file, identify which Claude API concepts it demonstrates. Map these categories:

| Category | What to look for |
|---|---|
| Model selection | Different models for different pipeline steps, and why |
| Tool use | Tool schemas, tool_choice, envelope pattern, tool use loop |
| Structured output | Forcing tool_choice to get JSON back |
| Extended thinking | budget_tokens, adaptive/effort, when to use |
| Token management | max_tokens strategy, truncation handling, retry logic |
| Error handling | APIConnectionError, RateLimitError, APIStatusError |
| Input/output | format_answers(), XML tags in prompts |
| Streaming | messages.stream() |
| Middleware patterns | Pre/post processing, deterministic vs Claude |
| Pipeline design | Classifier → Analyser → Evaluator flow |

Only extract concepts that are actually demonstrated in the code — don't add theory.

## Step 4 — Write the entries

For each new concept, write an entry in this format:

```markdown
## [Concept Name]

**Why it exists:** [One sentence on the problem it solves]

**The pattern:**
[2-3 sentence explanation]

**From the codebase:**
```python
# Concrete example pulled directly from the Pattern Mirror code
```

**Exam note:** [One sharp sentence on what the exam is likely to test about this]
```

Keep entries tight. If an example is self-explanatory, skip the explanation.

## Step 5 — Append to CCA_Exam_Reference.md

Find the right section in the existing doc and append the new entries there.
If no section fits, add a new one at the bottom.

After writing, print a one-line summary: "Added N entries: [concept names]"

Do not rewrite or reorganise existing content — only add.
