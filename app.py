"""
Pattern Mirror — Streamlit web app.

Three-stage flow:
  1. "initial"  — user answers 5 reflection questions + optional context file
  2. "followup" — Haiku generates 4-5 targeted follow-up questions; user answers them
  3. Results rendered inline after stage 2

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
from followup import generate_followups
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
    st.session_state.stage = "initial"
if "initial_answers" not in st.session_state:
    st.session_state.initial_answers = []
if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []
if "extended_thinking" not in st.session_state:
    st.session_state.extended_thinking = False
if "context_file_id" not in st.session_state:
    st.session_state.context_file_id = None


# ── Header ───────────────────────────────────────────────────
st.title("🪞 Pattern Mirror")
st.caption("Answer honestly. Incomplete is fine. There are no right answers.")
st.divider()


# ════════════════════════════════════════════════════════════
# STAGE: initial — 5 questions + context file + Continue
# ════════════════════════════════════════════════════════════
if st.session_state.stage == "initial":

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

        # Generate follow-up questions
        with st.spinner("Generating follow-up questions..."):
            followup_questions = generate_followups(client, answers)

        # Persist to session state and advance
        st.session_state.initial_answers = answers
        st.session_state.followup_questions = followup_questions
        st.session_state.extended_thinking = extended_thinking
        st.session_state.context_file_id = context_file_id
        st.session_state.stage = "followup"
        st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE: followup — dynamic questions + Analyse / Back
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == "followup":

    st.subheader("A few more questions")
    st.caption(
        "These help confirm whether the pattern you're exploring repeats across different "
        "areas of your life, or is specific to one situation."
    )
    st.write("")

    followup_answers = []
    for i, question in enumerate(st.session_state.followup_questions, 1):
        st.markdown(f"**{question}**")
        answer = st.text_area(
            label=f"FQ{i}",
            label_visibility="collapsed",
            placeholder="Your answer...",
            key=f"fq{i}",
            height=100
        )
        followup_answers.append({
            "question": question,
            "answer": answer.strip() if answer.strip() else "[no answer given]",
        })
        st.write("")

    st.divider()
    col_back, col_analyse = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            # Return to initial stage — keep context file for cleanup
            context_file_id = st.session_state.context_file_id
            if context_file_id:
                delete_file(get_client(), context_file_id)
            st.session_state.stage = "initial"
            st.session_state.context_file_id = None
            st.rerun()
    with col_analyse:
        analyse_btn = st.button("Analyse", type="primary", use_container_width=True)

    if analyse_btn:
        client = get_client()
        context_file_id = st.session_state.context_file_id
        result = None

        try:
            # Accurate preflight token count
            preflight_tokens = count_tokens_preflight(client, st.session_state.initial_answers)

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
                        st.session_state.initial_answers,
                        extended_thinking=st.session_state.extended_thinking,
                        context_file_id=context_file_id,
                        followup_answers=followup_answers,
                    )
            except PipelineError as e:
                st.error(str(e))
                st.stop()

        finally:
            # Always delete the context file — runs even when st.stop() is raised
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
                "The follow-up answers didn't give us enough to confirm whether this pattern "
                "repeats across different areas of your life. That's okay — it might be more "
                "situational than structural. Try again with more specific answers, or explore "
                "a different angle."
            )
            if st.button("Start a new reflection", use_container_width=True):
                for key in ["stage", "initial_answers", "followup_questions",
                            "extended_thinking", "context_file_id"]:
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
        st.markdown(f"### {core.get('name', '')}")
        st.caption(core.get("plain_summary", ""))
        st.markdown(core.get("description", ""))

        # Secondary pattern
        secondary = result.data.get("secondary_pattern")
        if secondary:
            st.markdown("---")
            st.markdown(f"**Secondary Pattern — {secondary.get('name', '')}**")
            st.markdown(secondary.get("description", ""))

        # Evidence
        st.markdown("---")
        st.markdown("**Evidence**")
        for quote in result.data.get("evidence", []):
            st.markdown(f"> {quote}")

        # Domains
        st.markdown("---")
        st.markdown("**Where It Shows Up**")
        cols = st.columns(len(result.data.get("domains", [])) or 1)
        for col, domain in zip(cols, result.data.get("domains", [])):
            col.markdown(f"**{domain}**")

        # Payoff
        st.markdown("---")
        st.markdown("**What It's Protecting You From**")
        st.info(result.data.get("payoff", ""))

        # Protocol
        protocol = result.data.get("protocol", {})
        st.markdown("---")
        st.markdown("**The Protocol**")
        st.markdown(f"🔍 **Detection:** {protocol.get('detection_trigger', '')}")
        st.markdown("**Steps:**")
        for i, step in enumerate(protocol.get("steps", []), 1):
            st.markdown(f"{i}. {step}")
        st.markdown(f"⚡ **If you can't stop right now:** {protocol.get('fallback_mid_activation', '')}")
        st.markdown(f"🛑 **If you're completely overwhelmed:** {protocol.get('fallback_shutdown', '')}")
        fc = protocol.get("failure_condition", {})
        if isinstance(fc, dict):
            st.warning(f"**If it goes wrong:** {fc.get('if_wrong', '')}")
            st.success(f"**If it goes right:** {fc.get('if_right', '')}")
        else:
            st.warning(f"**Failure condition:** {fc}")

        # Citations — only shown when web search was used
        if result.citations:
            st.markdown("---")
            st.markdown("**Further Reading**")
            for c in result.citations:
                st.markdown(f"- [{c['title']}]({c['url']})")

        # Evaluation — disabled for now to save tokens during development
        # Re-enable before user testing: uncomment the block below
        # st.divider()
        # st.subheader("Quality Evaluation")
        # with st.spinner("Evaluating output..."):
        #     with st.expander("See evaluation", expanded=False):
        #         import io, contextlib
        #         buffer = io.StringIO()
        #         with contextlib.redirect_stdout(buffer):
        #             evaluate_output(client, result.text)
        #         st.text(buffer.getvalue().strip())

        # Reset
        st.markdown("---")
        if st.button("Start a new reflection", use_container_width=True):
            for key in ["stage", "initial_answers", "followup_questions",
                        "extended_thinking", "context_file_id"]:
                st.session_state.pop(key, None)
            st.rerun()
