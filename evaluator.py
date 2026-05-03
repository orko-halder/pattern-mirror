"""
Pattern Mirror — output evaluation.

Grades the analysis on pattern accuracy and protocol deployability.
Runs as a post-analysis quality check using Haiku.
"""

from anthropic import Anthropic
from prompts import EVALUATOR_TOOL
from config import HAIKU_MODEL, MAX_TOKENS_EVALUATE


def evaluate_output(client: Anthropic, analysis_output: str) -> None:
    """Use Claude to grade the analysis output on two quality dimensions."""
    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS_EVALUATE,
        system=(
            "You are a quality evaluator for a human psychological pattern analysis tool. "
            "Score the analysis on two dimensions, each from 1 to 10.\n\n"
            "PATTERN ACCURACY (1-10): Did it identify a specific, precise pattern — or a vague generalisation?\n"
            "1 = generic and could apply to anyone. 10 = precise, specific, clearly grounded in the answers.\n\n"
            "PROTOCOL DEPLOYABILITY (1-10): Is the protocol concrete enough to use tomorrow morning?\n"
            "1 = generic advice. 10 = specific steps deployable in a real moment of pattern activation.\n\n"
            "Call the quality_evaluation tool with your scores and reasoning."
        ),
        tools=[EVALUATOR_TOOL],
        tool_choice={"type": "tool", "name": "quality_evaluation"},
        messages=[{"role": "user", "content": analysis_output}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "quality_evaluation":
            r = block.input
            accuracy = r.get("pattern_accuracy", 0)
            deployability = r.get("protocol_deployability", 0)
            print("\n" + "=" * 60)
            print("QUALITY EVALUATION")
            print("=" * 60 + "\n")
            print(f"PATTERN ACCURACY: {accuracy}/10 — {r.get('pattern_accuracy_reason', '')}")
            print(f"PROTOCOL DEPLOYABILITY: {deployability}/10 — {r.get('protocol_deployability_reason', '')}")
            print(f"OVERALL: {accuracy + deployability}/20")
            print(f"STRENGTHS: {r.get('strengths', '')}")
            print(f"WEAKNESSES: {r.get('weaknesses', '')}")
            print(f"REASONING: {r.get('reasoning', '')}")
            print()
            return

    print("\n⚠️  Quality evaluation unavailable.")
