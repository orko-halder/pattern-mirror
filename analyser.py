"""
Pattern Mirror — analysis pipeline.

Sends validated answers to Claude and returns the pattern analysis.
Two modes: structured JSON (default) and streaming text (kept for future toggle).
"""

import os
import functools
import anthropic as anthropic_sdk

from dataclasses import dataclass, field
from typing import Optional
from anthropic import Anthropic
from prompts import SYSTEM_PROMPT, ANALYSIS_TOOL, build_system_prompt
from validator import format_answers
from tools import LOOKUP_FRAMEWORK_TOOL, WEB_SEARCH_TOOL, handle_tool_call
from classifier import classify_readiness, log_profile
from file_context import build_document_block
from config import SONNET_MODEL, THINKING_BUDGET, MAX_TOKENS_ANALYSE, MAX_TOKENS_ANALYSE_SHORT, MAX_TOOL_ITERATIONS, PROMPT_CACHING_BETA


class PipelineError(Exception):
    """Raised when the analysis pipeline fails. Message is safe to show to the user."""
    pass


@dataclass
class AnalysisResult:
    data: dict = field(default_factory=dict)        # structured JSON from Claude
    text: str = ""                                   # formatted string for evaluator
    citations: list[dict] = field(default_factory=list)  # source URLs from web search
    usage: dict = field(default_factory=dict)        # cumulative token usage across all API calls


def analyse_structured(
    client: Anthropic,
    answers: list[dict],
    extended_thinking: bool = False,
    context_file_id: Optional[str] = None,
) -> AnalysisResult:
    """Send answers to Claude, get back structured JSON.
    Returns AnalysisResult(data, text, citations).
    Raises PipelineError on failure — message is user-friendly.

    Tool use loop:
    1. Claude may call lookup_framework or web_search before producing the final analysis
    2. We execute the tool and send the result back
    3. Claude continues until it calls pattern_analysis to return the structured output

    extended_thinking: if True, enables extended thinking on the first (agentic) call only.
    Disabled on the force_final call — forced tool_choice + thinking has constraints.

    context_file_id: optional Anthropic file ID from client.beta.files.upload().
    When provided, the file is prepended as a document block in the user message.
    Uses client.beta.messages.create with the files-api beta header for all calls
    in the loop (the first message retains the document block throughout).
    """
    # Classify readiness — profile shapes delivery mode
    profile = classify_readiness(client, answers)
    log_profile(profile)

    # Wrap system prompt as a content block with cache_control.
    # The system prompt (~2000 tokens) is identical across all calls in the tool use loop.
    # Marking it ephemeral caches it on call 1; calls 2 and 3 read from cache at 0.10× cost.
    system = [{
        "type": "text",
        "text": build_system_prompt(profile["delivery_mode"]),
        "cache_control": {"type": "ephemeral"},
    }]

    user_text = format_answers(answers)

    # If a context file was uploaded, prepend it as a document block.
    # The beta header is required for all calls in the loop because the document
    # block lives in the first user message which is replayed on every turn.
    # Combine betas: files API + prompt caching.
    if context_file_id:
        user_content = [build_document_block(context_file_id), {"type": "text", "text": user_text}]
        _create = functools.partial(
            client.beta.messages.create,
            betas=[PROMPT_CACHING_BETA, "files-api-2025-04-14"],
        )
    else:
        user_content = user_text
        _create = functools.partial(
            client.beta.messages.create,
            betas=[PROMPT_CACHING_BETA],
        )

    messages = [{"role": "user", "content": user_content}]
    tools = [LOOKUP_FRAMEWORK_TOOL, ANALYSIS_TOOL]
    if os.environ.get("TAVILY_API_KEY"):
        tools.insert(1, WEB_SEARCH_TOOL)

    # Mark the last tool for caching — caches the entire tools prefix up to this point.
    # Don't mutate the original dicts (module-level constants); build a new list.
    tools = tools[:-1] + [{**tools[-1], "cache_control": {"type": "ephemeral"}}]

    citations = []
    force_final = False
    total_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    max_tokens = max(MAX_TOKENS_ANALYSE, THINKING_BUDGET + 1000) if extended_thinking else MAX_TOKENS_ANALYSE_SHORT

    try:
        for _iteration in range(MAX_TOOL_ITERATIONS):
            # Extended thinking only on the first call — not when forcing pattern_analysis
            thinking_param = (
                {"type": "enabled", "budget_tokens": THINKING_BUDGET}
                if extended_thinking and not force_final
                else {"type": "disabled"}
            )

            response = _create(
                model=SONNET_MODEL,
                max_tokens=max_tokens,
                thinking=thinking_param,
                system=system,
                tools=tools,
                tool_choice={"type": "tool", "name": "pattern_analysis"} if force_final else {"type": "auto"},
                messages=messages,
            )

            # Accumulate token usage across all calls in the loop
            total_usage["input_tokens"] += response.usage.input_tokens
            total_usage["output_tokens"] += response.usage.output_tokens
            total_usage["cache_creation_input_tokens"] += getattr(response.usage, "cache_creation_input_tokens", 0) or 0
            total_usage["cache_read_input_tokens"] += getattr(response.usage, "cache_read_input_tokens", 0) or 0

            # Truncation on the first call — fail cleanly rather than silently skipping tool enrichment
            if response.stop_reason == "max_tokens" and not force_final:
                raise PipelineError("Analysis was interrupted before completing. Please try again.")

            # Truncation on the forced call — retry with larger budget
            # Messages are unchanged so Claude starts the schema fresh with more room
            if response.stop_reason == "max_tokens" and force_final:
                if max_tokens >= MAX_TOKENS_ANALYSE:
                    raise PipelineError("Analysis was too large to complete. Please try again.")
                print(f"⚠️  Analysis truncated at {max_tokens} tokens — retrying at {MAX_TOKENS_ANALYSE}.")
                max_tokens = MAX_TOKENS_ANALYSE
                continue

            if response.stop_reason == "model_context_window_exceeded":
                raise PipelineError("The conversation is too long to analyse. Please start a new session.")

            if response.stop_reason == "end_turn":
                break

            tool_calls = [b for b in response.content if b.type == "tool_use"]

            if not tool_calls:
                break

            # If Claude called pattern_analysis — we're done
            for block in tool_calls:
                if block.name == "pattern_analysis":
                    if not block.input:
                        raise PipelineError("The analysis came back empty. Please try again.")
                    formatted = format_structured_output(block.input)
                    return AnalysisResult(data=block.input, text=formatted, citations=citations, usage=total_usage)

            # Claude called a lookup tool — execute it, collect citations, add to history
            for b in tool_calls:
                print(f"\n🔧 Tool called: {b.name} | input: {b.input}")

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in tool_calls:
                envelope = handle_tool_call(block.name, block.input)
                if envelope["status"] == "error":
                    print(f"⚠️ Tool error ({block.name}): {envelope['content']}")
                citations.extend(envelope["metadata"].get("citations", []))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": envelope["content"]
                })

            messages.append({"role": "user", "content": tool_results})
            force_final = True

    except anthropic_sdk.APIConnectionError:
        raise PipelineError("Couldn't reach the Anthropic API. Check your internet connection and try again.")
    except anthropic_sdk.RateLimitError:
        raise PipelineError("Too many requests. Wait a moment and try again.")
    except anthropic_sdk.APIStatusError as e:
        raise PipelineError(f"API error ({e.status_code}). Please try again.")
    except PipelineError:
        raise
    except Exception as e:
        raise PipelineError(f"Something went wrong during analysis. Please try again. ({type(e).__name__})")

    raise PipelineError("The analysis didn't complete. Please try again.")


def format_structured_output(data: dict) -> str:
    """Render a structured analysis dict as readable CLI output."""
    lines = []

    core = data.get("core_pattern", {})
    lines.append("**Core Pattern**")
    lines.append(core.get("name", ""))
    lines.append(core.get("plain_summary", ""))
    lines.append(core.get("description", ""))

    secondary = data.get("secondary_pattern")
    if secondary:
        lines.append("\n**Secondary Pattern**")
        lines.append(secondary.get("name", ""))
        lines.append(secondary.get("description", ""))

    lines.append("\n**Evidence**")
    for quote in data.get("evidence", []):
        lines.append(f'  "{quote}"')

    lines.append("\n**Where It Shows Up**")
    lines.append("  " + ", ".join(data.get("domains", [])))

    lines.append("\n**What It's Protecting You From**")
    lines.append(data.get("payoff", ""))

    protocol = data.get("protocol", {})
    lines.append("\n**The Protocol**")
    lines.append(f"Detection: {protocol.get('detection_trigger', '')}")
    for i, step in enumerate(protocol.get("steps", []), 1):
        lines.append(f"  {i}. {step}")
    lines.append(f"If you can't stop right now: {protocol.get('fallback_mid_activation', '')}")
    lines.append(f"If you're completely overwhelmed: {protocol.get('fallback_shutdown', '')}")
    fc = protocol.get("failure_condition", {})
    if isinstance(fc, dict):
        lines.append(f"If it goes wrong: {fc.get('if_wrong', '')}")
        lines.append(f"If it goes right: {fc.get('if_right', '')}")
    else:
        lines.append(f"Failure condition: {fc}")

    return "\n".join(lines)


def analyse(client: Anthropic, answers: list[dict]) -> str:
    """Send answers to Claude and stream the pattern analysis. Returns full output.

    Kept for the Week 3 streaming toggle in Streamlit.
    """
    user_content = format_answers(answers)
    full_output = []

    with client.messages.stream(
        model=SONNET_MODEL,
        max_tokens=MAX_TOKENS_ANALYSE_SHORT,
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
