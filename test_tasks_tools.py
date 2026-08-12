from database.db import get_connection
from core.tool_manager import (
    TOOLS,
    execute_tool,
    available_tools,
)
from core.agent_loop import ALLOWED_TOOLS
from core.step_validation import (
    TOOL_ARGUMENT_RULES,
    validate_step,
)
from tools.tasks import (
    create_task,
    list_tasks,
    get_task,
    update_task,
    delete_task,
)

import core.agent_loop as agent_loop_module


TITLE_PREFIX = "Phase 10.1"


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def unique_title(label: str) -> str:
    import uuid
    return f"{TITLE_PREFIX} {label} {uuid.uuid4().hex[:8]}"


def delete_by_ids(ids):
    connection = get_connection()

    for task_id in ids:
        connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )

    connection.commit()
    connection.close()


def delete_by_titles(titles):
    connection = get_connection()

    for title in titles:
        connection.execute(
            "DELETE FROM tasks WHERE title = ?",
            (title,)
        )

    connection.commit()
    connection.close()


def task_row(task_id: int):
    connection = get_connection()

    row = connection.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    connection.close()

    return dict(row) if row is not None else None


def main():
    print("\nPHASE 10.1 TEST: TASK MANAGEMENT TOOLS\n")
    print("=" * 60)

    created_ids = []
    created_titles = []

    try:

        print("\nTEST A: GET_TASK")

        title_a = unique_title("get")
        created_titles.append(title_a)
        task = create_task(title_a, "2026-08-12 20:00")
        created_ids.append(task["id"])

        found = get_task(task["id"])
        verify(
            found["id"] == task["id"],
            "get_task returns the requested task id"
        )
        verify(
            found["title"] == title_a,
            "get_task returns the stored title"
        )
        verify(
            found["status"] == "pending",
            "get_task returns the stored status"
        )
        verify(
            found["due_at"] == "2026-08-12 20:00",
            "get_task returns the stored due_at"
        )
        verify(
            "created_at" in found,
            "get_task includes created_at"
        )

        missing = get_task(999999)
        verify(
            missing.get("success") is False,
            "get_task on a missing id reports not found"
        )
        verify(
            "not found" in missing.get("message", ""),
            "get_task's not-found message is clear"
        )

        print("\nTEST B: LIST_TASKS STATUS FILTER")

        title_pending = unique_title("pending")
        title_completed = unique_title("completed")
        created_titles.extend([title_pending, title_completed])

        pending = create_task(title_pending)
        created_ids.append(pending["id"])

        completed = create_task(title_completed)
        created_ids.append(completed["id"])

        from tools.tasks import complete_task as mark_done
        mark_done(completed["id"])

        all_rows = list_tasks()
        verify(
            any(t["id"] == pending["id"] for t in all_rows),
            "list_tasks() still returns pending tasks"
        )
        verify(
            any(t["id"] == completed["id"] for t in all_rows),
            "list_tasks() still returns completed tasks"
        )

        pending_rows = list_tasks(status="pending")
        verify(
            all(t["status"] == "pending" for t in pending_rows),
            "list_tasks(status='pending') returns only pending"
        )
        verify(
            any(t["id"] == pending["id"] for t in pending_rows),
            "the pending filter includes the pending task"
        )
        verify(
            not any(t["id"] == completed["id"] for t in pending_rows),
            "the pending filter excludes completed tasks"
        )

        completed_rows = list_tasks(status="completed")
        verify(
            all(t["status"] == "completed" for t in completed_rows),
            "list_tasks(status='completed') returns only completed"
        )
        verify(
            any(t["id"] == completed["id"] for t in completed_rows),
            "the completed filter includes the completed task"
        )

        try:
            list_tasks(status="bogus")
        except ValueError:
            verify(True, "list_tasks with an invalid status raises")
        else:
            raise AssertionError(
                "FAIL: list_tasks(status='bogus') should raise"
            )

        print("\nTEST C: UPDATE_TASK")

        title_update = unique_title("update")
        created_titles.append(title_update)
        task = create_task(title_update, "2026-08-12 20:00")
        created_ids.append(task["id"])

        new_title = title_update + " renamed"
        updated = update_task(task["id"], title=new_title)
        verify(
            updated["title"] == new_title,
            "update_task can rename a task"
        )
        verify(
            updated["status"] == "pending",
            "rename keeps the original status"
        )
        verify(
            updated["due_at"] == "2026-08-12 20:00",
            "rename keeps the original due_at"
        )

        updated = update_task(
            task["id"],
            due_at="2026-08-13 09:30",
        )
        verify(
            updated["due_at"] == "2026-08-13 09:30",
            "update_task can set a due date"
        )

        updated = update_task(task["id"], due_at=None)
        verify(
            updated["due_at"] is None,
            "update_task can clear the due date with null"
        )

        updated = update_task(task["id"], status="completed")
        verify(
            updated["status"] == "completed",
            "update_task can complete a task"
        )

        updated = update_task(task["id"], status="pending")
        verify(
            updated["status"] == "pending",
            "update_task can reopen a completed task"
        )

        verify(
            task_row(task["id"])["title"] == new_title,
            "the database row reflects the rename"
        )
        verify(
            task_row(task["id"])["due_at"] is None,
            "the database row reflects the cleared due date"
        )

        try:
            update_task(task["id"], status="bogus")
        except ValueError:
            verify(True, "update_task rejects an invalid status")
        else:
            raise AssertionError(
                "FAIL: update_task should reject an invalid status"
            )

        try:
            update_task(task["id"], title="   ")
        except ValueError:
            verify(True, "update_task rejects an empty title")
        else:
            raise AssertionError(
                "FAIL: update_task should reject an empty title"
            )

        try:
            update_task(999999, title="x")
        except ValueError:
            verify(True, "update_task on a missing id raises")
        else:
            raise AssertionError(
                "FAIL: update_task should raise on a missing id"
            )

        try:
            update_task(task["id"])
        except ValueError:
            verify(True, "update_task with nothing to update raises")
        else:
            raise AssertionError(
                "FAIL: update_task should raise with no fields"
            )

        try:
            update_task(task["id"], due_at=42)
        except ValueError:
            verify(True, "update_task rejects a non-string due_at")
        else:
            raise AssertionError(
                "FAIL: update_task should reject a numeric due_at"
            )

        print("\nTEST D: DELETE_TASK")

        title_delete = unique_title("delete")
        created_titles.append(title_delete)
        task = create_task(title_delete)
        created_ids.append(task["id"])

        verify(
            delete_task(task["id"]) is True,
            "delete_task returns True on success"
        )
        verify(
            task_row(task["id"]) is None,
            "the deleted task row is gone from the database"
        )
        verify(
            get_task(task["id"]).get("success") is False,
            "get_task confirms the task no longer exists"
        )

        try:
            delete_task(task["id"])
        except ValueError:
            verify(True, "delete_task on a missing id raises")
        else:
            raise AssertionError(
                "FAIL: delete_task should raise on a missing id"
            )

        print("\nTEST E: CREATE_TASK TITLE VALIDATION")

        try:
            create_task("   ")
        except ValueError:
            verify(True, "create_task rejects an empty title")
        else:
            raise AssertionError(
                "FAIL: create_task should reject an empty title"
            )

        print("\nTEST F: TOOL PIPELINE (execute_tool)")

        title_pipe = unique_title("pipeline")
        created_titles.append(title_pipe)
        task = create_task(title_pipe)
        created_ids.append(task["id"])

        result = execute_tool("get_task", {"task_id": task["id"]})
        verify(
            result.get("success") is True,
            "execute_tool(get_task) reports success"
        )
        verify(
            result["result"]["title"] == title_pipe,
            "execute_tool(get_task) returns the task"
        )

        result = execute_tool(
            "update_task",
            {"task_id": task["id"], "status": "completed"},
        )
        verify(
            result.get("success") is True,
            "execute_tool(update_task) reports success"
        )
        verify(
            result["result"]["status"] == "completed",
            "execute_tool(update_task) applied the change"
        )

        result = execute_tool("list_tasks", {"status": "pending"})
        verify(
            result.get("success") is True,
            "execute_tool(list_tasks) with a filter reports success"
        )
        verify(
            all(t["status"] == "pending" for t in result["result"]),
            "execute_tool(list_tasks) applies the filter"
        )

        result = execute_tool("delete_task", {"task_id": task["id"]})
        verify(
            result.get("success") is True,
            "execute_tool(delete_task) reports success"
        )

        result = execute_tool("update_task", {"task_id": 999999, "title": "x"})
        verify(
            result.get("success") is False,
            "execute_tool(update_task) fails cleanly on a missing id"
        )
        verify(
            "not found" in result.get("error", ""),
            "the pipeline failure message is clear"
        )

        result = execute_tool("delete_task", {"task_id": 999999})
        verify(
            result.get("success") is False,
            "execute_tool(delete_task) fails cleanly on a missing id"
        )

        print("\nTEST G: STEP VALIDATION FOR NEW TOOLS")

        result = validate_step({
            "number": 1,
            "title": "Get",
            "tool": "get_task",
            "arguments": {"task_id": 5},
        })
        verify(result["valid"], "get_task step validates")

        result = validate_step({
            "number": 1,
            "title": "Get",
            "tool": "get_task",
            "arguments": {},
        })
        verify(
            not result["valid"],
            "get_task without task_id is invalid"
        )

        result = validate_step({
            "number": 1,
            "title": "Update",
            "tool": "update_task",
            "arguments": {"task_id": 5, "title": "New"},
        })
        verify(result["valid"], "update_task subset validates")

        result = validate_step({
            "number": 1,
            "title": "Update",
            "tool": "update_task",
            "arguments": {"task_id": 5, "due_at": None},
        })
        verify(
            result["valid"],
            "update_task with null due_at validates"
        )

        result = validate_step({
            "number": 1,
            "title": "Update",
            "tool": "update_task",
            "arguments": {"task_id": "5"},
        })
        verify(
            not result["valid"],
            "update_task with a string task_id is invalid"
        )

        result = validate_step({
            "number": 1,
            "title": "Delete",
            "tool": "delete_task",
            "arguments": {"task_id": 5},
        })
        verify(result["valid"], "delete_task step validates")

        result = validate_step({
            "number": 1,
            "title": "Delete",
            "tool": "delete_task",
            "arguments": {},
        })
        verify(
            not result["valid"],
            "delete_task without task_id is invalid"
        )

        result = validate_step({
            "number": 1,
            "title": "List",
            "tool": "list_tasks",
            "arguments": {"status": "pending"},
        })
        verify(
            result["valid"],
            "list_tasks with a status filter validates"
        )

        print("\nTEST H: FOUR-WAY REGISTRATION SYNC")

        new_tools = {"get_task", "update_task", "delete_task"}

        verify(
            new_tools.issubset(TOOLS),
            "all new tools are in the tool registry"
        )
        verify(
            new_tools.issubset(ALLOWED_TOOLS),
            "all new tools are in ALLOWED_TOOLS"
        )
        verify(
            all(
                name in TOOL_ARGUMENT_RULES
                for name in new_tools
            ),
            "all new tools have argument rules"
        )
        verify(
            "list_tasks" in TOOL_ARGUMENT_RULES
            and "status" in TOOL_ARGUMENT_RULES["list_tasks"],
            "list_tasks gained a status rule"
        )
        verify(
            all(
                name in agent_loop_module.TOOLS
                for name in new_tools
            ),
            "all new tools are documented in the LLM prompt"
        )
        verify(
            set(available_tools()) == set(TOOLS.keys()),
            "available_tools matches the registry"
        )
        verify(
            ALLOWED_TOOLS == set(TOOLS.keys()),
            "ALLOWED_TOOLS exactly matches the registry"
        )

        print("\n" + "=" * 60)
        print("PHASE 10.1 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(created_titles)

        print("\nCLEANUP: removed all test-created task rows")


if __name__ == "__main__":
    main()
