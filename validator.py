"""
Pattern Mirror — input validation.

Checks answer quality before passing to the analysis pipeline.
Two checks: relevance (answers respond to their questions) and effort (genuine engagement).
"""

from anthropic import Anthropic
from prompts import QUESTIONS


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
        paired += f"  </pair>\n"
    paired += "</validation_input>"

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=(
            "You are an input quality checker for a psychological reflection tool. "
            "You have two jobs:\n\n"
            "1. RELEVANCE: Is each answer actually responding to its question? "
            "It is normal and expected for answers to share themes — the same pattern often surfaces across multiple questions. "
            "Only flag INVALID if an answer is clearly unrelated or random.\n\n"
            "2. EFFORT: Is the person genuinely engaging with the questions? "
            "Flag INVALID only if most answers are single words, completely empty, or obvious nonsense.\n\n"
            "Reply in this exact format:\n"
            "RELEVANCE: VALID or INVALID — one short reason\n"
            "EFFORT: VALID or INVALID — one short reason\n\n"
            "Be lenient on themes and strict only on relevance and effort."
        ),
        messages=[
            {"role": "user", "content": paired}
        ],
    )

    result = response.content[0].text.strip()
    lines = {line.split(":")[0].strip(): line for line in result.splitlines() if ":" in line}

    errors = []

    relevance_line = lines.get("RELEVANCE", "")
    if "INVALID" in relevance_line:
        reason = relevance_line.split("INVALID", 1)[1].strip(" —-")
        errors.append(f"Answers off-topic: {reason}")

    effort_line = lines.get("EFFORT", "")
    if "INVALID" in effort_line:
        reason = effort_line.split("INVALID", 1)[1].strip(" —-")
        errors.append(f"Answers too brief: {reason}")

    return errors
