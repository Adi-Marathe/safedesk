"""Pipeline: ingest -> analyze -> verify -> urgency. (Build step 3)"""

from __future__ import annotations

import sys
from pathlib import Path

from safedesk.ingest import ingest_file
from safedesk.llm import OllamaBackend
from safedesk.schema import Analysis


def run_pipeline(file_path: str | Path, backend: OllamaBackend | None = None) -> Analysis:
    """Run the full document analysis pipeline.

    Parameters
    ----------
    file_path : str | Path
        Path to the PDF or image file.
    backend : OllamaBackend | None
        Backend to use for analysis. If None, creates a default OllamaBackend.

    Returns
    -------
    Analysis
        Structured analysis result.
    """
    if backend is None:
        backend = OllamaBackend()

    # Step 1: Ingest
    result = ingest_file(file_path)

    # Step 2: Analyze with Gemma
    analysis = backend.analyze(result.page_images)

    return analysis


def main():
    """CLI entry point: python -m safedesk.pipeline <file>"""
    if len(sys.argv) < 2:
        print("Usage: python -m safedesk.pipeline <file>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        backend = OllamaBackend()
        backend.check_health()
        analysis = run_pipeline(file_path, backend)
        print(analysis.model_dump_json(indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
