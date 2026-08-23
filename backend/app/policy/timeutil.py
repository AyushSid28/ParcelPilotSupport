from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
OPEN = time(9, 0)
CLOSE = time(18, 0)


def hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def minutes_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60


def business_minutes(start: datetime, end: datetime) -> float:
    """Elapsed minutes inside Mon–Fri 09:00–18:00 IST."""
    if end <= start:
        return 0.0
    cur = start.astimezone(IST)
    last = end.astimezone(IST)
    total = 0.0
    while cur.date() <= last.date():
        if cur.weekday() < 5:
            day_open = cur.replace(hour=OPEN.hour, minute=0, second=0, microsecond=0)
            day_close = cur.replace(hour=CLOSE.hour, minute=0, second=0, microsecond=0)
            a = max(cur, day_open)
            b = min(last, day_close)
            if b > a:
                total += (b - a).total_seconds() / 60
        cur = (cur + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return total
