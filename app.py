"""
Pattern Mirror — Streamlit web app.

Renders the pattern analysis as a structured UI.
All logic imported from the existing pipeline modules.
"""

import os
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import QUESTIONS
from validator import validate_answers, validate_context_file
from analyser import analyse_structured, PipelineError
from middleware import pre_process, post_process
from file_context import upload_context_file, delete_file
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


# ── Header ───────────────────────────────────────────────────
st.title("🪞 Pattern Mirror")
st.caption("Answer honestly. Incomplete is fine. There are no right answers.")
st.divider()


# ── Context file (optional) ──────────────────────────────────
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


# ── Questions ────────────────────────────────────────────────
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
    answers.append({"question": f"Q{i}", "answer": answer.strip() if answer.strip() else "[no answer given]"})
    st.write("")


# ── Options + Run button ─────────────────────────────────────
st.divider()
extended_thinking = st.toggle(
    "Extended thinking",
    value=False,
    help="Gives Claude more reasoning time before analysing. Produces deeper results on ambiguous or sparse answers. Uses more tokens."
)
run = st.button("Analyse", type="primary", use_container_width=True)


# ── Pipeline ─────────────────────────────────────────────────
if run:
    client = get_client()

    # Upload, validate, analyse — all inside one try/finally so the context
    # file is always deleted even if validation fails or st.stop() is called.
    context_file_id = None
    result = None
    try:
        # Upload context file if provided — get file_id to pass to analyser
        if uploaded_file is not None:
            try:
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    uf = upload_context_file(client, uploaded_file.getvalue(), uploaded_file.name)
                    context_file_id = uf.file_id
            except ValueError as e:
                st.error(str(e))
                st.stop()

            # Relevance check — warn if document unlikely to help pattern analysis
            with st.spinner("Checking document relevance..."):
                relevance_warnings = validate_context_file(client, context_file_id)
            for warning in relevance_warnings:
                st.warning(warning)

        # Pre-processing — deterministic checks, no Claude calls
        pre = pre_process(answers, has_context_file=context_file_id is not None)
        if pre.warnings:
            for warning in pre.warnings:
                st.warning(warning)
        if pre.blocked:
            for error in pre.errors:
                st.error(error)
            st.stop()

        # Validation
        with st.spinner("Checking input quality..."):
            errors = validate_answers(client, answers)

        if errors:
            for error in errors:
                st.warning(error)
            st.info("Please revisit your answers and try again.")
            st.stop()

        st.divider()
        st.subheader("Pattern Analysis")

        try:
            spinner_msg = "Running analysis (extended thinking enabled)..." if extended_thinking else "Running analysis..."
            with st.spinner(spinner_msg):
                result = analyse_structured(
                    client,
                    answers,
                    extended_thinking=extended_thinking,
                    context_file_id=context_file_id,
                )
        except PipelineError as e:
            st.error(str(e))
            st.stop()

    finally:
        # Always delete the uploaded file — runs even when st.stop() is called
        if context_file_id:
            delete_file(client, context_file_id)

    if not result.data:
        st.error("The analysis came back empty. Please try again.")
        st.stop()

    # Post-processing — cost logging + safety filter
    post = post_process(result.data, result.usage, SONNET_MODEL)
    if post.warnings:
        for warning in post.warnings:
            st.warning(warning)
    with st.expander("📊 Token usage", expanded=False):
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
    cols = st.columns(len(result.data.get("domains", [])))
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
