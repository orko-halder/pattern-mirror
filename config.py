"""
Pattern Mirror — centralized configuration.

All tuneable constants and model names live here.
Import from here instead of hardcoding values in pipeline modules.
"""

from typing import Literal

# ── Models ────────────────────────────────────────────────────
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-5"

# ── Token budgets ─────────────────────────────────────────────
# NOTE: budget_tokens is deprecated on Sonnet 4.6+ / Opus 4.6+.
# When upgrading, migrate to: thinking={"type": "adaptive"}, effort="medium|high"
THINKING_BUDGET = 2000

MAX_TOKENS_ANALYSE = 4000       # used when extended_thinking=True
MAX_TOKENS_ANALYSE_SHORT = 2048  # used when extended_thinking=False or on truncation retry
MAX_TOKENS_VALIDATE = 300
MAX_TOKENS_CLASSIFY = 512
MAX_TOKENS_EVALUATE = 500

# ── Tool use loop ─────────────────────────────────────────────
# Maximum iterations before the loop is force-exited with a PipelineError.
# Normal flow uses at most 3 iterations (1 tool call + 1 force_final + 1 retry).
MAX_TOOL_ITERATIONS = 6

# ── Types ─────────────────────────────────────────────────────
DeliveryMode = Literal["direct", "paced", "gentle"]
