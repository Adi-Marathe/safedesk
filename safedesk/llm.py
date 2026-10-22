"""Backend interface and OllamaBackend for SafeDesk.

Default backend is Ollama at http://localhost:11434, model gemma4:e4b.
Requires Ollama v0.20.0 or newer.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

import ollama


from safedesk.prompts import ANALYZE_SYSTEM
from safedesk.schema import Analysis


class BackendError(Exception):
    """Raised when a backend is unavailable or a model call fails."""


@runtime_checkable
class Backend(Protocol):
    """Protocol for document-analysis backends."""

    def analyze(self, images: list[bytes]) -> Analysis:
        """Analyse page images and return a structured Analysis."""
        ...


class OllamaBackend:
    """Ollama backend targeting gemma4:e4b running locally."""

    DEFAULT_MODEL = "gemma4:e4b"
    DEFAULT_HOST = "http://localhost:11434"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        num_ctx: int = 16384,
    ) -> None:
        self.model = model
        self.num_ctx = num_ctx
        self._client = ollama.Client(host=host)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def check_health(self) -> None:
        """Verify Ollama is reachable and the model is pulled.

        Raises BackendError with an actionable message on failure.
        """
        try:
            model_list = self._client.list()
        except Exception as exc:
            raise BackendError(
                "Cannot reach Ollama. Is it running?\n"
                "  Start it with:  ollama serve\n"
                f"  (tried {self._client._client._base_url})"
            ) from exc

        available = [m.model for m in model_list.models]
        # Ollama may report the model with or without a ":latest" tag,
        # so we check both the exact name and a prefix match.
        if not any(
            name == self.model or name.startswith(self.model + ":")
            for name in available
        ):
            raise BackendError(
                f"Model '{self.model}' is not pulled.\n"
                f"  Run:  ollama pull {self.model}\n"
                f"  Available models: {', '.join(available) or '(none)'}"
            )

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self, images: list[bytes]) -> Analysis:
        """Send page images to Gemma 4 E4B and return a parsed Analysis.

        Parameters
        ----------
        images:
            List of PNG-encoded page images.

        Returns
        -------
        Analysis
            Pydantic model parsed from the model's JSON response.
        """
        if not images:
            raise ValueError("At least one page image is required.")

        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": ANALYZE_SYSTEM},
                {
                    "role": "user",
                    "content": "Read these pages.",
                    "images": images,
                },
            ],
            format=Analysis.model_json_schema(),
            options={"temperature": 0, "num_ctx": self.num_ctx},
            keep_alive="30m",
        )

        raw_text = response.message.content
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise BackendError(
                f"Model returned invalid JSON:\n{raw_text[:500]}"
            ) from exc

        return Analysis.model_validate(data)
