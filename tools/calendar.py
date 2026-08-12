"""Local-first calendar tools for Zoey."""

from datetime import datetime, timezone

from database.db import get_connection


_UNSET = object()
_MAX_TITLE = 500
_MAX_TEXT = 4000


def _parse_datetime(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty ISO 8601 datetime string.")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid ISO 8601 datetime.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _store_dt(parsed):
    return parsed.isoformat().replace("+00:00", "Z")


def _row_dict(row):
    return dict(row) if row is not None else None


def _clean_optional(value, name, max_len=_MAX_TEXT):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string or null.")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError(f"{name} is too long.")
    return value or None


def add_event(title, start_at, end_at, location=None, notes=None):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string.")
    title = title.strip()
    if len(title) > _MAX_TITLE:
        raise ValueError("title is too long.")

    start = _parse_datetime(start_at, "start_at")
    end = _parse_datetime(end_at, "end_at")
    if start > end:
        raise ValueError("start_at must be before or equal to end_at.")

    location = _clean_optional(location, "location")
    notes = _clean_optional(notes, "notes")

    connection = get_connection()
    cursor = connection.execute(
        """INSERT INTO events (title, start_at, end_at, location, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (title, _store_dt(start), _store_dt(end), location, notes),
    )
    event_id = cursor.lastrowid
    connection.commit()
    row = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    connection.close()
    return _row_dict(row)


def list_events(start_at=None, end_at=None, limit=50):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError("limit must be a positive integer.")
    if limit > 100:
        limit = 100

    start = _parse_datetime(start_at, "start_at") if start_at is not None else None
    end = _parse_datetime(end_at, "end_at") if end_at is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("start_at must be before or equal to end_at.")

    query = "SELECT * FROM events"
    params = []
    conditions = []
    # Window query returns events that overlap the requested interval.
    if start is not None:
        conditions.append("end_at >= ?")
        params.append(_store_dt(start))
    if end is not None:
        conditions.append("start_at <= ?")
        params.append(_store_dt(end))
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY start_at ASC, id ASC LIMIT ?"
    params.append(limit)

    connection = get_connection()
    rows = connection.execute(query, params).fetchall()
    connection.close()
    return [_row_dict(row) for row in rows]


def upcoming_events(limit=10):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError("limit must be a positive integer.")
    if limit > 100:
        limit = 100
    now = _store_dt(datetime.now(timezone.utc))
    connection = get_connection()
    rows = connection.execute(
        """SELECT * FROM events
           WHERE end_at >= ?
           ORDER BY start_at ASC, id ASC
           LIMIT ?""",
        (now, limit),
    ).fetchall()
    connection.close()
    return [_row_dict(row) for row in rows]


def update_event(event_id, title=_UNSET, start_at=_UNSET, end_at=_UNSET,
                 location=_UNSET, notes=_UNSET):
    if not isinstance(event_id, int) or isinstance(event_id, bool):
        raise ValueError("event_id must be an integer.")

    if all(value is _UNSET for value in (title, start_at, end_at, location, notes)):
        raise ValueError("At least one event field must be provided for update.")

    connection = get_connection()
    existing = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if existing is None:
        connection.close()
        raise ValueError(f"Event {event_id} not found.")

    current = dict(existing)
    new_title = current["title"] if title is _UNSET else title
    new_start = current["start_at"] if start_at is _UNSET else start_at
    new_end = current["end_at"] if end_at is _UNSET else end_at
    new_location = current["location"] if location is _UNSET else location
    new_notes = current["notes"] if notes is _UNSET else notes

    if not isinstance(new_title, str) or not new_title.strip():
        connection.close()
        raise ValueError("title must be a non-empty string.")
    new_title = new_title.strip()
    if len(new_title) > _MAX_TITLE:
        connection.close()
        raise ValueError("title is too long.")

    start = _parse_datetime(new_start, "start_at")
    end = _parse_datetime(new_end, "end_at")
    if start > end:
        connection.close()
        raise ValueError("start_at must be before or equal to end_at.")

    new_location = _clean_optional(new_location, "location")
    new_notes = _clean_optional(new_notes, "notes")

    connection.execute(
        """UPDATE events
           SET title = ?, start_at = ?, end_at = ?, location = ?, notes = ?
           WHERE id = ?""",
        (new_title, _store_dt(start), _store_dt(end), new_location, new_notes, event_id),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    connection.close()
    return _row_dict(row)


def delete_event(event_id):
    if not isinstance(event_id, int) or isinstance(event_id, bool):
        raise ValueError("event_id must be an integer.")
    connection = get_connection()
    cursor = connection.execute("DELETE FROM events WHERE id = ?", (event_id,))
    connection.commit()
    connection.close()
    if cursor.rowcount == 0:
        raise ValueError(f"Event {event_id} not found.")
    return True
