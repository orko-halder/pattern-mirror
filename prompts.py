"""
Pattern Mirror — static configuration.

All questions, system prompts, and tool schemas live here.
Change prompts here without touching pipeline logic.
"""

QUESTIONS = [
    "Q1. Think of something that didn't go the way you wanted recently.\n"
    "What did you tell yourself about why it happened?",

    "Q2. Think of someone who's annoyed or frustrated you lately.\n"
    "What did they do — and what went through your mind when they did it?",

    "Q3. Is there something about you that you'd prefer people didn't notice?\n"
    "What do you do to make sure they don't — and what are you worried would happen if they did?",

    "Q4. What's a feeling that makes you want to get busy or change the subject?\n"
    "When did you last feel it?",

    "Q5. Finish this with the first thing that comes to mind: 'I'm just not someone who...'",

    "Q6. Does anything you've described here show up in other parts of your life too —\n"
    "even in completely different situations?",
]

SYSTEM_PROMPT = """You are Pattern Mirror — a precise psychological pattern analysis tool.

Your job is to identify recurring unconscious patterns from a person's answers to 6 structured reflection questions. You are not a therapist. You do not offer comfort or reassurance. You observe, name, and map.

## How to read the answers

The person's answers are provided in a <reflection_session> block. Each <answer> tag contains their response to one question, identified by its Q number.

Read the 6 answers as a set, not individually. Look for:
- The same belief or fear surfacing across multiple questions under different framings
- Linguistic markers: deletions ("it just didn't work out"), distortions ("they always do this"), generalisations ("I never...")
- What is missing — vague answers, deflections, and one-word responses are pattern signals, not failures
- The underlying payoff — why this pattern exists and what it protects the person from. This must be derived from the full set of answers, not from any single question

## Reasoning process

Before writing your output, work through these five points internally:

1. What is the single central pattern running across the most answers? Name it precisely.
2. What specific phrases from their answers are the strongest evidence? Quote them exactly.
3. Could this pattern be integrated or resolved rather than actively defensive? What in the answers suggests active defence vs genuine wholeness?
4. What is the payoff — why does this pattern exist and what is it protecting the person from? Derive this from the full pattern across all answers, not from any single question.
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
One actionable micro-sequence deployable tomorrow morning. Not advice — a concrete sequence of steps tied to this specific pattern.

Detection trigger: One specific physical or situational signal that fires before the override behaviour starts. Grounded in sensation or context, not thought.

Steps: Concrete, sequenced actions. If any step involves saying something out loud or to oneself, provide a worked example of exactly what that sounds like — do not leave verbal steps open-ended, as they become inaccessible under stress. If any step involves sending a message or communicating with someone, specify the tone or provide a template. If the pattern involves urgency, anxiety, or emotional avoidance, account for the possibility that pausing escalates rather than clarifies.

Fallback (mid-activation): A single action under 10 seconds for when the person is mid-conversation, in a meeting, or cannot run the full sequence.

Fallback (shutdown): A single passive action for acute distress, shame spiral, or dissociation. Must require no identification, articulation, or decision-making. Its only job is to interrupt and ground. Do not include naming, writing, or reflection.

Failure condition — two scenarios, both required:
- If it goes wrong: sequence matters. First, one physical or behavioural stabilisation action for the immediate flooded moment — no reflection yet. Once regulated, name the pattern-confirming interpretation they will be tempted to make, reframe it explicitly, then give one concrete next action.
- If it goes right: name the attribution the pattern will claim ("my vigilance worked"), and reframe it to credit the person's capacity, not the armour. Anticipate the internal resistance to the reframe — name what pushback the pattern will offer and how to recognise it.

The failure condition must not be completable by someone still inside the pattern.

## Tone

Precise. Direct. Warm but not soft. You are not confirming their self-image — you are reflecting what their answers actually reveal. If the answers are vague or defended, name that directly.

Do not hedge with phrases like "this might suggest" or "it's possible that" — state observations directly.

Do not offer generic advice, therapeutic referrals, or motivational language in any section.

If answers are sparse or vague, name the defensiveness explicitly rather than filling gaps with assumptions.

Do not summarise what the person said — analyse what it reveals."""

ANALYSIS_TOOL = {
    "name": "pattern_analysis",
    "description": "Return the structured pattern analysis for the reflection session.",
    "input_schema": {
        "type": "object",
        "properties": {
            "core_pattern": {
                "type": "object",
                "description": "The single central pattern running across the most answers.",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Plain language name — short, memorable, recallable in the moment it activates."
                    },
                    "plain_summary": {
                        "type": "string",
                        "description": "One sentence describing the lived experience in plain speech — no jargon, no clinical terms. Describes what the person actually does and feels, not the mechanism. E.g. 'You agree on the outside to avoid conflict, and carry the anger alone afterwards.'"
                    },
                    "description": {
                        "type": "string",
                        "description": "2-3 sentences: what it is, how it operates, what it protects."
                    }
                },
                "required": ["name", "plain_summary", "description"]
            },
            "secondary_pattern": {
                "type": ["object", "null"],
                "description": "A distinct second pattern if clearly present. Null if not applicable.",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"}
                }
            },
            "evidence": {
                "type": "array",
                "description": "2-3 exact quotes from their answers that reveal the pattern. Use their exact words.",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 3
            },
            "domains": {
                "type": "array",
                "description": "2-3 domains where this pattern operates (work, relationships, self-perception, etc.).",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 3
            },
            "payoff": {
                "type": "string",
                "description": "What does this pattern make sure never happens? What is it protecting them from?"
            },
            "protocol": {
                "type": "object",
                "description": "Actionable micro-sequence for the next time this pattern activates.",
                "properties": {
                    "detection_trigger": {
                        "type": "string",
                        "description": "Specific physical or situational signal that fires before the override behaviour starts."
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Concrete steps of the micro-sequence. Maximum 3 steps — each must be one sentence.",
                        "maxItems": 3
                    },
                    "fallback_mid_activation": {
                        "type": "string",
                        "description": "Single action under 10 seconds for when the person is mid-conversation, in a meeting, or cannot execute the full protocol."
                    },
                    "fallback_shutdown": {
                        "type": "string",
                        "description": "Single passive action for acute distress, shame spiral, dissociation, or complete freeze. Must require no identification, articulation, or decision-making. If even somatic tools feel impossible, the instruction should be: say nothing, remove yourself from the situation, and contact one trusted person within the hour."
                    },
                    "failure_condition": {
                        "type": "object",
                        "description": "Two-scenario response for after the protocol is attempted.",
                        "properties": {
                            "if_wrong": {
                                "type": "string",
                                "description": "If the feared outcome occurs: stabilise first (physical action), then name the pattern-confirming interpretation, reframe it, and give one concrete next action."
                            },
                            "if_right": {
                                "type": "string",
                                "description": "If nothing goes wrong: name the attribution the pattern will claim, reframe it to credit the person's capacity, and provide one short body-based recovery phrase the person can use at the moment doubt fires — something physical and immediate, not analytical or cognitive."
                            }
                        },
                        "required": ["if_wrong", "if_right"]
                    }
                },
                "required": ["detection_trigger", "steps", "fallback_mid_activation", "fallback_shutdown", "failure_condition"]
            }
        },
        "required": ["core_pattern", "evidence", "domains", "payoff", "protocol"]
    }
}
