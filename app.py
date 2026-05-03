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
from validator import validate_answers
from analyser import analyse_structured, PipelineError


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
            result = analyse_structured(client, answers, extended_thinking=extended_thinking)
    except PipelineError as e:
        st.error(str(e))
        st.stop()

    if not result.data:
        st.error("The analysis came back empty. Please try again.")
        st.stop()

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
