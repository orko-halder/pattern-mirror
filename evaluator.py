"""
Pattern Mirror — output evaluation.

Grades the analysis on pattern accuracy and protocol deployability.
Runs as a post-analysis quality check using Haiku.
"""

from anthropic import Anthropic
from prompts import EVALUATOR_TOOL, EVALUATOR_SYSTEM_PROMPT
from config import HAIKU_MODEL, MAX_TOKENS_EVALUATE


def evaluate_output(client: Anthropic, analysis_output: str) -> None:
    """Use Claude to grade the analysis output on two quality dimensions."""
    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS_EVALUATE,
        system=EVALUATOR_SYSTEM_PROMPT,
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
