"""Tests for urgency.py."""

from __future__ import annotations

import datetime

import pytest

from safedesk.urgency import compute_urgency


def test_urgency_overdue():
    """Test that overdue dates are marked red."""
    today = datetime.date(2024, 12, 10)
    urgency = compute_urgency("2024-12-05", today)

    assert urgency.color == "red"
    assert urgency.label == "OVERDUE"
    assert urgency.days_left == -5


def test_urgency_0_to_3_days():
    """Test that 0-3 days left is marked red."""
    today = datetime.date(2024, 12, 10)

    # 0 days
    urgency0 = compute_urgency("2024-12-10", today)
    assert urgency0.color == "red"
    assert urgency0.days_left == 0

    # 1 day
    urgency1 = compute_urgency("2024-12-11", today)
    assert urgency1.color == "red"
    assert urgency1.days_left == 1

    # 3 days
    urgency3 = compute_urgency("2024-12-13", today)
    assert urgency3.color == "red"
    assert urgency3.days_left == 3


def test_urgency_4_to_7_days():
    """Test that 4-7 days left is marked amber."""
    today = datetime.date(2024, 12, 10)

    # 4 days
    urgency4 = compute_urgency("2024-12-14", today)
    assert urgency4.color == "amber"
    assert urgency4.days_left == 4

    # 7 days
    urgency7 = compute_urgency("2024-12-17", today)
    assert urgency7.color == "amber"
    assert urgency7.days_left == 7


def test_urgency_more_than_7_days():
    """Test that >7 days left is marked green."""
    today = datetime.date(2024, 12, 10)

    # 8 days
    urgency8 = compute_urgency("2024-12-18", today)
    assert urgency8.color == "green"
    assert urgency8.days_left == 8

    # 30 days
    urgency30 = compute_urgency("2025-01-09", today)
    assert urgency30.color == "green"
    assert urgency30.days_left == 30


def test_urgency_no_date():
    """Test that None date is marked grey."""
    urgency = compute_urgency(None)

    assert urgency.color == "grey"
    assert urgency.label == "Date not stated"
    assert urgency.days_left is None


def test_urgency_invalid_date_format():
    """Test that invalid date formats are handled gracefully."""
    urgency = compute_urgency("invalid-date")

    assert urgency.color == "grey"
    assert urgency.label == "Date not stated"
    assert urgency.days_left is None


def test_urgency_uses_today_by_default():
    """Test that compute_urgency uses today's date by default."""
    # This test will pass on any day, just checking it doesn't crash
    urgency = compute_urgency("2025-12-31")

    assert urgency.color in ["red", "amber", "green"]
    assert urgency.days_left is not None
