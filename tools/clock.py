"""OS-clock date/time for Zoey.

The current date and time must always come from the system clock,
never from the LLM. This module is the single source of truth the
intent/action pipeline uses.
"""

from datetime import datetime


def current_time():
    """Return the local system date and time.

    Returns a dict with ISO datetime, separate date/time strings,
    weekday, timezone name, and a human-readable message."""

    now = datetime.now().astimezone()

    readable = now.strftime("%A, %d %B %Y at %I:%M %p")

    timezone = now.tzname() or "local time"

    return {
        "datetime": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
        "timezone": timezone,
        "message": f"It's {readable} ({timezone}).",
    }
