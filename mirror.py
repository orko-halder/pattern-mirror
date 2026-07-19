"""
Pattern Mirror — mirror stage question generator.

Layer 3 of the four-layer pipeline. Reads all reflection and investigation answers,
forms an internal working hypothesis about the career-limiting pattern, and generates
1-2 mirror questions that reflect the observed pattern back to the employee — phrased
as observations, not conclusions, giving them room to confirm, refine, or push back.

Entry point:
  generate_mirror_questions(client, reflection_answers, investigation_answers) → MirrorResult
"""

import sys
from dataclasses import dataclass
from anthropic import Anthropic
from prompts import MIRROR_SYSTEM_PROMPT, MIRROR_TOOL
from validator import format_answers
from config import SONNET_MODEL, MAX_TOKENS_CONFIDENCE


@dataclass
class MirrorResult:
    hypothesis: str       # internal — never shown to the user
    questions: list[str]  # 1-2 mirror questions shown to the user


# Fallback questions if the API call fails — broad enough to work for any pattern
MIRROR_FALLBACK_QUESTIONS = [
    "Thinking about everything you've shared — does a pattern feel familiar? "
    "What would you say is the one thing most likely to hold you back at work?",
]


def generate_mirror_questions(
    client: Anthropic,
    reflection_answers: list[dict],
    investigation_answers: list[dict],
) -> MirrorResult:
    """Generate 1-2 mirror questions from all collected answers.

    Uses Sonnet with forced tool_choice. Forms a working hypothesis about the
    career-limiting pattern, then generates reflection questions phrased as
    observations — leading with the evidence observed, then inviting the employee
    to confirm, refine, or push back. The pattern label is never revealed.

    Falls back gracefully if the API call fails — pipeline must not block here.

    Returns a MirrorResult with:
      hypothesis — internal string passed to analyse_structured() as primed context.
                   Never shown to the user.
      questions  — list of 1-2 strings rendered to the user in the mirror stage.
    """
    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=MAX_TOKENS_CONFIDENCE,
            system=MIRROR_SYSTEM_PROMPT,
            tools=[MIRROR_TOOL],
            tool_choice={"type": "tool", "name": "generate_mirror_questions"},
            messages=[{
                "role": "user",
                "content": format_answers(reflection_answers, investigation_answers),
            }],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_mirror_questions":
                hypothesis = block.input.get("hypothesis", "")
                questions = block.input.get("questions", [])
                if hypothesis and questions:
                    return MirrorResult(hypothesis=hypothesis, questions=questions)

    except Exception as e:
        print(f"⚠️  Mirror stage failed: {e}", file=sys.stderr)

    # Fallback — pipeline continues with a broad open question
    return MirrorResult(
        hypothesis="pattern unclear — proceeding without primed hypothesis",
        questions=MIRROR_FALLBACK_QUESTIONS,
    )
