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
Name the pattern in plain language — short, memorable, something the person can recall in the moment it activates. Avoid clinical labels. Save precision for the description that follows. Then describe it in 2-3 sentences: what it is, how it operates, what it protects.

**Secondary Pattern** (include only if clearly present)
A distinct second pattern if the answers reveal one. Skip this section entirely if not applicable.

**Evidence**
Quote 2-3 specific phrases from their answers that reveal the pattern. Use their exact words. Do not paraphrase.

**Where It Shows Up**
Based on their answers, name 2-3 domains where this pattern operates (work, relationships, self-perception, etc.)

**The Payoff**
What does this pattern make sure never happens? What is it protecting them from?

**The Protocol**
One actionable micro-sequence they can use the next time this pattern activates. Concrete. Specific. Deployable tomorrow morning. Not advice — a sequence of steps. End with one failure condition: what should the person do if the feared outcome actually occurs when they try the protocol?

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
    1. RELEVANCE — is each answer actually responding to its question?
    2. EFFORT — is the person genuinely engaging, or giving empty non-answers?

    Note: recurring themes across answers are expected and valid — that's the pattern.
    Do NOT flag answers for being thematically similar.
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

    failed = False

    relevance_line = lines.get("RELEVANCE", "")
    if "INVALID" in relevance_line:
        reason = relevance_line.split("INVALID", 1)[1].strip(" —-")
        print(f"\n⚠️  Answers off-topic: {reason}")
        print("Please run again and answer each question directly.")
        failed = True

    effort_line = lines.get("EFFORT", "")
    if "INVALID" in effort_line:
        reason = effort_line.split("INVALID", 1)[1].strip(" —-")
        print(f"\n⚠️  Answers too brief: {reason}")
        print("Please run again and engage genuinely with each question.")
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


def analyse(client: Anthropic, answers: list[dict]) -> str:
    """Send answers to Claude and stream the pattern analysis. Returns full output."""
    print("\n" + "=" * 60)
    print("PATTERN ANALYSIS")
    print("=" * 60 + "\n")

    user_content = format_answers(answers)
    full_output = []

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
            full_output.append(text)

    print("\n")
    return "".join(full_output)


def evaluate_output(client: Anthropic, analysis_output: str) -> None:
    """Use Claude to grade the analysis output on three quality dimensions."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=(
            "You are a quality evaluator for a human psychological pattern analysis tool. "
            "Score the analysis on two dimensions, each from 1 to 10.\n\n"
            "PATTERN ACCURACY (1-10): Did it identify a specific, precise pattern — or a vague generalisation?\n"
            "1 = generic and could apply to anyone. 10 = precise, specific, clearly grounded in the answers.\n\n"
            "PROTOCOL DEPLOYABILITY (1-10): Is the protocol concrete enough to use tomorrow morning?\n"
            "1 = generic advice. 10 = specific steps deployable in a real moment of pattern activation.\n\n"
            "Reply in this exact format:\n"
            "PATTERN ACCURACY: X/10 — one short reason\n"
            "PROTOCOL DEPLOYABILITY: X/10 — one short reason\n"
            "OVERALL: X/20\n"
            "STRENGTHS: one sentence — what the analysis does well\n"
            "WEAKNESSES: one sentence — what the analysis could improve\n"
            "REASONING: one sentence — why you gave the scores you did, based on the content of the analysis output\n"
            "---"
        ),
        stop_sequences=["---"],
        messages=[
            {"role": "user", "content": analysis_output}
        ],
    )

    print("\n" + "=" * 60)
    print("QUALITY EVALUATION")
    print("=" * 60 + "\n")
    print(response.content[0].text.strip())
    print()


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

    analysis_output = analyse(client, answers)
    evaluate_output(client, analysis_output)


if __name__ == "__main__":
    main()
