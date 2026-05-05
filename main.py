"""
Pattern Mirror — CLI entrypoint.

Collects answers, runs validation, analysis, and evaluation.
All logic lives in prompts.py, validator.py, analyser.py, evaluator.py.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import QUESTIONS
from validator import validate_answers
from analyser import analyse_structured
from evaluator import evaluate_output


def collect_answers() -> list[dict]:
    """Ask each question and collect the user's answers."""
    print("\n" + "=" * 60)
    print("PATTERN MIRROR")
    print("=" * 60)
    print("\nAnswer each question honestly.")
    print("There are no right answers. Incomplete is fine.")
    print("Take your time.\n")

    messages = []

    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n{'─' * 60}")
        print(f"\n{question}\n")
        answer = input("Your answer: ").strip()
        messages.append({
            "question": f"Q{i}",
            "answer": answer if answer else "[no answer given]"
        })

    return messages


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing ANTHROPIC_API_KEY. Copy .env.example to .env and fill it in."
        )

    client = Anthropic(api_key=api_key)
    answers = collect_answers()

    print("\nChecking input quality...")
    errors = validate_answers(client, answers)
    if errors:
        for error in errors:
            print(f"✗ {error}")
        raise SystemExit(1)

    print("\nRunning analysis...")
    analysis_data, analysis_output = analyse_structured(client, answers)

    print("\n" + "=" * 60)
    print("PATTERN ANALYSIS")
    print("=" * 60 + "\n")
    print(analysis_output)
    print()

    evaluate_output(client, analysis_output)


if __name__ == "__main__":
    main()
