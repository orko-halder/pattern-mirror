"""
Pattern Mirror — investigation question generator.

Layer 2 of the four-layer pipeline. Reads the 5 reflection answers, forms one or
more working hypotheses about the career-limiting pattern, and returns 3-7 targeted
investigation questions designed to test those hypotheses across work domains.

Entry point:
  generate_investigation_questions(client, reflection_answers) → list[str]
"""

from anthropic import Anthropic
from prompts import INVESTIGATION_SYSTEM_PROMPT, INVESTIGATION_TOOL, INVESTIGATION_FALLBACK_QUESTIONS
from validator import format_answers
from config import SONNET_MODEL, MAX_TOKENS_CLASSIFY


def generate_investigation_questions(client: Anthropic, reflection_answers: list[dict]) -> list[str]:
    """Generate 3-7 investigation questions from the 5 reflection answers.

    Uses Sonnet with forced tool_choice — hypothesis quality here directly shapes
    the mirror stage and final analysis. Questions must test hypotheses, not confirm
    them: at least one must be capable of disproving the leading hypothesis.

    Falls back to a safe default set if the API call fails — pipeline must not
    block on investigation generation failure.

    Returns a list of question strings, 3-7 items.
    """
    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=MAX_TOKENS_CLASSIFY,
            system=INVESTIGATION_SYSTEM_PROMPT,
            tools=[INVESTIGATION_TOOL],
            tool_choice={"type": "tool", "name": "generate_investigation_questions"},
            messages=[{"role": "user", "content": format_answers(reflection_answers)}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_investigation_questions":
                questions = block.input.get("questions", [])
                if questions:
                    return questions

    except Exception as e:
        print(f"⚠️  Investigation generation failed: {e}")

    # Fallback — broad cross-domain questions that work for any pattern
    return INVESTIGATION_FALLBACK_QUESTIONS
