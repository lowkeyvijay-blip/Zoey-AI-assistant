from database.db import get_connection


# Sentinel distinguishing "argument not provided" from
# an explicit null (used to clear a due date).
_UNSET = object()


def create_task(title: str, due_at: str | None = None):
    title = title.strip()

    if not title:
        raise ValueError("Task title cannot be empty.")

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO tasks (title, due_at)
        VALUES (?, ?)
        """,
        (title, due_at)
    )

    connection.commit()
    task_id = cursor.lastrowid
    connection.close()

    return {
        "id": task_id,
        "title": title,
        "status": "pending",
        "due_at": due_at
    }


def list_tasks(status: str | None = None):
    connection = get_connection()

    if status is not None:

        if status not in ("pending", "completed"):
            connection.close()
            raise ValueError(
                f"Invalid task status: {status}"
            )

        rows = connection.execute(
            """
            SELECT id, title, status, due_at, created_at
            FROM tasks
            WHERE status = ?
            ORDER BY id DESC
            """,
            (status,)
        ).fetchall()

    else:

        rows = connection.execute(
            """
            SELECT id, title, status, due_at, created_at
            FROM tasks
            ORDER BY id DESC
            """
        ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def get_task(task_id: int):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT id, title, status, due_at, created_at
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return {
            "success": False,
            "message": f"Task {task_id} not found.",
        }

    return dict(row)


def update_task(
    task_id: int,
    title=_UNSET,
    due_at=_UNSET,
    status=_UNSET,
):
    if (
        title is _UNSET
        and due_at is _UNSET
        and status is _UNSET
    ):
        raise ValueError(
            "Nothing to update: provide a title, "
            "due_at or status."
        )

    connection = get_connection()

    row = connection.execute(
        "SELECT id FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    if row is None:
        connection.close()
        raise ValueError(
            f"Task {task_id} not found."
        )

    # title: a non-empty string only; it can never be
    # cleared or emptied.
    if title is not _UNSET:

        if (
            not isinstance(title, str)
            or not title.strip()
        ):
            connection.close()
            raise ValueError(
                "Task title cannot be empty."
            )

        title = title.strip()

    # status: only the two real lifecycle states.
    if status is not _UNSET:

        if status not in ("pending", "completed"):
            connection.close()
            raise ValueError(
                f"Invalid task status: {status}"
            )

    # due_at: _UNSET leaves it unchanged, an explicit
    # None clears it, a string sets it.
    if due_at is not _UNSET and due_at is not None:

        if not isinstance(due_at, str):
            connection.close()
            raise ValueError(
                "Task due_at must be a string or null."
            )

    updates = []
    values = []

    if title is not _UNSET:
        updates.append("title = ?")
        values.append(title)

    if due_at is not _UNSET:
        updates.append("due_at = ?")
        values.append(due_at)

    if status is not _UNSET:
        updates.append("status = ?")
        values.append(status)

    values.append(task_id)

    connection.execute(
        f"UPDATE tasks SET {', '.join(updates)} "
        "WHERE id = ?",
        values
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT id, title, status, due_at, created_at
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    ).fetchone()

    connection.close()

    return dict(row)


def delete_task(task_id: int):
    connection = get_connection()

    cursor = connection.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        raise ValueError(
            f"Task {task_id} not found."
        )

    return True


def complete_task(task_id: int):
    connection = get_connection()

    connection.execute(
        """
        UPDATE tasks
        SET status = 'completed'
        WHERE id = ?
        """,
        (task_id,)
    )

    connection.commit()
    connection.close()

    return True


def _existing_pending_task(title: str):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT id, title, status, due_at
        FROM tasks
        WHERE title = ? AND status = 'pending'
        ORDER BY id ASC
        LIMIT 1
        """,
        (title,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "due_at": row["due_at"],
    }


def plan_to_tasks(plan, check_duplicates: bool = True):
    """
    Convert a structured plan into persistent tasks.

    plan must be a dict containing a "steps" list. Each step
    is a dict with a non-empty "title". Returns one task record
    per valid step, preserving plan order.
    """

    if not isinstance(plan, dict):
        raise ValueError(
            "Plan must be a dictionary with a 'steps' list."
        )

    steps = plan.get("steps")

    if not isinstance(steps, list):
        raise ValueError(
            "Plan must be a dictionary with a 'steps' list."
        )

    tasks = []

    for step in steps:

        if not isinstance(step, dict):
            continue

        title = str(step.get("title", "")).strip()

        if not title:
            continue

        if check_duplicates:

            existing = _existing_pending_task(title)

            if existing is not None:
                tasks.append(existing)
                continue

        tasks.append(create_task(title))

    return tasks