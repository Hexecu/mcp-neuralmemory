from datetime import datetime, timedelta

from kg_mcp.kg.scoring import calculate_urgency_score


def test_urgency_score_priority():
    score_low = calculate_urgency_score(None, "low")
    score_high = calculate_urgency_score(None, "critical")
    assert score_high > score_low
    assert score_high == 90.0


def test_urgency_score_due_date():
    now = datetime.now()
    due_tomorrow = now + timedelta(days=1)
    due_week = now + timedelta(days=6)

    score_tomorrow = calculate_urgency_score(due_tomorrow, "medium")
    score_week = calculate_urgency_score(due_week, "medium")

    # Closer deadline should have higher score
    assert score_tomorrow > score_week


def test_urgency_score_overdue():
    now = datetime.now()
    overdue = now - timedelta(days=1)

    score = calculate_urgency_score(overdue, "medium")
    assert score > 50.0  # Base penalty for overdue


def test_urgency_score_completed():
    assert calculate_urgency_score(datetime.now(), status="completed") == 0.0
