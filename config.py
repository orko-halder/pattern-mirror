"""
Pattern Mirror — centralized configuration.

All tuneable constants and model names live here.
Import from here instead of hardcoding values in pipeline modules.
"""

from typing import Literal

# ── Models ────────────────────────────────────────────────────
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

# ── Token budgets ─────────────────────────────────────────────
# Sonnet 4.6+ uses adaptive thinking — budget_tokens is gone.
# effort controls how much thinking Claude does: "low" | "medium" | "high"
# On 4.6+, max_tokens is output-only — thinking tokens are separate and not counted here.
THINKING_EFFORT = "high"

MAX_TOKENS_ANALYSE = 6500       # output tokens — used for both thinking and non-thinking calls
MAX_TOKENS_ANALYSE_SHORT = 4000  # used when extended_thinking=False or on truncation retry
# Raised from 4000/2048 (v2.0 taxonomy integration) — the analysis schema grew: pattern_loop
# (5 new fields), next_experiment, confidence, career_progression_risk, why_this_pattern. The
# old ceiling was truncating on the first call, before the forced-call retry logic could run.
# Raised again from 6000/3500 (prediction, interruption_check, relationship_to_primary added) —
# pattern_loop's immediate_relief/career_consequence were also shortened to short clauses in the
# same change, which offsets some of this, but bumping proactively rather than waiting for a
# repeat truncation report.
MAX_TOKENS_VALIDATE = 300
MAX_TOKENS_CLASSIFY = 512
MAX_TOKENS_CONFIDENCE = 800     # Sonnet hypothesis formation + 1-2 confirmation questions
MAX_TOKENS_EVALUATE = 500

# ── Tool use loop ─────────────────────────────────────────────
# Maximum iterations before the loop is force-exited with a PipelineError.
# Normal flow uses at most 3 iterations (1 tool call + 1 force_final + 1 retry).
MAX_TOOL_ITERATIONS = 6

# ── Prompt caching ───────────────────────────────────────────
# Anthropic charges differently for cached vs uncached tokens.
# Cache creation (first call): 1.25× normal input price — you're paying to write the cache.
# Cache read (subsequent calls): 0.10× normal — the whole point.
# Minimum cacheable block: 1024 tokens. Our system prompt + tools exceed this comfortably.
PROMPT_CACHING_BETA = "prompt-caching-2024-07-31"

# ── Types ─────────────────────────────────────────────────────
DeliveryMode = Literal["direct", "paced", "gentle"]
