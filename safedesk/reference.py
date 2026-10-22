"""Reference: optional independent text from PDF text layer or Tesseract. (Build step 4)"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import fitz  # PyMuPDF


@dataclass
class ReferenceText:
    """Independent text extracted from a document."""

    source: Literal["pdf_text", "tesseract"] | None
    text: str


def extract_reference_text(
    pdf_bytes: bytes | None, page_images: list[bytes]
) -> ReferenceText:
    """Extract reference text for cross-checking.

    Tries in order:
    1. PDF text layer (if pdf_bytes is provided and has substantial text)
    2. Tesseract OCR (if available and working)
    3. Returns source=None if neither is available

    Parameters
    ----------
    pdf_bytes : bytes | None
        Original PDF bytes, if the document was a PDF.
    page_images : list[bytes]
        Page images (PNG bytes), used for Tesseract if needed.

    Returns
    -------
    ReferenceText
        Extracted text and its source, or source=None if unavailable.
    """
    # Try PDF text layer first
    if pdf_bytes is not None:
        pdf_text = _extract_pdf_text(pdf_bytes)
        if pdf_text:
            return ReferenceText(source="pdf_text", text=pdf_text)

    # Try Tesseract if available
    tesseract_text = _extract_tesseract_text(page_images)
    if tesseract_text:
        return ReferenceText(source="tesseract", text=tesseract_text)

    # No reference text available
    return ReferenceText(source=None, text="")


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF.

    Only returns text if there's substantial content (>40 chars per page on average).

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF bytes.

    Returns
    -------
    str
        Extracted text, or empty string if insufficient.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_text = []

        for page in doc:
            text = page.get_text()
            all_text.append(text)

        doc.close()

        combined = " ".join(all_text)
        # Only return if there's substantial text (>40 chars per page average)
        if len(combined) > 40 * len(all_text):
            return combined

        return ""
    except Exception:
        return ""


def _extract_tesseract_text(page_images: list[bytes]) -> str:
    """Extract text using Tesseract OCR.

    Only attempts if pytesseract is installed and Tesseract is available.
    Never raises; returns empty string on any error.

    Parameters
    ----------
    page_images : list[bytes]
        PNG-encoded page images.

    Returns
    -------
    str
        Extracted text, or empty string if Tesseract unavailable or fails.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Check if Tesseract is actually installed
        try:
            # Check for TESSERACT_CMD environment variable (Windows)
            tesseract_cmd = os.environ.get("TESSERACT_CMD")
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            pytesseract.get_tesseract_version()
        except Exception:
            # Tesseract not available
            return ""

        # Extract text from all pages
        all_text = []
        for img_bytes in page_images:
            img = Image.open(io.BytesIO(img_bytes))
            # Use --psm 6 (assume uniform block of text)
            text = pytesseract.image_to_string(img, config="--psm 6")
            all_text.append(text)

        return " ".join(all_text)

    except ImportError:
        # pytesseract not installed
        return ""
    except Exception:
        # Any other error
        return ""
