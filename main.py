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

The person's answers are provided in a <reflection_session> block. Each <answer> tag contains their response to one question, identified by its Q number.

Read the 7 answers as a set, not individually. Look for:
- The same belief or fear surfacing across multiple questions under different framings
- Linguistic markers: deletions ("it just didn't work out"), distortions ("they always do this"), generalisations ("I never...")
- What is missing — vague answers, deflections, and one-word responses are pattern signals, not failures
- The payoff in Q7 — this explains why the pattern in Q1-Q6 keeps recurring

## Reasoning process

Before writing your output, work through these five points internally:

1. What is the single central pattern running across the most answers? Name it precisely.
2. What specific phrases from their answers are the strongest evidence? Quote them exactly.
3. Could this pattern be integrated or resolved rather than actively defensive? What in the answers suggests active defence vs genuine wholeness?
4. What is the payoff — what does this pattern make sure never happens?
5. Do the answers point to one central pattern or two distinct patterns operating simultaneously? If two, name both. If one is clearly dominant, name it as Core and note the secondary briefly under Evidence.

Only after working through these five points, write the structured output.

## Output format

Respond in this exact structure:

**Core Pattern**
Name the primary pattern in one precise phrase. Then describe it in 2-3 sentences: what it is, how it operates, what it protects.

**Secondary Pattern** (include only if clearly present)
A distinct second pattern if the answers reveal one. Skip this section entirely if not applicable.

**Evidence**
Quote 2-3 specific phrases from their answers that reveal the pattern. Use their exact words. Do not paraphrase.

**Where It Shows Up**
Based on their answers, name 2-3 domains where this pattern operates (work, relationships, self-perception, etc.)

**The Payoff**
What does this pattern make sure never happens? What is it protecting them from?

**The Protocol**
One actionable micro-sequence they can use the next time this pattern activates. Concrete. Specific. Deployable tomorrow morning. Not advice — a sequence of steps.

## Tone

Precise. Direct. Warm but not soft. You are not confirming their self-image — you are reflecting what their answers actually reveal. If the answers are vague or defended, name that directly.

Do not hedge with phrases like "this might suggest" or "it's possible that" — state observations directly.

Do not offer generic advice, therapeutic referrals, or motivational language in any section.

If answers are sparse or vague, name the defensiveness explicitly rather than filling gaps with assumptions.

Do not summarise what the person said — analyse what it reveals."""


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


def validate_answers(client: Anthropic, answers: list[dict]) -> bool:
    """Use Claude to check answer quality before analysis.

    Two checks:
    1. DISTINCTNESS — are answers genuinely different from each other?
    2. RELEVANCE — is each answer actually responding to its question?
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
        model="claude-sonnet-4-5",
        max_tokens=150,
        system=(
            "You are an input quality checker for a psychological reflection tool. "
            "You have two jobs:\n\n"
            "1. DISTINCTNESS: Are the answers genuinely distinct responses to different questions, "
            "or is the person repeating variations of the same answer across all questions?\n\n"
            "2. RELEVANCE: Is each answer actually responding to its question, "
            "or is the person writing something unrelated or random?\n\n"
            "Reply in this exact format:\n"
            "DISTINCTNESS: VALID or INVALID — one short reason\n"
            "RELEVANCE: VALID or INVALID — one short reason\n\n"
            "Be strict. An answer that ignores its question entirely is INVALID for relevance. "
            "Answers that all address the same topic are INVALID for distinctness."
        ),
        messages=[
            {"role": "user", "content": paired}
        ],
    )

    result = response.content[0].text.strip()
    lines = {line.split(":")[0].strip(): line for line in result.splitlines() if ":" in line}

    failed = False

    distinctness_line = lines.get("DISTINCTNESS", "")
    if "INVALID" in distinctness_line:
        reason = distinctness_line.split("INVALID", 1)[1].strip(" —-")
        print(f"\n⚠️  Answers too similar: {reason}")
        print("Please run again and answer each question from a different angle.")
        failed = True

    relevance_line = lines.get("RELEVANCE", "")
    if "INVALID" in relevance_line:
        reason = relevance_line.split("INVALID", 1)[1].strip(" —-")
        print(f"\n⚠️  Answers off-topic: {reason}")
        print("Please run again and answer each question directly.")
        failed = True

    if failed:
        print()
        return False

    return True


def format_answers(answers: list[dict]) -> str:
    """Format answers into XML-tagged block for the prompt."""
    formatted = "<reflection_session>\n"
    for item in answers:
        formatted += f"  <answer id=\"{item['question']}\">{item['answer']}</answer>\n"
    formatted += "</reflection_session>"
    return formatted


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

    print("\nChecking input quality...")
    if not validate_answers(client, answers):
        raise SystemExit(1)

    analyse(client, answers)


if __name__ == "__main__":
    main()
