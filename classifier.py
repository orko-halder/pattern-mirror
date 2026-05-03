"""
Pattern Mirror — readiness classifier.

Reads the 6 answers and produces a delivery profile before the main analysis runs.
The profile shapes how the pattern is delivered, not what is found.

Active parameters (classified by Claude):
  - self_awareness  : how much the person already sees their patterns
  - fragility_risk  : risk that direct delivery triggers shame spiral or shutdown

Derived parameter (computed in Python from active parameters):
  - delivery_mode   : direct | paced | gentle — see derive_delivery_mode()

Future parameters are tracked in the project backlog (Arka_CCA_Sprint_Tracker.md).
To activate one: add to CLASSIFIER_TOOL schema, system prompt signals, derive_delivery_mode(), safe default, and log_profile().
"""

from anthropic import Anthropic
from prompts import CLASSIFIER_TOOL
from validator import format_answers
from config import HAIKU_MODEL, MAX_TOKENS_CLASSIFY, DeliveryMode


def derive_delivery_mode(profile: dict) -> DeliveryMode:
    """Deterministically derive delivery mode from the classified profile.

    Fragility is the dominant signal — it determines the floor.
    Self-awareness is the tiebreaker only when fragility is low.

    Future parameters plug in here:
      - resistance: HIGH resistance → anchor pattern in person's own words regardless of mode
      - psychological_vocabulary: LOW vocabulary → plain language register regardless of mode
    """
    fragility = profile.get("fragility_risk", "medium")
    awareness = profile.get("self_awareness", "medium")

    if fragility == "high":
        return "gentle"
    if fragility == "medium":
        return "paced"
    # fragility is low — awareness decides
    if awareness == "high":
        return "direct"
    return "paced"


def classify_readiness(client: Anthropic, answers: list[dict]) -> dict:
    """Assess the person's readiness profile from their answers.

    Returns a profile dict with active parameters + derived delivery_mode.
    Returns a safe default on failure — never blocks the main pipeline.
    """
    user_content = format_answers(answers)

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=MAX_TOKENS_CLASSIFY,
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
                if not block.input:
                    print("⚠️  Classifier returned empty profile — using default.")
                    break
                profile = dict(block.input)
                profile["delivery_mode"] = derive_delivery_mode(profile)
                return profile

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
