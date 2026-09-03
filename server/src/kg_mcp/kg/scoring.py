
from datetime import datetime, timedelta
import math

def calculate_urgency_score(
    due_at: datetime | None,
    priority: str = "medium",
    created_at: datetime | None = None,
    last_viewed_at: datetime | None = None,
    status: str = "open"
) -> float:
    """
    Calculate urgency score (0.0 to 100.0+).

    Factors:
    - Due Date Proximity (exponential decay)
    - Priority (multiplier)
    - Stalled Duration (linear boost)
    """
    if status == "completed":
        return 0.0

    score = 0.0
    now = datetime.now()

    # 1. Base Score from Priority
    priority_map = {
        "low": 10.0,
        "medium": 30.0,
        "high": 60.0,
        "critical": 90.0
    }
    base_score = priority_map.get(priority.lower(), 30.0)
    score += base_score

    # 2. Due Date Proximity
    if due_at:
        delta = due_at - now
        days_until = delta.total_seconds() / 86400.0

        if days_until < 0:
            # Overdue: heavy penalty/boost
            score += 50.0 + (abs(days_until) * 5.0)
        elif days_until < 1:
            # Due today: high boost
            score += 40.0
        elif days_until < 3:
            # Due soon
            score += 20.0
        elif days_until < 7:
            score += 10.0

    # 3. Staleness / Age (if no due date, older items might need attention or decay?)
    # Here mimicking "Stalled" - if created long ago and still open
    if created_at:
        age_days = (now - created_at).total_seconds() / 86400.0
        if age_days > 7:
            # Nudge old items slightly
            score += min(age_days, 20.0) # Max 20 pts from age

    return round(score, 2)
