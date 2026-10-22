"""Tests for ingest.py."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from safedesk.ingest import MAX_PAGES, ingest_file, ingest_stream


def create_test_image(width: int = 800, height: int = 600, color: tuple = (255, 0, 0)) -> bytes:
    """Create a test image as PNG bytes."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_ingest_png_stream():
    """Test ingesting a PNG image from a stream."""
    img_bytes = create_test_image(800, 600, (255, 0, 0))
    stream = io.BytesIO(img_bytes)
    
    result = ingest_stream(stream, ".png")
    
    assert len(result.page_images) == 1
    assert result.pdf_bytes is None
    assert result.truncated is False
    
    # Verify the output is valid PNG
    output_img = Image.open(io.BytesIO(result.page_images[0]))
    assert output_img.format == "PNG"
    assert output_img.mode == "RGB"


def test_ingest_large_image_downscaled():
    """Test that large images are downscaled to MAX_DIMENSION."""
    # Create a 3000x2000 image
    img_bytes = create_test_image(3000, 2000, (0, 255, 0))
    stream = io.BytesIO(img_bytes)
    
    result = ingest_stream(stream, ".png")
    
    # Check that longest side is at most 1600
    output_img = Image.open(io.BytesIO(result.page_images[0]))
    assert max(output_img.size) <= 1600
    # Aspect ratio should be preserved
    assert abs((output_img.width / output_img.height) - (3000 / 2000)) < 0.01


def test_ingest_small_image_not_upscaled():
    """Test that small images are not upscaled."""
    img_bytes = create_test_image(400, 300, (0, 0, 255))
    stream = io.BytesIO(img_bytes)
    
    result = ingest_stream(stream, ".png")
    
    output_img = Image.open(io.BytesIO(result.page_images[0]))
    # Should remain small
    assert output_img.width <= 400
    assert output_img.height <= 300


def test_ingest_unsupported_format():
    """Test that unsupported formats raise ValueError."""
    stream = io.BytesIO(b"fake data")
    
    with pytest.raises(ValueError, match="Unsupported file type"):
        ingest_stream(stream, ".txt")


def test_ingest_jpeg():
    """Test ingesting a JPEG image."""
    img = Image.new("RGB", (800, 600), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()
    
    stream = io.BytesIO(jpeg_bytes)
    result = ingest_stream(stream, ".jpg")
    
    assert len(result.page_images) == 1
    assert result.pdf_bytes is None
    # Output should be PNG
    output_img = Image.open(io.BytesIO(result.page_images[0]))
    assert output_img.format == "PNG"


def test_pdf_truncation():
    """Test that PDFs with more than MAX_PAGES are truncated."""
    # This test requires a PDF with multiple pages
    # For now, we'll test the truncation flag in a simpler way
    # by creating a minimal PDF (requires PyMuPDF)
    import fitz
    
    doc = fitz.open()
    # Create 7 pages (more than MAX_PAGES which is 5)
    for i in range(7):
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), f"Page {i + 1}")
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    stream = io.BytesIO(pdf_bytes)
    result = ingest_stream(stream, ".pdf")
    
    assert len(result.page_images) == MAX_PAGES  # Should be capped at 5
    assert result.truncated is True
    assert result.pdf_bytes == pdf_bytes


def test_pdf_no_truncation():
    """Test that PDFs with <= MAX_PAGES are not truncated."""
    import fitz
    
    doc = fitz.open()
    # Create 3 pages (less than MAX_PAGES)
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), f"Page {i + 1}")
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    stream = io.BytesIO(pdf_bytes)
    result = ingest_stream(stream, ".pdf")
    
    assert len(result.page_images) == 3
    assert result.truncated is False
    assert result.pdf_bytes == pdf_bytes


def test_pdf_color_preservation():
    """Test that PDF pages are rendered in color."""
    import fitz
    
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Draw colored rectangles
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(100, 100, 200, 200))
    shape.finish(color=(1, 0, 0), fill=(1, 0, 0))  # Red
    shape.commit()
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    stream = io.BytesIO(pdf_bytes)
    result = ingest_stream(stream, ".pdf")
    
    # Verify output is RGB
    output_img = Image.open(io.BytesIO(result.page_images[0]))
    assert output_img.mode == "RGB"
