"""Pydantic models for SafeDesk document analysis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Category = Literal[
    "utility_bill",
    "tax_notice",
    "bank_statement",
    "government_letter",
    "insurance",
    "medical",
    "legal",
    "other",
    "unknown",
]


class Deadline(BaseModel):
    """A deadline extracted from the document."""

    label: str
    date_iso: str | None
    evidence_quote: str


class Amount(BaseModel):
    """A monetary amount extracted from the document."""

    label: str
    value: str
    evidence_quote: str


class Mark(BaseModel):
    """A stamp, handwritten note, or signature observed on the document."""

    kind: Literal["stamp", "handwriting", "signature", "other"]
    text: str


class Analysis(BaseModel):
    """Full analysis result returned by the model for one document."""

    category: Category
    issuer: str | None
    summary_bullets: list[str]  # 1-3 items, target 3
    deadlines: list[Deadline]
    amounts: list[Amount]
    marks: list[Mark]
    action_required: str | None
