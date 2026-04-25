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
from analyser import analyse_structured
from evaluator import evaluate_output


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


# ── Run button ───────────────────────────────────────────────
st.divider()
run = st.button("Analyse", type="primary", use_container_width=True)


# ── Pipeline ─────────────────────────────────────────────────
if run:
    client = get_client()

    # Validation
    with st.spinner("Checking input quality..."):
        valid = validate_answers(client, answers)

    if not valid:
        st.stop()

    # Analysis
    with st.spinner("Running analysis..."):
        analysis_data, analysis_text = analyse_structured(client, answers)

    st.divider()
    st.subheader("Pattern Analysis")

    # Core pattern
    core = analysis_data.get("core_pattern", {})
    st.markdown(f"### {core.get('name', '')}")
    st.markdown(core.get("description", ""))

    # Secondary pattern
    secondary = analysis_data.get("secondary_pattern")
    if secondary:
        st.markdown("---")
        st.markdown(f"**Secondary Pattern — {secondary.get('name', '')}**")
        st.markdown(secondary.get("description", ""))

    # Evidence
    st.markdown("---")
    st.markdown("**Evidence**")
    for quote in analysis_data.get("evidence", []):
        st.markdown(f"> {quote}")

    # Domains
    st.markdown("---")
    st.markdown("**Where It Shows Up**")
    cols = st.columns(len(analysis_data.get("domains", [])))
    for col, domain in zip(cols, analysis_data.get("domains", [])):
        col.markdown(f"**{domain}**")

    # Payoff
    st.markdown("---")
    st.markdown("**The Payoff**")
    st.info(analysis_data.get("payoff", ""))

    # Protocol
    protocol = analysis_data.get("protocol", {})
    st.markdown("---")
    st.markdown("**The Protocol**")
    st.markdown(f"🔍 **Detection:** {protocol.get('detection_trigger', '')}")
    st.markdown("**Steps:**")
    for i, step in enumerate(protocol.get("steps", []), 1):
        st.markdown(f"{i}. {step}")
    fc = protocol.get("failure_condition", {})
    if isinstance(fc, dict):
        st.warning(f"**If it goes wrong:** {fc.get('if_wrong', '')}")
        st.success(f"**If it goes right:** {fc.get('if_right', '')}")
    else:
        st.warning(f"**Failure condition:** {fc}")

    # Evaluation
    st.divider()
    st.subheader("Quality Evaluation")
    with st.spinner("Evaluating output..."):
        with st.expander("See evaluation", expanded=False):
            # Redirect evaluate_output print to st.text
            import io, contextlib
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                evaluate_output(client, analysis_text)
            st.text(buffer.getvalue().strip())
