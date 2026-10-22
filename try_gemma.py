#!/usr/bin/env python3
"""Send a sample image to Gemma 4 E4B via Ollama and print the reply.

This is the step-1 smoke test from the build plan.  It creates a small
synthetic document image with Pillow (no external file needed), sends it
to the local OllamaBackend, and prints the structured Analysis plus the
wall-clock time.

Usage
-----
    python try_gemma.py                  # uses the built-in synthetic image
    python try_gemma.py path/to/img.png  # uses a real image file instead
"""

from __future__ import annotations

import io
import sys
import time

from PIL import Image, ImageDraw, ImageFont

from safedesk.llm import BackendError, OllamaBackend


def make_sample_image() -> bytes:
    """Create a tiny synthetic electricity-bill image and return PNG bytes."""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Use default font (always available, no file needed)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        font_sm = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    # Fake letterhead
    draw.rectangle([(0, 0), (800, 70)], fill=(30, 80, 160))
    draw.text((20, 18), "METRO POWER DISTRIBUTION LTD", fill="white", font=font)

    # Body
    y = 90
    lines = [
        "ELECTRICITY BILL",
        "",
        "Account No: 4412-8837-0021",
        "Bill Date: 2026-09-15",
        "Due Date: 2026-10-31",
        "",
        "Units consumed:   342 kWh",
        "Rate:             Rs 7.50 / kWh",
        "Energy charges:   Rs 2,565.00",
        "Fixed charge:     Rs   150.00",
        "Tax (18% GST):    Rs   488.70",
        "─────────────────────────────",
        "Total Due:        Rs 3,203.70",
        "",
        "Pay before 2026-10-31 to avoid a late fee of Rs 160.19.",
    ]
    for line in lines:
        draw.text((40, y), line, fill="black", font=font_sm)
        y += 26

    # Simulate a red PAID stamp (angled text is hard without extra deps,
    # so we just draw a red rectangle + text).
    draw.rectangle([(500, 400), (740, 470)], outline="red", width=4)
    draw.text((540, 420), "PAID  2026-10-01", fill="red", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    # Resolve image bytes -------------------------------------------------
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"Loading image from: {path}")
        with open(path, "rb") as f:
            image_bytes = f.read()
    else:
        print("Using built-in synthetic electricity-bill image.")
        image_bytes = make_sample_image()

    # Save synthetic image so the user can inspect it ---------------------
    preview_path = "samples/sample_bill.png"
    try:
        with open(preview_path, "wb") as f:
            f.write(image_bytes)
        print(f"Sample image saved to: {preview_path}")
    except OSError:
        pass

    # Backend setup -------------------------------------------------------
    backend = OllamaBackend()

    print("\n--- Health check ---")
    try:
        backend.check_health()
        print("OK: Ollama is running and model is available.")
    except BackendError as exc:
        print(f"FAIL:\n{exc}")
        sys.exit(1)

    # Send to model -------------------------------------------------------
    print("\n--- Sending image to Gemma 4 E4B … ---")
    t0 = time.perf_counter()
    try:
        analysis = backend.analyze([image_bytes])
    except BackendError as exc:
        print(f"Model error:\n{exc}")
        sys.exit(1)
    elapsed = time.perf_counter() - t0

    # Print results -------------------------------------------------------
    print("\n--- Analysis result ---")
    print(analysis.model_dump_json(indent=2))
    print(f"\n⏱  Time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
