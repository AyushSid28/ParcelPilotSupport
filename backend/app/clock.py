from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
SNAPSHOT = datetime(2026, 8, 16, 11, 0, tzinfo=IST)


def now() -> datetime:
    """Assessment clock. All time-based rules use this instant."""
    return SNAPSHOT
