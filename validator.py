"""
Pattern Mirror — input validation.

Checks answer quality before passing to the analysis pipeline.
Two checks: relevance (answers respond to their questions) and effort (genuine engagement).

Also provides validate_context_file() — a Haiku relevance check for uploaded documents.
"""

from typing import Optional
from anthropic import Anthropic
from prompts import (
    QUESTIONS,
    SYSTEM_PROMPT,
    VALIDATOR_TOOL,
    VALIDATOR_SYSTEM_PROMPT,
    CONTEXT_RELEVANCE_TOOL,
    CONTEXT_RELEVANCE_SYSTEM_PROMPT,
)
from config import HAIKU_MODEL, MAX_TOKENS_VALIDATE, SONNET_MODEL


def format_answers(
    answers: list[dict],
    followup_answers: Optional[list[dict]] = None,
) -> str:
    """Format answers into XML-tagged block for the prompt.

    Without followup_answers: flat <reflection_session> block — used for
    validation, token counting, and follow-up generation.

    With followup_answers: splits into <initial_answers> and <validation_answers>.
    Each follow-up item must have 'question' (the text) and 'answer' keys.
    """
    if followup_answers is None:
        formatted = "<reflection_session>\n"
        for item in answers:
            formatted += f"  <answer id=\"{item['question']}\">{item['answer']}</answer>\n"
        formatted += "</reflection_session>"
        return formatted

    formatted = "<reflection_session>\n"
    formatted += "  <initial_answers>\n"
    for item in answers:
        formatted += f"    <answer id=\"{item['question']}\">{item['answer']}</answer>\n"
    formatted += "  </initial_answers>\n"
    formatted += "  <validation_answers>\n"
    for i, item in enumerate(followup_answers, 1):
        formatted += (
            f"    <answer id=\"F{i}\" question=\"{item['question']}\">"
            f"{item['answer']}</answer>\n"
        )
    formatted += "  </validation_answers>\n"
    formatted += "</reflection_session>"
    return formatted


def validate_answers(client: Anthropic, answers: list[dict]) -> list[str]:
    """Use Claude to check answer quality before analysis.

    Two checks:
    1. RELEVANCE — is each answer actually responding to its question?
    2. EFFORT — is the person genuinely engaging, or giving empty non-answers?

    Note: recurring themes across answers are expected and valid — that's the pattern.
    Do NOT flag answers for being thematically similar.

    Returns a list of error strings — empty list means valid.
    """

    # Build paired question + answer block so Claude can check relevance
    paired = "<validation_input>\n"
    for i, (question, answer) in enumerate(zip(QUESTIONS, answers), 1):
        paired += f"  <pair id=\"Q{i}\">\n"
        paired += f"    <question>{question}</question>\n"
        paired += f"    <answer>{answer['answer']}</answer>\n"
        paired += "  </pair>\n"
    paired += "</validation_input>"

    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS_VALIDATE,
        system=VALIDATOR_SYSTEM_PROMPT,
        tools=[VALIDATOR_TOOL],
        tool_choice={"type": "tool", "name": "input_quality_check"},
        messages=[{"role": "user", "content": paired}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "input_quality_check":
            result = block.input
            errors = []
            if result.get("relevance") == "invalid":
                reason = result.get("relevance_reason", "answers appear off-topic")
                errors.append(f"Answers off-topic: {reason}")
            if result.get("effort") == "invalid":
                reason = result.get("effort_reason", "answers too brief or empty")
                errors.append(f"Answers too brief: {reason}")
            return errors

    # Fallback: tool call not found — pass validation rather than block pipeline
    return []


def validate_context_file(client: Anthropic, file_id: str) -> list[str]:
    """Check whether the uploaded context file is relevant to psychological pattern analysis.

    Uses Haiku + Files API for a cheap relevance check before the main analysis.
    Returns a list of warning strings — empty list means the document is usable.

    Irrelevant documents (recipes, technical docs, code) get a warning so the
    user can swap the file out rather than silently polluting the analysis.
    """
    response = client.beta.messages.create(
        model=HAIKU_MODEL,
        max_tokens=256,
        betas=["files-api-2025-04-14"],
        system=CONTEXT_RELEVANCE_SYSTEM_PROMPT,
        tools=[CONTEXT_RELEVANCE_TOOL],
        tool_choice={"type": "tool", "name": "context_relevance_check"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {"type": "file", "file_id": file_id},
                },
                {
                    "type": "text",
                    "text": "Is this document relevant to psychological pattern analysis?",
                },
            ],
        }],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "context_relevance_check":
            if not block.input.get("is_relevant", True):
                reason = block.input.get("reason", "")
                return [
                    f"The uploaded document doesn't appear relevant to psychological pattern analysis"
                    f"{f' — {reason}' if reason else ''}. "
                    "You can remove it and continue with your answers, or keep it and Claude will "
                    "focus on your answers instead."
                ]
            return []

    # Fallback: tool call not found — treat as relevant, don't block
    return []


def count_tokens_preflight(client: Anthropic, answers: list[dict]) -> int:
    """Get an accurate token count via the API before running analysis.

    Uses client.messages.count_tokens() — no model inference, no cost beyond the
    count call itself. Returns the exact input token count Anthropic would charge for.

    Called after validate_answers() passes — not a gate, just a display figure
    shown to the user before the expensive Sonnet call runs.

    Uses SYSTEM_PROMPT (base, no delivery mode) as an approximation — the actual
    call uses a delivery-mode-appended version, so the real count will be slightly
    higher. Close enough for display purposes.
    """
    result = client.messages.count_tokens(
        model=SONNET_MODEL,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": format_answers(answers)}],
    )
    return result.input_tokens
