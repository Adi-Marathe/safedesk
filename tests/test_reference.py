"""Tests for reference.py."""

from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image

from safedesk.reference import extract_reference_text


def create_pdf_with_text(text: str) -> bytes:
    """Create a simple PDF with text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((100, 100), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_test_image() -> bytes:
    """Create a simple test image."""
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_pdf_text_substantial():
    """Test extracting substantial text from PDF."""
    pdf_bytes = create_pdf_with_text("This is a test document with enough text to be considered substantial.")
    
    result = extract_reference_text(pdf_bytes, [])
    
    assert result.source == "pdf_text"
    assert "test document" in result.text.lower()


def test_extract_pdf_text_insufficient():
    """Test that PDFs with minimal text return empty."""
    pdf_bytes = create_pdf_with_text("Hi")  # Only 2 characters, less than 40
    
    result = extract_reference_text(pdf_bytes, [])
    
    # Should fall through to no reference (or tesseract if available)
    # Since we're not testing with actual tesseract here, expect None
    assert result.source in [None, "tesseract"]


def test_extract_no_pdf():
    """Test extraction when no PDF is provided (image only)."""
    img_bytes = create_test_image()
    
    result = extract_reference_text(None, [img_bytes])
    
    # Without tesseract installed, should return None
    # With tesseract, might return tesseract
    assert result.source in [None, "tesseract"]


def test_extract_handles_corrupt_pdf():
    """Test that corrupt PDF data doesn't crash."""
    corrupt_pdf = b"This is not a PDF"
    
    result = extract_reference_text(corrupt_pdf, [])
    
    # Should handle gracefully and return None
    assert result.source in [None, "tesseract"]


def test_extract_empty_inputs():
    """Test extraction with no inputs at all."""
    result = extract_reference_text(None, [])
    
    assert result.source is None
    assert result.text == ""
