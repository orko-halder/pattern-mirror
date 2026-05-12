"""
Pattern Mirror — pre/post processing middleware.

Pre-processing (runs before pipeline, no Claude calls):
  - token_estimate : rough token count — warns or blocks on very large inputs
  - crisis_check   : keyword scan for crisis language — hard block, surfaces resources
  - pii_detect     : regex scan for PII patterns — warns, does not block

Post-processing (runs after pipeline):
  - log_cost       : prints token usage and estimated cost from usage dict
  - safety_filter  : keyword scan of protocol output for potentially harmful content

Entry points:
  pre_process(answers)               → PreCheckResult
  post_process(result_data, usage)   → PostCheckResult
"""

import re
from dataclasses import dataclass, field


# ── Result types ──────────────────────────────────────────────

@dataclass
class PreCheckResult:
    blocked: bool = False
    errors: list[str] = field(default_factory=list)    # hard stop — pipeline does not run
    warnings: list[str] = field(default_factory=list)  # surfaced to user, pipeline continues
    token_estimate: int = 0


@dataclass
class PostCheckResult:
    flagged: bool = False
    warnings: list[str] = field(default_factory=list)
    cost_summary: str = ""


# ── Token estimation ───────────────────────────────────────────

# Fixed overhead: base system prompt + tool schemas + classifier prompt.
# Rough estimate based on observed prompt sizes.
_SYSTEM_OVERHEAD_TOKENS = 1500

_TOKEN_WARN_THRESHOLD = 3000   # warn above this — answers are getting long
_TOKEN_BLOCK_THRESHOLD = 5000  # block above this — unlikely with 6 short answers


def estimate_tokens(answers: list[dict]) -> int:
    """Rough token estimate for the full analysis request.

    Uses chars/4 heuristic. Includes fixed overhead for system prompt and tool schemas.
    This is intentionally an overestimate — better to warn early than to hit API limits.
    No API call — used inside pre_process() as a fast deterministic gate.
    """
    answer_chars = sum(len(a.get("answer", "")) for a in answers)
    answer_tokens = answer_chars // 4
    return _SYSTEM_OVERHEAD_TOKENS + answer_tokens


# ── Crisis language check ──────────────────────────────────────

# Matched as word/phrase substrings (case-insensitive, re.search).
# Intentionally conservative — false positives in a psych tool are acceptable.
_CRISIS_PATTERNS = [
    r"\bsuicid",                   # suicide, suicidal, suicidality
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bdon.t want to live\b",
    r"\bwant to die\b",
    r"\bself.harm\b",
    r"\bself.hurt\b",
    r"\bcut myself\b",
    r"\boverdos",                  # overdose, overdosing
    r"\bno reason to live\b",
    r"\bbetter off dead\b",
    r"\bbetter off without me\b",
]

_CRISIS_MESSAGE = (
    "We noticed some language in your answers that concerns us. "
    "Pattern Mirror is a reflection tool, not a crisis service — "
    "it isn't the right tool for what you're going through right now.\n\n"
    "If you're in crisis, please reach out:\n"
    "• International: https://www.iasp.info/resources/Crisis_Centres/\n"
    "• Crisis Text Line (US): Text HOME to 741741\n"
    "• Samaritans (UK/Ireland): 116 123\n"
    "• Vandrevala Foundation (India): 1860-2662-345"
)


def crisis_check(answers: list[dict]) -> list[str]:
    """Scan answers for crisis language.

    Returns a list with one error string if crisis language is found, empty list otherwise.
    This is a hard block — pipeline does not run if this returns non-empty.
    """
    all_text = " ".join(a.get("answer", "") for a in answers).lower()
    for pattern in _CRISIS_PATTERNS:
        if re.search(pattern, all_text):
            return [_CRISIS_MESSAGE]
    return []


# ── PII detection ──────────────────────────────────────────────

# Patterns ordered by specificity. Phone is intentionally loose —
# false positives are acceptable; false negatives are not.
_PII_PATTERNS: dict[str, str] = {
    "email address": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "phone number": r"(\+?\d[\d\s\-().]{7,}\d)",
    "SSN": r"\b\d{3}[- ]\d{2}[- ]\d{4}\b",
}


def pii_detect(answers: list[dict]) -> list[str]:
    """Scan answers for PII patterns.

    Returns warning strings — one per PII type detected. Does not block the pipeline.
    Users may legitimately mention contact details in context; they deserve to know
    the data is being sent to Claude, not to have the pipeline silently refuse.
    """
    all_text = " ".join(a.get("answer", "") for a in answers)
    warnings = []
    for label, pattern in _PII_PATTERNS.items():
        if re.search(pattern, all_text):
            warnings.append(
                f"Your answers may contain a {label}. "
                "Pattern Mirror sends your responses to Claude for analysis. "
                "You can continue, but consider removing sensitive information first."
            )
    return warnings


_EMPTY_ANSWER = "[no answer given]"
_EMPTY_BLOCK_THRESHOLD = 6   # all questions empty → hard block
_EMPTY_WARN_THRESHOLD = 4    # 4+ empty → warn, validator decides


def empty_check(answers: list[dict], has_context_file: bool = False) -> tuple[list[str], list[str]]:
    """Check how many questions were left unanswered.

    Returns (errors, warnings).

    Without a context file:
      All empty → hard block. 4+ empty → warn, pipeline continues.

    With a context file:
      All empty → warn only (document is the primary source).
      4+ empty → info note, pipeline continues.
    """
    empty_count = sum(1 for a in answers if a.get("answer", "") == _EMPTY_ANSWER)
    answered = len(answers) - empty_count

    if empty_count >= _EMPTY_BLOCK_THRESHOLD:
        if has_context_file:
            return (
                [],
                [
                    "No questions answered — Claude will use your uploaded document as the "
                    "primary source and treat the 6 questions as a structural framework."
                ],
            )
        return (
            ["Please answer at least one question before running the analysis."],
            [],
        )

    if empty_count >= _EMPTY_WARN_THRESHOLD:
        return (
            [],
            [
                f"Only {answered} of {len(answers)} questions answered. "
                "The analysis may be limited — more context produces better results."
            ],
        )

    return [], []


# ── Pre-process entry point ────────────────────────────────────

def pre_process(answers: list[dict], has_context_file: bool = False) -> PreCheckResult:
    """Run all pre-processing checks. Call before validate_answers().

    Checks run in priority order:
    1. Empty answers (block if all empty with no file, warn otherwise)
    2. Token estimate (block if extreme, warn if large)
    3. Crisis language (hard block)
    4. PII detection (warn only)

    has_context_file: when True, all-empty answers become a warning not a block —
    the uploaded document is treated as the primary reflection source.

    Returns PreCheckResult:
      blocked=True  → pipeline must not run; show errors
      warnings      → show to user, pipeline continues
    """
    result = PreCheckResult()

    # 1. Empty answers — cheapest check, run first
    empty_errors, empty_warnings = empty_check(answers, has_context_file)
    result.errors.extend(empty_errors)
    result.warnings.extend(empty_warnings)
    if result.errors:
        result.blocked = True
        return result

    # 2. Token estimate
    result.token_estimate = estimate_tokens(answers)
    if result.token_estimate > _TOKEN_BLOCK_THRESHOLD:
        result.errors.append(
            f"Your answers are very long (~{result.token_estimate:,} tokens estimated). "
            "Please shorten them and try again."
        )
    elif result.token_estimate > _TOKEN_WARN_THRESHOLD:
        result.warnings.append(
            f"Your answers are quite detailed (~{result.token_estimate:,} tokens estimated). "
            "Analysis will still run."
        )

    # 3. Crisis language — hard block
    crisis_errors = crisis_check(answers)
    if crisis_errors:
        result.errors.extend(crisis_errors)

    # 4. PII — warn only
    result.warnings.extend(pii_detect(answers))

    result.blocked = len(result.errors) > 0
    return result


# ── Cost logging ───────────────────────────────────────────────

# Claude Sonnet 3.5 / 4.x approximate pricing (USD per token).
# Update when Anthropic changes pricing.
_COST_PER_INPUT_TOKEN = 3.00 / 1_000_000
_COST_PER_OUTPUT_TOKEN = 15.00 / 1_000_000
_COST_PER_CACHE_CREATION_TOKEN = 3.75 / 1_000_000   # 1.25× input — writing to cache
_COST_PER_CACHE_READ_TOKEN = 0.30 / 1_000_000        # 0.10× input — reading from cache


def log_cost(usage: dict, model: str = "") -> str:
    """Compute and log token usage + estimated cost.

    Returns a formatted summary string — also prints to console.
    usage dict must have keys: input_tokens, output_tokens.
    Optional cache keys: cache_creation_input_tokens, cache_read_input_tokens.
    """
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    cost = (
        (input_tokens * _COST_PER_INPUT_TOKEN)
        + (output_tokens * _COST_PER_OUTPUT_TOKEN)
        + (cache_creation * _COST_PER_CACHE_CREATION_TOKEN)
        + (cache_read * _COST_PER_CACHE_READ_TOKEN)
    )

    model_tag = f" ({model})" if model else ""
    cache_note = (
        f" | cache write: {cache_creation:,} / read: {cache_read:,}"
        if cache_creation or cache_read
        else ""
    )
    summary = (
        f"📊 Usage{model_tag} — "
        f"in: {input_tokens:,} | out: {output_tokens:,}{cache_note} | "
        f"est. cost: ${cost:.4f}"
    )
    print(summary)
    return summary


# ── Safety filter ──────────────────────────────────────────────

# Scans the structured protocol output only — not framing sections.
# One flagged pattern → one warning (not one per match).
_SAFETY_PATTERNS = [
    r"\bharm (yourself|others)\b",
    r"\bself.injur",
    r"\bsuicid",
    r"\bself.harm\b",
]


def safety_filter(result_data: dict) -> PostCheckResult:
    """Scan structured output protocol for potentially harmful content.

    Only scans protocol sections (steps, fallbacks) — not framing text.
    Returns one warning if anything is flagged.
    """
    protocol = result_data.get("protocol", {})
    steps_text = " ".join(protocol.get("steps", []))
    fallback_mid = protocol.get("fallback_mid_activation", "")
    fallback_shut = protocol.get("fallback_shutdown", "")
    scan_text = f"{steps_text} {fallback_mid} {fallback_shut}".lower()

    for pattern in _SAFETY_PATTERNS:
        if re.search(pattern, scan_text):
            return PostCheckResult(
                flagged=True,
                warnings=[
                    "Some protocol content references sensitive topics. "
                    "Please review the steps carefully before following them."
                ]
            )

    return PostCheckResult()


# ── Post-process entry point ───────────────────────────────────

def post_process(result_data: dict, usage: dict, model: str = "") -> PostCheckResult:
    """Run all post-processing checks. Call after analyse_structured() succeeds.

    Returns PostCheckResult:
      cost_summary → formatted log line (also printed to console)
      flagged=True + warnings → surface to user
    """
    post = PostCheckResult()
    post.cost_summary = log_cost(usage, model)

    safety = safety_filter(result_data)
    post.flagged = safety.flagged
    post.warnings = safety.warnings

    return post
