"""Tests for the OS-clock date/time tool."""

from datetime import datetime

from tools.clock import current_time


def test_returns_all_fields():
    clock = current_time()

    for key in (
        "datetime",
        "date",
        "time",
        "weekday",
        "timezone",
        "message",
    ):
        assert key in clock


def test_matches_system_clock():
    from datetime import timedelta

    before = datetime.now().astimezone()
    clock = current_time()
    after = datetime.now().astimezone()

    parsed = datetime.fromisoformat(clock["datetime"])

    # The tool reports whole seconds, allow one second of slack.
    assert before - timedelta(seconds=1) <= parsed <= after


def test_weekday_is_consistent():
    clock = current_time()
    parsed = datetime.fromisoformat(clock["datetime"])

    assert clock["weekday"] == parsed.strftime("%A")


def test_message_contains_readable_time():
    clock = current_time()

    assert isinstance(clock["message"], str)
    assert clock["weekday"] in clock["message"]
