import sqlite3

import tools.notifications as notifications
from core.agent_loop import ALLOWED_TOOLS, TOOLS
from core.step_validation import TOOL_ARGUMENT_RULES, validate_step
from database.db import DB_PATH, get_connection, initialize_database


def cleanup():
    initialize_database()
    connection = get_connection()
    connection.execute("DELETE FROM notifications")
    connection.commit()
    connection.close()


def run():
    cleanup()

    calls = []

    def fake_runner(title, message):
        calls.append((title, message))
        return True, None

    original = notifications._run_powershell
    notifications._run_powershell = fake_runner

    try:
        result = notifications.notify("Zoey", "Hello")
        assert result["success"] is True
        assert calls == [("Zoey", "Hello")]

        rows = notifications.notifications_log()
        assert len(rows) == 1
        assert rows[0]["title"] == "Zoey"
        assert rows[0]["message"] == "Hello"

        injection = 'hello"; Write-Host "PWNED'
        result = notifications.notify("Title", injection)
        assert result["success"] is True
        assert calls[-1] == ("Title", injection)

        for bad_title in ("", "   ", None, 123):
            try:
                notifications.notify(bad_title, "message")
                raise AssertionError("bad title accepted")
            except ValueError:
                pass

        for bad_message in ("", "   ", None, 123):
            try:
                notifications.notify("title", bad_message)
                raise AssertionError("bad message accepted")
            except ValueError:
                pass

        try:
            notifications.notify("x" * 121, "message")
            raise AssertionError("oversized title accepted")
        except ValueError:
            pass

        try:
            notifications.notify("title", "x" * 1001)
            raise AssertionError("oversized message accepted")
        except ValueError:
            pass

        assert notifications.notifications_log(1)[0]["message"] == injection

        try:
            notifications.notifications_log(0)
            raise AssertionError("zero limit accepted")
        except ValueError:
            pass

        try:
            notifications.notifications_log(101)
            raise AssertionError("oversized limit accepted")
        except ValueError:
            pass

        assert "notify" in TOOLS
        assert "notifications_log" in TOOLS
        assert "notify" in ALLOWED_TOOLS
        assert "notifications_log" in ALLOWED_TOOLS
        assert "notify" in TOOL_ARGUMENT_RULES
        assert "notifications_log" in TOOL_ARGUMENT_RULES

        assert validate_step({"tool": "notify", "arguments": {"title": "x", "message": "y"}})["valid"]
        assert validate_step({"tool": "notifications_log", "arguments": {}})["valid"]
        assert not validate_step({"tool": "notify", "arguments": {"title": "x"}})["valid"]

        def failing_runner(title, message):
            return False, "mock PowerShell failure"

        notifications._run_powershell = failing_runner
        failed = notifications.notify("Fail", "now")
        assert failed["success"] is False
        assert "failure" in failed["message"].lower()

        # Failed sends are not written as successful notification history.
        assert all(row["title"] != "Fail" for row in notifications.notifications_log(100))

        print("test_notifications.py: 10 tests passed")
    finally:
        notifications._run_powershell = original
        cleanup()


if __name__ == "__main__":
    run()
