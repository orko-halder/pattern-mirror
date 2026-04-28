"""
Pattern Mirror — readiness classifier.

Reads the 6 answers and produces a delivery profile before the main analysis runs.
The profile shapes how the pattern is delivered, not what is found.

Currently: logs to terminal only. Delivery adaptation wired in Step 2.
"""

from anthropic import Anthropic
from validator import format_answers


CLASSIFIER_TOOL = {
    "name": "readiness_profile",
    "description": "Return the readiness profile for this reflection session.",
    "input_schema": {
        "type": "object",
        "properties": {
            "self_awareness": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": (
                    "How much the person already sees their own patterns. "
                    "HIGH: ownership language, nuance, prior reflection evident. "
                    "MEDIUM: partial ownership, some externalizing. "
                    "LOW: externalizes consistently, sees themselves only as reaction to others."
                )
            },
            "fragility_risk": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": (
                    "Risk that direct delivery triggers shutdown, shame spiral, or rejection. "
                    "HIGH: shame-heavy language, catastrophizing, very defended answers, 'always/never' absolutes. "
                    "MEDIUM: some defensiveness or anxiety markers but stable overall. "
                    "LOW: answers feel grounded, curious, or matter-of-fact about difficulty."
                )
            },
            "delivery_mode": {
                "type": "string",
                "enum": ["direct", "paced", "gentle"],
                "description": (
                    "Derived from self_awareness + fragility_risk. "
                    "DIRECT: high awareness + low fragility — name the pattern clearly, trust them to hold it. "
                    "PACED: medium awareness or medium fragility — acknowledge the cost before naming the pattern. "
                    "GENTLE: low awareness or high fragility — frame what happened to them before what they're doing."
                )
            },
            "signal_notes": {
                "type": "string",
                "description": (
                    "1-2 sentences on the specific signals that drove this classification. "
                    "Quote exact phrases from their answers where possible."
                )
            }
        },
        "required": ["self_awareness", "fragility_risk", "delivery_mode", "signal_notes"]
    }
}


def classify_readiness(client: Anthropic, answers: list[dict]) -> dict:
    """Assess the person's self-awareness level and fragility risk from their answers.

    Returns a readiness profile dict:
    {
        "self_awareness": "low" | "medium" | "high",
        "fragility_risk": "low" | "medium" | "high",
        "delivery_mode": "direct" | "paced" | "gentle",
        "signal_notes": str
    }

    Returns a safe default on failure — never blocks the main pipeline.
    """
    user_content = format_answers(answers)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=(
                "You are a readiness classifier for a psychological pattern analysis tool. "
                "Your job is to assess how a person's answers reveal their current capacity "
                "to receive and integrate direct feedback about themselves.\n\n"
                "Read the 6 answers as a set. Look for:\n\n"
                "SELF-AWARENESS signals:\n"
                "- Ownership language: 'I notice I...', 'I tend to...', 'I know I do this'\n"
                "- Prior reflection: references to therapy, patterns they've seen before\n"
                "- Nuance: holding complexity, acknowledging their own role in outcomes\n"
                "- Externalizing: 'they made me feel', 'it just happened', 'people always'\n\n"
                "FRAGILITY signals:\n"
                "- Shame language: 'I'm terrible at', 'I hate that I', 'I'm such a'\n"
                "- Catastrophizing: 'everything falls apart', 'nothing ever works'\n"
                "- Heavy defense: very short answers, deflections, answering a different question\n"
                "- Anxiety markers: urgency, hypervigilance language, worst-case framing\n\n"
                "Important: vague answers are ambiguous — they can signal defense OR limited "
                "self-vocabulary. Weight other signals before concluding on vagueness alone.\n\n"
                "Call the readiness_profile tool with your assessment."
            ),
            tools=[CLASSIFIER_TOOL],
            tool_choice={"type": "tool", "name": "readiness_profile"},
            messages=[{"role": "user", "content": user_content}]
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "readiness_profile":
                return block.input

    except Exception as e:
        print(f"⚠️  Classifier failed ({type(e).__name__}) — using default profile.")

    # Safe default — never block the pipeline
    return {
        "self_awareness": "medium",
        "fragility_risk": "medium",
        "delivery_mode": "paced",
        "signal_notes": "Classifier unavailable — default profile applied."
    }


def log_profile(profile: dict) -> None:
    """Print the readiness profile to the terminal."""
    print("\n── Readiness Profile ──────────────────────────────────────")
    print(f"  Self-awareness : {profile['self_awareness'].upper()}")
    print(f"  Fragility risk : {profile['fragility_risk'].upper()}")
    print(f"  Delivery mode  : {profile['delivery_mode'].upper()}")
    print(f"  Signal notes   : {profile['signal_notes']}")
    print("────────────────────────────────────────────────────────────\n")
