"""
Pattern Mirror — CLI entrypoint.

Week 2: Asks 7 reflection questions, collects answers, sends to Claude,
prints pattern analysis. Ugly is fine. No error handling yet.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv


QUESTIONS = [
    "Q1. What's something you've concluded about yourself that's uncomfortable to admit?\n"
    "When did that feel confirmed recently?",

    "Q2. What quality in others consistently irritates you?\n"
    "What does that behaviour say about them in your mind?",

    "Q3. What's something you believe would go wrong if you were truly seen?\n"
    "What are you currently doing to hide that?",

    "Q4. What feeling do you work hardest to avoid?\n"
    "When did it show up recently — even briefly?",

    "Q5. Finish this without thinking: 'I'm just not someone who...'",

    "Q6. Take one thing you've noticed about yourself so far — a belief, feeling, or way you reacted.\n"
    "Where else does that show up in your life, even in very different situations?",

    "Q7. In the situation you described — what did reacting that way help you avoid, feel, or maintain?",
]

SYSTEM_PROMPT = """You are Pattern Mirror — a precise psychological pattern analysis tool.

Your job is to identify recurring unconscious patterns from a person's answers to 7 structured reflection questions. You are not a therapist. You do not offer comfort or reassurance. You observe, name, and map.

## How to read the answers

Read the 7 answers as a set, not individually. Look for:
- The same belief or fear surfacing across multiple questions under different framings
- Linguistic markers: deletions ("it just didn't work out"), distortions ("they always do this"), generalisations ("I never...")
- What is missing — vague answers, deflections, and one-word responses are pattern signals, not failures
- The payoff in Q7 — this explains why the pattern in Q1-Q6 keeps recurring

## Output format

Respond in this exact structure:

**Core Pattern**
Name the primary pattern in one precise phrase. Then describe it in 2-3 sentences: what it is, how it operates, what it protects.

**Evidence**
Quote 2-3 specific phrases from their answers that reveal the pattern. Use their exact words. Do not paraphrase.

**Where It Shows Up**
Based on their answers, name 2-3 domains where this pattern operates (work, relationships, self-perception, etc.)

**The Payoff**
What does this pattern make sure never happens? What is it protecting them from?

**The Protocol**
One actionable micro-sequence they can use the next time this pattern activates. Concrete. Specific. Deployable tomorrow morning. Not advice — a sequence of steps.

## Tone

Precise. Direct. Warm but not soft. You are not confirming their self-image — you are reflecting what their answers actually reveal. If the answers are vague or defended, name that directly."""


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


def format_answers(answers: list[dict]) -> str:
    """Format answers into a clean block for the prompt."""
    formatted = "Here are the person's answers to the 7 reflection questions:\n\n"
    for item in answers:
        formatted += f"{item['question']}: {item['answer']}\n\n"
    return formatted.strip()


def analyse(client: Anthropic, answers: list[dict]) -> None:
    """Send answers to Claude and stream the pattern analysis."""
    print("\n" + "=" * 60)
    print("PATTERN ANALYSIS")
    print("=" * 60 + "\n")

    user_content = format_answers(answers)

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_content}
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print("\n")


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing ANTHROPIC_API_KEY. Copy .env.example to .env and fill it in."
        )

    client = Anthropic(api_key=api_key)
    answers = collect_answers()
    analyse(client, answers)


if __name__ == "__main__":
    main()
