"""
Pattern Mirror — confidence check question generator.

Stage 2 of the three-stage pipeline. Reads all initial and follow-up answers,
forms an internal pattern hypothesis, and generates 1-2 confirmation questions
to verify the hypothesis with the user before the final analysis runs.

Entry point:
  generate_confidence_questions(client, initial_answers, followup_answers) → ConfidenceResult
"""

import sys
from dataclasses import dataclass
from anthropic import Anthropic
from prompts import CONFIDENCE_SYSTEM_PROMPT, CONFIDENCE_TOOL
from validator import format_answers
from config import SONNET_MODEL, MAX_TOKENS_CONFIDENCE


@dataclass
class ConfidenceResult:
    hypothesis: str       # internal — never shown to the user
    questions: list[str]  # 1-2 confirmation questions shown to the user


# Fallback questions if the API call fails — broad enough to work for any pattern
CONFIDENCE_FALLBACK_QUESTIONS = [
    "Thinking about everything you've shared — does a pattern feel familiar? "
    "What would you say is the one thing most likely to hold you back at work?",
]


def generate_confidence_questions(
    client: Anthropic,
    initial_answers: list[dict],
    followup_answers: list[dict],
) -> ConfidenceResult:
    """Generate 1-2 hypothesis confirmation questions from all collected answers.

    Uses Sonnet with forced tool_choice. Forms a precise internal hypothesis about
    the career-limiting pattern, then generates soft confirmation questions phrased
    as observations the employee can agree with, refine, or push back on.
    The pattern label is never revealed in the questions.

    Falls back gracefully if the API call fails — pipeline must not block here.

    Returns a ConfidenceResult with:
      hypothesis — internal string passed to analyse_structured() as primed context.
                   Never shown to the user.
      questions  — list of 1-2 strings rendered to the user in Stage 3 (confidence check).
    """
    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=MAX_TOKENS_CONFIDENCE,
            system=CONFIDENCE_SYSTEM_PROMPT,
            tools=[CONFIDENCE_TOOL],
            tool_choice={"type": "tool", "name": "generate_confidence_questions"},
            messages=[{
                "role": "user",
                "content": format_answers(initial_answers, followup_answers),
            }],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_confidence_questions":
                hypothesis = block.input.get("hypothesis", "")
                questions = block.input.get("questions", [])
                if hypothesis and questions:
                    return ConfidenceResult(hypothesis=hypothesis, questions=questions)

    except Exception as e:
        print(f"⚠️  Confidence question generation failed: {e}", file=sys.stderr)

    # Fallback — pipeline continues with a broad open question
    return ConfidenceResult(
        hypothesis="pattern unclear — proceeding without primed hypothesis",
        questions=CONFIDENCE_FALLBACK_QUESTIONS,
    )
