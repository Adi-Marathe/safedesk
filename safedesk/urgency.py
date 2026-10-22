"""Urgency: days-left and colour computation. (Build step 4)"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Literal


@dataclass
class UrgencyInfo:
    """Urgency information for a deadline."""

    color: Literal["red", "amber", "green", "grey"]
    label: str
    days_left: int | None  # None if no date


def compute_urgency(date_iso: str | None, today: datetime.date | None = None) -> UrgencyInfo:
    """Compute urgency color and label for a deadline.

    Rules:
    - Overdue: red "OVERDUE"
    - 0-3 days: red
    - 4-7 days: amber
    - >7 days: green
    - No date: grey "Date not stated"

    Parameters
    ----------
    date_iso : str | None
        Date in YYYY-MM-DD format, or None.
    today : datetime.date | None
        Current date (defaults to today). Used for testing.

    Returns
    -------
    UrgencyInfo
        Urgency color, label, and days left.
    """
    if today is None:
        today = datetime.date.today()

    if date_iso is None:
        return UrgencyInfo(color="grey", label="Date not stated", days_left=None)

    try:
        deadline = datetime.date.fromisoformat(date_iso)
    except ValueError:
        # Invalid date format
        return UrgencyInfo(color="grey", label="Date not stated", days_left=None)

    days_left = (deadline - today).days

    if days_left < 0:
        return UrgencyInfo(color="red", label="OVERDUE", days_left=days_left)
    elif days_left <= 3:
        return UrgencyInfo(color="red", label=f"{days_left} days left", days_left=days_left)
    elif days_left <= 7:
        return UrgencyInfo(color="amber", label=f"{days_left} days left", days_left=days_left)
    else:
        return UrgencyInfo(color="green", label=f"{days_left} days left", days_left=days_left)
