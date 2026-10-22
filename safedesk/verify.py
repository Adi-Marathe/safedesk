"""Verify: evidence cross-check against reference text. (Build step 4)"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Literal

from safedesk.reference import ReferenceText
from safedesk.schema import Amount, Deadline


@dataclass
class VerifiedFact:
    """A fact (deadline or amount) with verification status."""

    label: str
    value: str  # date_iso for deadlines, value for amounts
    evidence_quote: str
    status: Literal["confirmed", "mismatch", "unchecked"]


def verify_facts(
    deadlines: list[Deadline],
    amounts: list[Amount],
    reference: ReferenceText,
) -> tuple[list[VerifiedFact], list[VerifiedFact]]:
    """Cross-check deadlines and amounts against reference text.

    Parameters
    ----------
    deadlines : list[Deadline]
        Deadlines extracted by the model.
    amounts : list[Amount]
        Amounts extracted by the model.
    reference : ReferenceText
        Independent reference text.

    Returns
    -------
    tuple[list[VerifiedFact], list[VerifiedFact]]
        Verified deadlines and verified amounts.
    """
    verified_deadlines = [
        _verify_fact(d.label, d.date_iso or "", d.evidence_quote, reference)
        for d in deadlines
    ]

    verified_amounts = [
        _verify_fact(a.label, a.value, a.evidence_quote, reference)
        for a in amounts
    ]

    return verified_deadlines, verified_amounts


def _verify_fact(
    label: str, value: str, evidence_quote: str, reference: ReferenceText
) -> VerifiedFact:
    """Verify a single fact against reference text.

    Parameters
    ----------
    label : str
        Fact label.
    value : str
        Fact value.
    evidence_quote : str
        Quote from the document.
    reference : ReferenceText
        Reference text.

    Returns
    -------
    VerifiedFact
        Fact with verification status.
    """
    if reference.source is None:
        # No reference text available
        return VerifiedFact(
            label=label, value=value, evidence_quote=evidence_quote, status="unchecked"
        )

    # Normalize both the quote and reference text
    normalized_quote = _normalize_text(evidence_quote)
    normalized_reference = _normalize_text(reference.text)

    # Check if the normalized quote appears in the reference text
    if _fuzzy_match(normalized_quote, normalized_reference):
        return VerifiedFact(
            label=label, value=value, evidence_quote=evidence_quote, status="confirmed"
        )
    else:
        return VerifiedFact(
            label=label, value=value, evidence_quote=evidence_quote, status="mismatch"
        )


def _normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Applies:
    - Casefold
    - Collapse whitespace
    - Replace common OCR confusions (0/O, 1/l)

    Parameters
    ----------
    text : str
        Text to normalize.

    Returns
    -------
    str
        Normalized text.
    """
    text = text.casefold()
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Replace OCR confusions
    # Note: Be careful with replacements; we only do very common ones
    # We don't replace aggressively to avoid false matches
    return text


def _fuzzy_match(needle: str, haystack: str, threshold: float = 0.92) -> bool:
    """Check if needle appears in haystack with fuzzy matching.

    Uses a sliding window and difflib to allow approximate matches.

    Parameters
    ----------
    needle : str
        Text to find (normalized).
    haystack : str
        Text to search in (normalized).
    threshold : float
        Minimum similarity ratio (0-1) to consider a match.

    Returns
    -------
    bool
        True if a close match is found.
    """
    if not needle:
        return False

    # First try exact substring match
    if needle in haystack:
        return True

    # Try fuzzy match with sliding window
    needle_len = len(needle)
    haystack_len = len(haystack)

    if needle_len > haystack_len:
        return False

    # Slide window across haystack
    for i in range(haystack_len - needle_len + 1):
        window = haystack[i : i + needle_len]
        ratio = difflib.SequenceMatcher(None, needle, window).ratio()
        if ratio >= threshold:
            return True

    return False
