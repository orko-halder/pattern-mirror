"""
Pattern Mirror — input validation.

Checks answer quality before passing to the analysis pipeline.
Two checks: relevance (answers respond to their questions) and effort (genuine engagement).
"""

from anthropic import Anthropic
from prompts import QUESTIONS, VALIDATOR_TOOL
from config import HAIKU_MODEL, MAX_TOKENS_VALIDATE


def format_answers(answers: list[dict]) -> str:
    """Format answers into XML-tagged block for the prompt."""
    formatted = "<reflection_session>\n"
    for item in answers:
        formatted += f"  <answer id=\"{item['question']}\">{item['answer']}</answer>\n"
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
        system=(
            "You are an input quality checker for a psychological reflection tool. "
            "You have two jobs:\n\n"
            "1. RELEVANCE: Is each answer actually responding to its question? "
            "It is normal and expected for answers to share themes — the same pattern often surfaces across multiple questions. "
            "Only flag invalid if an answer is clearly unrelated or random.\n\n"
            "2. EFFORT: Is the person genuinely engaging with the questions? "
            "Flag invalid only if most answers are single words, completely empty, or obvious nonsense.\n\n"
            "Be lenient on themes and strict only on relevance and effort.\n\n"
            "Call the input_quality_check tool with your assessment."
        ),
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
