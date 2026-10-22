"""SafeDesk: Streamlit entry point. (Build step 5)"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import streamlit as st
from PIL import Image

from safedesk.ingest import ingest_stream
from safedesk.llm import BackendError, OllamaBackend
from safedesk.reference import extract_reference_text
from safedesk.schema import Analysis
from safedesk.urgency import compute_urgency
from safedesk.verify import verify_facts

# Session directory for temporary files
SESSION_DIR = Path(".session")


def init_session():
    """Initialize session state."""
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "page_images" not in st.session_state:
        st.session_state.page_images = None
    if "reference_text" not in st.session_state:
        st.session_state.reference_text = None
    if "verified_deadlines" not in st.session_state:
        st.session_state.verified_deadlines = None
    if "verified_amounts" not in st.session_state:
        st.session_state.verified_amounts = None


def wipe_session():
    """Delete session directory and clear session state."""
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
    st.session_state.analysis = None
    st.session_state.page_images = None
    st.session_state.reference_text = None
    st.session_state.verified_deadlines = None
    st.session_state.verified_amounts = None


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="SafeDesk", page_icon="📄", layout="wide")

    init_session()

    # Sidebar
    with st.sidebar:
        st.title("SafeDesk")
        st.markdown("### 🔒 Privacy First")
        st.success("✅ Running locally on Gemma 4 E4B\n\nNothing leaves this device.")

        st.markdown("---")
        st.markdown("**Model:** gemma4:e4b")

        # Check backend health
        try:
            backend = OllamaBackend()
            backend.check_health()
            st.info("✅ Ollama connected")
        except BackendError as e:
            st.error(f"❌ Backend Error:\n\n{e}")
            st.stop()

        # Cross-check status
        if st.session_state.reference_text:
            ref = st.session_state.reference_text
            if ref.source == "pdf_text":
                st.info("📄 Cross-check: PDF text")
            elif ref.source == "tesseract":
                st.info("🔍 Cross-check: Tesseract")
            else:
                st.info("⚠️ Cross-check: Off")
        else:
            st.info("⚠️ Cross-check: Off")

        st.markdown("---")
        if st.button("🗑️ Wipe session", use_container_width=True):
            wipe_session()
            st.rerun()

    # Main content
    st.title("📄 SafeDesk: Private Document Parser")
    st.markdown("Upload a PDF or photo of a letter, bill, or notice. Gemma 4 reads it locally—nothing leaves your machine.")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        help="Upload a PDF or image (PNG, JPG, WEBP)"
    )

    if uploaded_file is not None:
        # Get file extension
        suffix = Path(uploaded_file.name).suffix.lower()

        # Validate file type
        if suffix not in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]:
            st.error(f"❌ Unsupported file type: {suffix}")
            st.stop()

        # Process document
        with st.spinner("Processing document..."):
            try:
                # Progress indicators
                progress = st.progress(0, text="Reading pages...")

                # Ingest
                stream = io.BytesIO(uploaded_file.read())
                ingest_result = ingest_stream(stream, suffix)
                st.session_state.page_images = ingest_result.page_images

                if ingest_result.truncated:
                    st.warning(f"⚠️ Document was truncated to 5 pages for faster processing.")

                progress.progress(33, text="Understanding...")

                # Analyze with Gemma
                analysis = backend.analyze(ingest_result.page_images)
                st.session_state.analysis = analysis

                progress.progress(66, text="Cross-checking...")

                # Extract reference text
                reference = extract_reference_text(ingest_result.pdf_bytes, ingest_result.page_images)
                st.session_state.reference_text = reference

                # Verify facts
                verified_deadlines, verified_amounts = verify_facts(
                    analysis.deadlines, analysis.amounts, reference
                )
                st.session_state.verified_deadlines = verified_deadlines
                st.session_state.verified_amounts = verified_amounts

                progress.progress(100, text="Done!")
                progress.empty()

            except BackendError as e:
                st.error(f"❌ Backend Error: {e}")
                st.stop()
            except Exception as e:
                st.error(f"❌ Error processing document: {e}")
                st.stop()

    # Display results
    if st.session_state.analysis:
        analysis: Analysis = st.session_state.analysis
        verified_deadlines = st.session_state.verified_deadlines
        verified_amounts = st.session_state.verified_amounts
        reference = st.session_state.reference_text

        st.markdown("---")

        # Two columns: images and results
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("📄 Pages")
            for i, img_bytes in enumerate(st.session_state.page_images):
                img = Image.open(io.BytesIO(img_bytes))
                st.image(img, caption=f"Page {i + 1}", use_container_width=True)

        with col2:
            st.subheader("📋 Analysis")

            # Category chip
            category_display = analysis.category.replace("_", " ").title()
            st.markdown(f"**Category:** `{category_display}`")

            # Issuer
            if analysis.issuer:
                st.markdown(f"**Issuer:** {analysis.issuer}")

            # Summary bullets
            st.markdown("**Summary:**")
            for bullet in analysis.summary_bullets:
                st.markdown(f"- {bullet}")

            st.markdown("---")

            # Deadlines
            if verified_deadlines:
                st.subheader("⏰ Deadlines")

                # Sort by date (put undated at the end)
                def sort_key(vd):
                    if vd.value:  # date_iso
                        return (0, vd.value)
                    return (1, "")

                sorted_deadlines = sorted(verified_deadlines, key=sort_key)

                for vd in sorted_deadlines:
                    urgency = compute_urgency(vd.value if vd.value else None)

                    # Color mapping
                    color_map = {
                        "red": "🔴",
                        "amber": "🟠",
                        "green": "🟢",
                        "grey": "⚪",
                    }
                    color_icon = color_map.get(urgency.color, "⚪")

                    # Status badge
                    status_badge = ""
                    if vd.status == "confirmed":
                        status_badge = "✅"
                    elif vd.status == "mismatch":
                        status_badge = "❌ MISMATCH"
                    else:
                        status_badge = "⚠️ Gemma only"

                    # Skip mismatches in urgent banner
                    with st.container():
                        st.markdown(f"### {color_icon} {vd.label}")
                        st.markdown(f"**{urgency.label}** {status_badge}")
                        st.caption(f'"{vd.evidence_quote}"')

                        if vd.status == "mismatch":
                            st.error("⚠️ Does not match the document text. Check manually.")

            st.markdown("---")

            # Amounts
            if verified_amounts:
                st.subheader("💰 Amounts")

                for va in verified_amounts:
                    status_badge = ""
                    if va.status == "confirmed":
                        status_badge = "✅"
                    elif va.status == "mismatch":
                        status_badge = "❌ MISMATCH"
                    else:
                        status_badge = "⚠️ Gemma only"

                    with st.container():
                        st.markdown(f"**{va.label}:** {va.value} {status_badge}")
                        st.caption(f'"{va.evidence_quote}"')

                        if va.status == "mismatch":
                            st.error("⚠️ Does not match the document text. Check manually.")

            st.markdown("---")

            # Marks (stamps, handwriting)
            if analysis.marks:
                st.subheader("✍️ Marks & Stamps")
                for mark in analysis.marks:
                    kind_icon = {"stamp": "📮", "handwriting": "✍️", "signature": "✒️", "other": "🔖"}
                    icon = kind_icon.get(mark.kind, "🔖")
                    st.markdown(f"{icon} **{mark.kind.title()}:** {mark.text}")
                    st.caption("Visual mark, read by Gemma only")

            st.markdown("---")

            # Action required
            if analysis.action_required:
                st.subheader("⚡ Action Required")
                st.info(analysis.action_required)

            # Cross-check stats
            if reference and reference.source:
                total_facts = len(verified_deadlines) + len(verified_amounts)
                confirmed = sum(
                    1
                    for vd in (verified_deadlines + verified_amounts)
                    if vd.status == "confirmed"
                )
                unchecked = sum(
                    1
                    for vd in (verified_deadlines + verified_amounts)
                    if vd.status == "unchecked"
                )

                st.markdown("---")
                st.caption(
                    f"📊 **Verification:** {confirmed} of {total_facts} facts cross-checked"
                    + (f", {unchecked} read by Gemma only" if unchecked > 0 else "")
                )

            # Expander for reference text
            if reference and reference.source and reference.text:
                with st.expander("📄 Show cross-check text"):
                    st.text(reference.text[:2000])  # Limit display
                    if len(reference.text) > 2000:
                        st.caption(f"... ({len(reference.text)} characters total)")


if __name__ == "__main__":
    main()
