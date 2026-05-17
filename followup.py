"""
Pattern Mirror — follow-up question generator.

Stage 1 of the two-stage pipeline. Reads the 5 initial answers, internally
identifies a pattern hypothesis (not shown to the user), and returns 4-5 targeted
follow-up questions probing whether the pattern repeats across different life domains.

Entry point:
  generate_followups(client, initial_answers) → list[str]
"""

from anthropic import Anthropic
from prompts import FOLLOWUP_SYSTEM_PROMPT, FOLLOWUP_TOOL, FOLLOWUP_FALLBACK_QUESTIONS
from validator import format_answers
from config import HAIKU_MODEL, MAX_TOKENS_CLASSIFY


def generate_followups(client: Anthropic, initial_answers: list[dict]) -> list[str]:
    """Generate 4-5 targeted follow-up questions from the initial 5 answers.

    Uses Haiku with forced tool_choice — cheap, fast, single call.
    The pattern hypothesis is internal to Claude; the returned questions
    must not reveal it. Caller gets only the question strings.

    Falls back to a safe default set if the API call fails — pipeline must not
    block on follow-up generation failure.

    Returns a list of question strings, 4-5 items.
    """
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=MAX_TOKENS_CLASSIFY,
            system=FOLLOWUP_SYSTEM_PROMPT,
            tools=[FOLLOWUP_TOOL],
            tool_choice={"type": "tool", "name": "generate_followup_questions"},
            messages=[{"role": "user", "content": format_answers(initial_answers)}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_followup_questions":
                questions = block.input.get("questions", [])
                if questions:
                    return questions

    except Exception as e:
        print(f"⚠️  Follow-up generation failed: {e}")

    # Fallback — broad cross-domain questions that work for any pattern
    return FOLLOWUP_FALLBACK_QUESTIONS
