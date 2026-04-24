"""
Pattern Mirror — output evaluation.

Grades the analysis on pattern accuracy and protocol deployability.
Runs as a post-analysis quality check using Haiku.
"""

from anthropic import Anthropic


def evaluate_output(client: Anthropic, analysis_output: str) -> None:
    """Use Claude to grade the analysis output on two quality dimensions."""
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
