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
    if "backend_status" not in st.session_state:
        st.session_state.backend_status = None


def wipe_session():
    """Delete session directory and clear session state."""
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
    st.session_state.analysis = None
    st.session_state.page_images = None
    st.session_state.reference_text = None
    st.session_state.verified_deadlines = None
    st.session_state.verified_amounts = None


def render_status_bar():
    """Render horizontal status bar at bottom."""
    st.markdown("---")
    
    # Create horizontal layout for status items
    cols = st.columns([2, 2, 2, 2, 1])
    
    with cols[0]:
        st.markdown("##### 🔒 Privacy")
        st.caption("Running locally • Gemma 4 E4B")
        st.caption("Nothing leaves this device")
    
    with cols[1]:
        st.markdown("##### 🔌 Backend Status")
        if st.session_state.backend_status == "connected":
            st.success("✅ Ollama connected")
        elif st.session_state.backend_status == "error":
            st.error("❌ Ollama disconnected")
        else:
            st.info("⏳ Checking...")
    
    with cols[2]:
        st.markdown("##### 🔍 Cross-check")
        if st.session_state.reference_text:
            ref = st.session_state.reference_text
            if ref.source == "pdf_text":
                st.info("📄 PDF text layer")
            elif ref.source == "tesseract":
                st.info("🔍 Tesseract OCR")
            else:
                st.warning("⚠️ Off")
        else:
            st.caption("Not available")
    
    with cols[3]:
        st.markdown("##### 📊 Session")
        if st.session_state.analysis:
            st.success("✅ Document analyzed")
        else:
            st.caption("No document loaded")
    
    with cols[4]:
        st.markdown("##### ")
        if st.button("🗑️ Clear", use_container_width=True, help="Wipe session data"):
            wipe_session()
            st.rerun()


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="SafeDesk - Private Document Parser", 
        page_icon="📄", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    init_session()

    # Check backend health once
    if st.session_state.backend_status is None:
        try:
            backend = OllamaBackend()
            backend.check_health()
            st.session_state.backend_status = "connected"
        except BackendError as e:
            st.session_state.backend_status = "error"
            st.error(f"❌ **Backend Error**\n\n{e}")
            st.markdown("---")
            render_status_bar()
            st.stop()
    
    backend = OllamaBackend()

    # Header
    st.markdown("<h1 style='text-align: center;'>📄 SafeDesk</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #666;'>Private Document Parser • Powered by Gemma 4 E4B</h4>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Upload a PDF or photo of a letter, bill, or notice. Read locally—nothing leaves your machine.</p>", unsafe_allow_html=True)
    
    st.markdown("---")

    
    # File uploader - centered and prominent
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        uploaded_file = st.file_uploader(
            "Drop your document here or click to browse",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            help="Supports: PDF, PNG, JPG, JPEG, WEBP",
            label_visibility="collapsed"
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
        st.markdown("## 📋 Analysis Results")

        # Three columns for better layout
        left_col, middle_col, right_col = st.columns([2, 3, 2])

        with left_col:
            st.markdown("### 📄 Document Pages")
            for i, img_bytes in enumerate(st.session_state.page_images):
                img = Image.open(io.BytesIO(img_bytes))
                st.image(img, caption=f"Page {i + 1}", use_container_width=True)

        with middle_col:
            # Category and Issuer
            category_display = analysis.category.replace("_", " ").title()
            st.markdown(f"### 📂 {category_display}")
            
            if analysis.issuer:
                st.markdown(f"**From:** {analysis.issuer}")

            # Summary
            st.markdown("#### 📝 Summary")
            for bullet in analysis.summary_bullets:
                st.markdown(f"• {bullet}")

            # Action required
            if analysis.action_required:
                st.markdown("#### ⚡ Action Required")
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

                st.caption(
                    f"📊 **Verification:** {confirmed} of {total_facts} facts cross-checked"
                    + (f", {unchecked} read by Gemma only" if unchecked > 0 else "")
                )

        with right_col:
            # Deadlines
            if verified_deadlines:
                st.markdown("### ⏰ Deadlines")

                # Sort by date
                def sort_key(vd):
                    if vd.value:
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
                    if vd.status == "confirmed":
                        status_badge = "✅"
                    elif vd.status == "mismatch":
                        status_badge = "❌"
                    else:
                        status_badge = "⚠️"

                    with st.container():
                        st.markdown(f"**{color_icon} {vd.label}**")
                        st.caption(f"{urgency.label} {status_badge}")
                        st.caption(f'_"{vd.evidence_quote}"_')
                        
                        if vd.status == "mismatch":
                            st.error("⚠️ Check manually", icon="⚠️")
                        
                        st.markdown("")

            # Amounts
            if verified_amounts:
                st.markdown("### 💰 Amounts")

                for va in verified_amounts:
                    if va.status == "confirmed":
                        status_badge = "✅"
                    elif va.status == "mismatch":
                        status_badge = "❌"
                    else:
                        status_badge = "⚠️"

                    with st.container():
                        st.markdown(f"**{va.label}:** {va.value} {status_badge}")
                        st.caption(f'_"{va.evidence_quote}"_')
                        
                        if va.status == "mismatch":
                            st.error("⚠️ Check manually", icon="⚠️")
                        
                        st.markdown("")

            # Marks
            if analysis.marks:
                st.markdown("### ✍️ Marks & Stamps")
                for mark in analysis.marks:
                    kind_icon = {
                        "stamp": "📮",
                        "handwriting": "✍️",
                        "signature": "✒️",
                        "other": "🔖"
                    }
                    icon = kind_icon.get(mark.kind, "🔖")
                    st.markdown(f"{icon} **{mark.text}**")
                    st.caption(f"_{mark.kind.title()}_")

        # Expander for reference text
        if reference and reference.source and reference.text:
            with st.expander("📄 View cross-check text"):
                st.text(reference.text[:2000])
                if len(reference.text) > 2000:
                    st.caption(f"... ({len(reference.text)} characters total)")

    # Status bar at bottom
    render_status_bar()


if __name__ == "__main__":
    main()
