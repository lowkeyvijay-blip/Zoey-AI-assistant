import json

from database.db import get_connection


def _dump(value):
    return json.dumps(value, default=str)


def _load(value):
    if value is None:
        return None

    try:
        return json.loads(value)
    except Exception:
        return None


def _step_to_row(run_id, step):
    return (
        run_id,
        step.get("number"),
        step.get("title"),
        step.get("tool"),
        _dump(step.get("arguments") or {}),
        _dump(step.get("depends_on") or []),
        step.get("task_id"),
        step.get("status", "pending"),
        _dump(step.get("result"))
        if step.get("result") is not None else None,
    )


def create_run(record):
    """Persist an approved plan and its steps; returns run_id."""
    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            INSERT INTO plan_runs (goal, plan_json, status)
            VALUES (?, ?, ?)
            """,
            (
                record.get("goal"),
                _dump(record.get("plan")),
                record.get("status", "approved"),
            )
        )

        run_id = cursor.lastrowid

        for step in record.get("steps", []):

            connection.execute(
                """
                INSERT INTO plan_steps (
                    run_id, number, title, tool,
                    arguments_json, depends_on_json,
                    task_id, status, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _step_to_row(run_id, step)
            )

        connection.commit()

        return run_id

    finally:
        connection.close()


def update_run(run_id, status):
    """Update the run's overall status (write-through)."""
    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE plan_runs
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, run_id)
        )

        connection.commit()

    finally:
        connection.close()


def update_step(run_id, number, step):
    """Persist one step's latest state (write-through)."""
    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE plan_steps
            SET tool = ?, arguments_json = ?,
                depends_on_json = ?, task_id = ?,
                status = ?, result_json = ?
            WHERE run_id = ? AND number = ?
            """,
            (
                step.get("tool"),
                _dump(step.get("arguments") or {}),
                _dump(step.get("depends_on") or []),
                step.get("task_id"),
                step.get("status", "pending"),
                _dump(step.get("result"))
                if step.get("result") is not None else None,
                run_id,
                number,
            )
        )

        connection.commit()

    finally:
        connection.close()


def _row_to_record(run_row, step_rows):

    record = {
        "run_id": run_row["id"],
        "goal": run_row["goal"],
        "plan": _load(run_row["plan_json"]) or {},
        "status": run_row["status"],
        "created_at": run_row["created_at"],
        "updated_at": run_row["updated_at"],
        "steps": [],
    }

    for step in step_rows:

        record["steps"].append({
            "number": step["number"],
            "title": step["title"],
            "tool": step["tool"],
            "arguments": _load(
                step["arguments_json"]
            ) or {},
            "depends_on": _load(
                step["depends_on_json"]
            ) or [],
            "task_id": step["task_id"],
            "status": step["status"],
            "result": _load(step["result_json"]),
        })

    return record


def load_run(run_id):
    connection = get_connection()

    try:

        run_row = connection.execute(
            "SELECT * FROM plan_runs WHERE id = ?",
            (run_id,)
        ).fetchone()

        if run_row is None:
            return None

        step_rows = connection.execute(
            """
            SELECT * FROM plan_steps
            WHERE run_id = ? ORDER BY number ASC
            """,
            (run_id,)
        ).fetchall()

        return _row_to_record(run_row, step_rows)

    finally:
        connection.close()


def load_latest_run():
    connection = get_connection()

    try:

        run_row = connection.execute(
            """
            SELECT * FROM plan_runs
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()

        if run_row is None:
            return None

        step_rows = connection.execute(
            """
            SELECT * FROM plan_steps
            WHERE run_id = ? ORDER BY number ASC
            """,
            (run_row["id"],)
        ).fetchall()

        return _row_to_record(run_row, step_rows)

    finally:
        connection.close()


def list_runs():
    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT r.id, r.goal, r.status,
                   r.created_at, r.updated_at,
                   COUNT(s.number) AS step_count
            FROM plan_runs r
            LEFT JOIN plan_steps s ON s.run_id = r.id
            GROUP BY r.id
            ORDER BY r.id DESC
            """
        ).fetchall()

        return [
            {
                "run_id": row["id"],
                "goal": row["goal"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "step_count": row["step_count"],
            }
            for row in rows
        ]

    finally:
        connection.close()


def mark_interrupted(run_id):
    update_run(run_id, "interrupted")


def delete_run(run_id):
    connection = get_connection()

    try:

        connection.execute(
            "DELETE FROM plan_steps WHERE run_id = ?",
            (run_id,)
        )

        connection.execute(
            "DELETE FROM plan_runs WHERE id = ?",
            (run_id,)
        )

        connection.commit()

    finally:
        connection.close()


def delete_all_runs():
    connection = get_connection()

    try:

        connection.execute("DELETE FROM plan_steps")
        connection.execute("DELETE FROM plan_runs")
        connection.commit()

    finally:
        connection.close()
