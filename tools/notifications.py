import os
import subprocess
from pathlib import Path

from database.db import get_connection, initialize_database


MAX_TITLE_LENGTH = 120
MAX_MESSAGE_LENGTH = 1000
DEFAULT_LOG_LIMIT = 20
MAX_LOG_LIMIT = 100


# Fixed PowerShell program. User text is supplied only through
# environment variables, never interpolated into this command.
_POWERSHELL_SCRIPT = r'''
$ErrorActionPreference = "Stop"
$title = $env:ZOEY_NOTIFY_TITLE
$message = $env:ZOEY_NOTIFY_MESSAGE

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$([System.Security.SecurityElement]::Escape($title))</text><text>$([System.Security.SecurityElement]::Escape($message))</text></binding></visual></toast>")
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Zoey").Show($toast)
'''.strip()


def _validate_text(value, name, maximum):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string.")

    value = value.strip()

    if not value:
        raise ValueError(f"{name} cannot be empty.")

    if len(value) > maximum:
        raise ValueError(f"{name} exceeds the {maximum}-character limit.")

    return value


def _run_powershell(title, message):
    if os.name != "nt":
        return False, "Windows notifications are only supported on Windows."

    env = os.environ.copy()
    env["ZOEY_NOTIFY_TITLE"] = title
    env["ZOEY_NOTIFY_MESSAGE"] = message

    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                _POWERSHELL_SCRIPT,
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception as error:
        return False, str(error)

    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "PowerShell notification failed.").strip()
        return False, error

    return True, None


def notify(title, message):
    title = _validate_text(title, "title", MAX_TITLE_LENGTH)
    message = _validate_text(message, "message", MAX_MESSAGE_LENGTH)

    initialize_database()

    success, error = _run_powershell(title, message)
    if not success:
        return {
            "success": False,
            "message": error or "Notification failed.",
        }

    connection = get_connection()
    connection.execute(
        "INSERT INTO notifications (title, message) VALUES (?, ?)",
        (title, message),
    )
    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "Notification sent.",
    }


def notifications_log(limit=DEFAULT_LOG_LIMIT):
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("limit must be an integer.")
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    if limit > MAX_LOG_LIMIT:
        raise ValueError(f"limit cannot exceed {MAX_LOG_LIMIT}.")

    initialize_database()

    connection = get_connection()
    rows = connection.execute(
        """
        SELECT id, title, message, created_at
        FROM notifications
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    connection.close()

    return [dict(row) for row in rows]
