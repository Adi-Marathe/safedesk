"""Ingest: PDF/image -> list of page images. (Build step 2)"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF
from PIL import Image


MAX_PAGES = 5
MAX_DIMENSION = 1600
PDF_DPI = 150


@dataclass
class IngestResult:
    """Result of ingesting a document."""

    page_images: list[bytes]  # PNG-encoded page images
    pdf_bytes: bytes | None  # Original PDF bytes if it was a PDF
    truncated: bool  # True if pages were capped at MAX_PAGES


def ingest_file(file_path: str | Path) -> IngestResult:
    """Ingest a PDF or image file into page images.

    Parameters
    ----------
    file_path : str | Path
        Path to the PDF or image file.

    Returns
    -------
    IngestResult
        Page images (PNG bytes), original PDF if applicable, and truncation flag.
    """
    path = Path(file_path)
    with open(path, "rb") as f:
        return ingest_stream(f, path.suffix.lower())


def ingest_stream(stream: BinaryIO, suffix: str) -> IngestResult:
    """Ingest a PDF or image from a stream.

    Parameters
    ----------
    stream : BinaryIO
        Binary stream containing the file data.
    suffix : str
        File extension (e.g., ".pdf", ".png").

    Returns
    -------
    IngestResult
        Page images (PNG bytes), original PDF if applicable, and truncation flag.
    """
    data = stream.read()

    if suffix == ".pdf":
        return _ingest_pdf(data)
    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return _ingest_image(data)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _ingest_pdf(pdf_bytes: bytes) -> IngestResult:
    """Convert PDF pages to color PNG images.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF file bytes.

    Returns
    -------
    IngestResult
        Page images, original PDF bytes, and truncation flag.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    truncated = page_count > MAX_PAGES
    pages_to_process = min(page_count, MAX_PAGES)

    page_images = []
    for page_num in range(pages_to_process):
        page = doc[page_num]
        # Render at 150 DPI
        mat = fitz.Matrix(PDF_DPI / 72, PDF_DPI / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

        # Convert to PIL Image
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        # Downscale if needed
        img = _downscale_image(img)

        # Encode as PNG
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        page_images.append(buf.getvalue())

    doc.close()
    return IngestResult(
        page_images=page_images, pdf_bytes=pdf_bytes, truncated=truncated
    )


def _ingest_image(image_bytes: bytes) -> IngestResult:
    """Convert an image to a color PNG.

    Parameters
    ----------
    image_bytes : bytes
        Raw image file bytes.

    Returns
    -------
    IngestResult
        Single page image, no PDF bytes, not truncated.
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Fix EXIF rotation
    try:
        exif = img.getexif()
        if exif:
            orientation = exif.get(0x0112)  # Orientation tag
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        # If EXIF handling fails, continue with original image
        pass

    # Convert to RGB if needed (e.g., RGBA, grayscale)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Downscale if needed
    img = _downscale_image(img)

    # Encode as PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return IngestResult(
        page_images=[buf.getvalue()], pdf_bytes=None, truncated=False
    )


def _downscale_image(img: Image.Image) -> Image.Image:
    """Downscale image so longest side is at most MAX_DIMENSION pixels.

    Parameters
    ----------
    img : Image.Image
        PIL Image to downscale.

    Returns
    -------
    Image.Image
        Downscaled image (or original if already small enough).
    """
    width, height = img.size
    longest_side = max(width, height)

    if longest_side > MAX_DIMENSION:
        scale = MAX_DIMENSION / longest_side
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return img
