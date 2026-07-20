"""
Pattern Mirror — Streamlit web app.

Four-layer flow:
  1. "reflection"   — user answers 5 career-progression questions + optional context file
  2. "investigation" — Sonnet generates 3-7 targeted investigation questions; user answers them
  3. "mirror"       — Sonnet forms internal hypothesis, generates 1-2 reflection questions
  4. Results rendered after user answers mirror questions

All logic imported from the existing pipeline modules.
"""

import os
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import QUESTIONS
from validator import validate_answers, validate_context_file, count_tokens_preflight
from analyser import analyse_structured, PipelineError
from middleware import pre_process, post_process
from file_context import upload_context_file, delete_file
from investigation import generate_investigation_questions
from mirror import generate_mirror_questions
from config import SONNET_MODEL


# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Pattern Mirror",
    page_icon="🪞",
    layout="centered"
)


# ── Client ───────────────────────────────────────────────────
@st.cache_resource
def get_client():
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Missing ANTHROPIC_API_KEY. Add it to your .env file.")
        st.stop()
    return Anthropic(api_key=api_key)


# ── Session state defaults ───────────────────────────────────
if "stage" not in st.session_state:
    st.session_state.stage = "reflection"
if "reflection_answers" not in st.session_state:
    st.session_state.reflection_answers = []
if "investigation_questions" not in st.session_state:
    st.session_state.investigation_questions = []
if "investigation_answers" not in st.session_state:
    st.session_state.investigation_answers = []
if "mirror_questions" not in st.session_state:
    st.session_state.mirror_questions = []
if "hypothesis" not in st.session_state:
    st.session_state.hypothesis = ""
if "extended_thinking" not in st.session_state:
    st.session_state.extended_thinking = False
if "context_file_id" not in st.session_state:
    st.session_state.context_file_id = None


# ── Header ───────────────────────────────────────────────────
st.title("🪞 Pattern Mirror")
st.caption("Answer honestly. Incomplete is fine. There are no right answers.")
st.divider()


# ════════════════════════════════════════════════════════════
# LAYER 1: reflection — 5 questions + context file + Continue
# ════════════════════════════════════════════════════════════
if st.session_state.stage == "reflection":

    # Context file (optional)
    uploaded_file = None
    with st.expander("📎 Add context (optional)"):
        st.caption(
            "Upload a previous journal entry, prior session notes, or related writing. "
            "Claude will read it before analysing your answers below."
        )
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["txt", "md", "pdf"],
            label_visibility="collapsed",
            key="context_file",
        )
        if uploaded_file:
            size_kb = len(uploaded_file.getvalue()) // 1024
            st.caption(f"**{uploaded_file.name}** — {size_kb} KB")

    st.divider()

    # Reflection questions
    st.subheader("Reflection")
    answers = []
    for i, question in enumerate(QUESTIONS, 1):
        st.markdown(f"**{question}**")
        answer = st.text_area(
            label=f"Q{i}",
            label_visibility="collapsed",
            placeholder="Your answer...",
            key=f"q{i}",
            height=100
        )
        answers.append({
            "question": f"Q{i}",
            "answer": answer.strip() if answer.strip() else "[no answer given]",
        })
        st.write("")

    st.divider()
    extended_thinking = st.toggle(
        "Extended thinking",
        value=False,
        help="Gives Claude more reasoning time before analysing. Produces deeper results on ambiguous or sparse answers. Uses more tokens."
    )
    continue_btn = st.button("Continue →", type="primary", use_container_width=True)

    if continue_btn:
        client = get_client()

        # Upload context file if provided
        context_file_id = None
        if uploaded_file is not None:
            try:
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    uf = upload_context_file(client, uploaded_file.getvalue(), uploaded_file.name)
                    context_file_id = uf.file_id
            except ValueError as e:
                st.error(str(e))
                st.stop()

            with st.spinner("Checking document relevance..."):
                relevance_warnings = validate_context_file(client, context_file_id)
            for warning in relevance_warnings:
                st.warning(warning)

        # Pre-processing
        pre = pre_process(answers, has_context_file=context_file_id is not None)
        if pre.warnings:
            for warning in pre.warnings:
                st.warning(warning)
        if pre.blocked:
            for error in pre.errors:
                st.error(error)
            if context_file_id:
                delete_file(client, context_file_id)
            st.stop()

        # Validation
        with st.spinner("Checking input quality..."):
            errors = validate_answers(client, answers)
        if errors:
            for error in errors:
                st.warning(error)
            st.info("Please revisit your answers and try again.")
            if context_file_id:
                delete_file(client, context_file_id)
            st.stop()

        # Generate investigation questions
        with st.spinner("Generating investigation questions..."):
            investigation_questions = generate_investigation_questions(client, answers)

        # Persist to session state and advance
        st.session_state.reflection_answers = answers
        st.session_state.investigation_questions = investigation_questions
        st.session_state.extended_thinking = extended_thinking
        st.session_state.context_file_id = context_file_id
        st.session_state.stage = "investigation"
        st.rerun()


# ════════════════════════════════════════════════════════════
# LAYER 2: investigation — dynamic questions + Continue / Back
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == "investigation":

    st.subheader("A few more questions")
    st.caption(
        "We're looking for whether the same pattern shows up across different areas of your work."
    )
    st.write("")

    investigation_answers = []
    for i, question in enumerate(st.session_state.investigation_questions, 1):
        st.markdown(f"**{question}**")
        answer = st.text_area(
            label=f"IQ{i}",
            label_visibility="collapsed",
            placeholder="Your answer...",
            key=f"iq{i}",
            height=100
        )
        investigation_answers.append({
            "question": question,
            "answer": answer.strip() if answer.strip() else "[no answer given]",
        })
        st.write("")

    st.divider()
    col_back, col_continue = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            # Return to reflection stage — clean up context file
            context_file_id = st.session_state.context_file_id
            if context_file_id:
                delete_file(get_client(), context_file_id)
            st.session_state.stage = "reflection"
            st.session_state.context_file_id = None
            st.rerun()
    with col_continue:
        continue_btn = st.button("Continue →", type="primary", use_container_width=True)

    if continue_btn:
        client = get_client()

        # Persist investigation answers before advancing — needed by mirror stage
        st.session_state.investigation_answers = investigation_answers

        # Generate mirror questions — Sonnet forms hypothesis + 1-2 reflection questions
        with st.spinner("Almost there — preparing final questions..."):
            mirror_result = generate_mirror_questions(
                client,
                st.session_state.reflection_answers,
                investigation_answers,
            )

        st.session_state.mirror_questions = mirror_result.questions
        st.session_state.hypothesis = mirror_result.hypothesis
        st.session_state.stage = "mirror"
        st.rerun()



# ════════════════════════════════════════════════════════════
# LAYER 3: mirror — 1-2 reflection questions
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == "mirror":

    st.subheader("Here's what we're seeing")
    st.caption(
        "Based on everything you've shared, we're reflecting back what we noticed. "
        "If something doesn't land quite right, say so — your response shapes the final analysis."
    )
    st.write("")

    mirror_answers = []
    for i, question in enumerate(st.session_state.mirror_questions, 1):
        st.markdown(f"**{question}**")
        answer = st.text_area(
            label=f"MQ{i}",
            label_visibility="collapsed",
            placeholder="Your answer...",
            key=f"mq{i}",
            height=100,
        )
        mirror_answers.append({
            "question": question,
            "answer": answer.strip() if answer.strip() else "[no answer given]",
            "hypothesis": st.session_state.hypothesis,
        })
        st.write("")

    st.divider()
    col_back, col_analyse = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.stage = "investigation"
            st.rerun()
    with col_analyse:
        analyse_btn = st.button("Analyse", type="primary", use_container_width=True)

    if analyse_btn:
        client = get_client()
        context_file_id = st.session_state.context_file_id
        result = None

        try:
            preflight_tokens = count_tokens_preflight(client, st.session_state.reflection_answers)

            st.divider()
            st.subheader("Pattern Analysis")

            try:
                spinner_msg = (
                    "Running analysis (extended thinking enabled)..."
                    if st.session_state.extended_thinking
                    else "Running analysis..."
                )
                with st.spinner(spinner_msg):
                    result = analyse_structured(
                        client,
                        st.session_state.reflection_answers,
                        extended_thinking=st.session_state.extended_thinking,
                        context_file_id=context_file_id,
                        investigation_answers=st.session_state.investigation_answers,
                        mirror_answers=mirror_answers,
                    )
            except PipelineError as e:
                st.error(str(e))
                st.stop()

        finally:
            if context_file_id:
                delete_file(client, context_file_id)
                st.session_state.context_file_id = None

        if not result or not result.data:
            st.error("The analysis came back empty. Please try again.")
            st.stop()

        # Cross-domain evidence check
        cross_domain = result.data.get("cross_domain_evidence", "partial")
        if cross_domain == "insufficient":
            st.info(
                "The answers didn't give us enough to confirm whether this pattern "
                "repeats across different areas of your work life. That's okay — it might be "
                "more situational than structural. Try again with more specific answers, "
                "or explore a different angle."
            )
            if st.button("Start a new reflection", use_container_width=True):
                for key in ["stage", "reflection_answers", "investigation_questions", "investigation_answers",
                            "mirror_questions", "hypothesis", "extended_thinking", "context_file_id"]:
                    st.session_state.pop(key, None)
                st.rerun()
            st.stop()

        if cross_domain == "partial":
            st.warning(
                "The pattern shows up in some areas but not all. The analysis below reflects "
                "what's confirmed — treat it as a hypothesis worth watching rather than a verdict."
            )

        # Post-processing — cost logging + safety filter
        post = post_process(result.data, result.usage, SONNET_MODEL)
        if post.warnings:
            for warning in post.warnings:
                st.warning(warning)
        with st.expander("📊 Token usage", expanded=False):
            st.caption(f"Preflight count (before analysis): {preflight_tokens:,} input tokens")
            st.caption(post.cost_summary)

        # Core pattern
        core = result.data.get("core_pattern", {})
        confidence = core.get("confidence", "")
        confidence_label = {"high": "🟢 High confidence", "medium": "🟡 Medium confidence", "low": "🔴 Low confidence"}.get(confidence, "")
        st.markdown(f"### {core.get('name', '')}")
        if confidence_label:
            st.caption(confidence_label)
        st.caption(core.get("plain_summary", ""))
        st.markdown(core.get("description", ""))

        # What progressors do
        if result.data.get("what_progressors_do"):
            st.markdown(f"*{result.data.get('what_progressors_do', '')}*")

        # Secondary pattern
        secondary = result.data.get("secondary_pattern")
        if secondary:
            relationship = secondary.get("relationship_to_primary", "")
            relationship_label = " (amplifies the primary pattern)" if relationship == "amplifying" else " (independent)" if relationship else ""
            st.markdown("---")
            st.markdown(f"**Secondary Pattern — {secondary.get('name', '')}{relationship_label}**")
            st.markdown(secondary.get("description", ""))

        # Why this pattern
        if result.data.get("why_this_pattern"):
            st.markdown("---")
            st.markdown("**Why This Pattern**")
            st.markdown(result.data.get("why_this_pattern", ""))

        # Evidence
        st.markdown("---")
        st.markdown("**Evidence**")
        for quote in result.data.get("evidence", []):
            st.markdown(f"> {quote}")

        # Pattern loop
        loop = result.data.get("pattern_loop", {})
        if loop:
            st.markdown("---")
            st.markdown("**How the Pattern Plays Out**")
            if loop.get("trigger"):
                st.markdown(f"**Trigger** — {loop.get('trigger', '')}")
            if loop.get("automatic_response"):
                st.markdown(f"**Automatic response** — {loop.get('automatic_response', '')}")
            if loop.get("interruption_point"):
                st.info(f"**Interruption point** — {loop.get('interruption_point', '')}")
            if loop.get("immediate_relief"):
                st.markdown(f"**Immediate relief** — {loop.get('immediate_relief', '')}")
            if loop.get("career_consequence"):
                st.markdown(f"**Career consequence** — {loop.get('career_consequence', '')}")

        # Career cost
        career_cost = result.data.get("career_cost", "")
        if career_cost:
            st.markdown("---")
            st.error(f"**Career Cost** — {career_cost}")

        # Career progression risk
        risk = result.data.get("career_progression_risk", "")
        if risk:
            risk_label = {"high": "🔴 High", "moderate": "🟡 Moderate", "low": "🟢 Low"}.get(risk, risk.capitalize())
            st.caption(f"Career Progression Risk: {risk_label}")

        # Career moments
        career_moments = result.data.get("career_moments", [])
        if career_moments:
            st.markdown("---")
            st.markdown("**Where This Shows Up at Work**")
            for moment in career_moments:
                st.markdown(f"- {moment}")

        # Avoided outcome
        st.markdown("---")
        st.markdown("**What This Behaviour Is Designed to Avoid**")
        st.info(result.data.get("avoided_outcome", ""))

        # Prediction
        if result.data.get("prediction"):
            st.markdown("---")
            st.markdown("**Prediction**")
            st.warning(result.data.get("prediction", ""))

        # Protocol
        protocol = result.data.get("protocol", {})
        st.markdown("---")
        st.markdown("**The Protocol**")
        if protocol.get("use_when"):
            st.caption(protocol.get("use_when", ""))
        if protocol.get("interruption_check"):
            st.markdown(f"🛑 **Interruption check:** {protocol.get('interruption_check', '')}")
        steps = protocol.get("steps", [])
        if steps:
            st.markdown("**Steps:**")
            steps_text = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))
            st.markdown(steps_text)
        st.markdown(f"⚡ **If you can't stop right now:** {protocol.get('fallback_mid_activation', '')}")
        if protocol.get("next_action"):
            st.markdown(f"**If it doesn't land:** {protocol.get('next_action', '')}")
        if protocol.get("when_it_works"):
            st.success(f"**When it works, watch for this:** {protocol.get('when_it_works', '')}")

        # Next experiment
        if protocol.get("next_experiment"):
            st.markdown("---")
            st.markdown("**Next Experiment**")
            st.markdown(protocol.get("next_experiment", ""))

        # Citations — only shown when web search was used
        if result.citations:
            st.markdown("---")
            st.markdown("**Further Reading**")
            for c in result.citations:
                st.markdown(f"- [{c['title']}]({c['url']})")

        # Reset
        st.markdown("---")
        if st.button("Start a new reflection", use_container_width=True):
            for key in ["stage", "reflection_answers", "investigation_questions", "investigation_answers",
                        "mirror_questions", "hypothesis", "extended_thinking", "context_file_id"]:
                st.session_state.pop(key, None)
            st.rerun()
