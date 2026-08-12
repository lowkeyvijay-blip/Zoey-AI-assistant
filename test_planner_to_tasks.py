from database.db import get_connection
from tools.tasks import (
    create_task,
    list_tasks,
    complete_task,
    plan_to_tasks,
)


PLAN = {
    "goal": "I want to finish Zoey today.",
    "steps": [
        {
            "number": 1,
            "title": "Test the memory system",
            "description": "Run the memory tests"
        },
        {
            "number": 2,
            "title": "Test the agent",
            "description": "Run the agent tests"
        },
        {
            "number": 3,
            "title": "Test the planning system",
            "description": "Run the planner tests"
        },
    ],
}

PLAN_TITLES = [step["title"] for step in PLAN["steps"]]

CLEANUP_TITLES = PLAN_TITLES + [
    "Phase 8.3 valid leftover",
    "Phase 8.3 temp task",
]

created_ids = set()


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def delete_by_titles(titles):
    connection = get_connection()

    for title in titles:
        connection.execute(
            "DELETE FROM tasks WHERE title = ?",
            (title,)
        )

    connection.commit()
    connection.close()


def delete_by_ids(ids):
    connection = get_connection()

    for task_id in ids:
        connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )

    connection.commit()
    connection.close()


def count_tasks(title: str) -> int:
    connection = get_connection()

    row = connection.execute(
        "SELECT COUNT(*) AS total FROM tasks WHERE title = ?",
        (title,)
    ).fetchone()

    connection.close()

    return row["total"]


def count_pending_tasks(title: str) -> int:
    connection = get_connection()

    row = connection.execute(
        "SELECT COUNT(*) AS total FROM tasks "
        "WHERE title = ? AND status = 'pending'",
        (title,)
    ).fetchone()

    connection.close()

    return row["total"]


def task_status(task_id: int) -> str:
    connection = get_connection()

    row = connection.execute(
        "SELECT status FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    connection.close()

    return row["status"]


def main():
    print("\nPHASE 8.3 TEST: PLANNER -> TASKS\n")
    print("=" * 60)

    try:

        delete_by_titles(CLEANUP_TITLES)

        print("\nTEST A: CREATION")

        result = plan_to_tasks(PLAN)

        for record in result:
            created_ids.add(record["id"])

        verify(len(result) == 3, "exactly 3 tasks are returned")

        for record, step in zip(result, PLAN["steps"]):
            verify(
                isinstance(record["id"], int),
                f"task has an integer id ({record['id']})"
            )
            verify(
                record["title"] == step["title"],
                f"title matches plan step: '{record['title']}'"
            )
            verify(
                record["status"] == "pending",
                f"task '{record['title']}' has status 'pending'"
            )
            verify(
                record["due_at"] is None,
                f"task '{record['title']}' has due_at None"
            )

        verify(
            [record["title"] for record in result] == PLAN_TITLES,
            "task order matches plan step order"
        )

        print("\nTEST B: DATABASE PERSISTENCE")

        tasks = list_tasks()
        task_titles = {task["title"] for task in tasks}

        for title in PLAN_TITLES:
            verify(
                title in task_titles,
                f"'{title}' exists via list_tasks()"
            )
            verify(
                count_tasks(title) == 1,
                f"'{title}' has exactly 1 row in SQLite"
            )

        connection = get_connection()
        rows = connection.execute(
            "SELECT id, title, status FROM tasks ORDER BY id ASC"
        ).fetchall()
        connection.close()
        db_titles = {row["title"] for row in rows}

        for title in PLAN_TITLES:
            verify(
                title in db_titles,
                f"'{title}' exists via direct database query"
            )

        print("\nTEST C: DUPLICATE PROTECTION")

        result_again = plan_to_tasks(PLAN)

        verify(len(result_again) == 3, "re-run returns 3 task records")

        first_ids = {record["id"] for record in result}
        again_ids = {record["id"] for record in result_again}

        verify(
            again_ids == first_ids,
            "re-run returns the same pending task IDs"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"no duplicate rows created for '{title}'"
            )

        print("\nTEST D: COMPLETED TASK IS NOT REUSED")

        first_record = result_again[0]
        completed_title = first_record["title"]

        complete_task(first_record["id"])

        verify(
            task_status(first_record["id"]) == "completed",
            f"task {first_record['id']} is now completed"
        )

        result_after_complete = plan_to_tasks(PLAN)

        new_pending = [
            record for record in result_after_complete
            if record["title"] == completed_title
        ]

        verify(len(new_pending) == 1, "a new pending task was created")

        verify(
            new_pending[0]["id"] != first_record["id"],
            "the completed task was not reused"
        )

        verify(
            new_pending[0]["status"] == "pending",
            "the new task is pending"
        )

        created_ids.add(new_pending[0]["id"])

        verify(
            count_tasks(completed_title) == 2,
            f"'{completed_title}' now has 1 completed + 1 pending row"
        )
        verify(
            count_pending_tasks(completed_title) == 1,
            f"'{completed_title}' has exactly 1 pending row"
        )

        for title in PLAN_TITLES[1:]:
            verify(
                count_tasks(title) == 1,
                f"unrelated step '{title}' was not duplicated"
            )

        print("\nTEST E: MALFORMED PLAN")

        for bad_plan in (None, {}, {"steps": "invalid"}):

            try:
                plan_to_tasks(bad_plan)
            except ValueError:
                verify(True, f"plan_to_tasks({bad_plan!r}) raises ValueError")
            else:
                raise AssertionError(
                    f"FAIL: plan_to_tasks({bad_plan!r}) "
                    "should raise ValueError"
                )

        print("\nTEST F: MALFORMED STEPS ARE SKIPPED")

        bad_steps_plan = {
            "goal": "cleanup",
            "steps": [
                None,
                {},
                {"number": 2},
                {"title": ""},
                {
                    "number": 3,
                    "title": "Phase 8.3 valid leftover",
                    "description": "Only valid step"
                },
            ],
        }

        bad_steps_result = plan_to_tasks(bad_steps_plan)

        verify(
            len(bad_steps_result) == 1,
            "only the valid step becomes a task"
        )
        verify(
            bad_steps_result[0]["title"] == "Phase 8.3 valid leftover",
            "the surviving task has the correct title"
        )

        created_ids.add(bad_steps_result[0]["id"])

        print("\nTEST G: EXISTING TASK API")

        temp = create_task("Phase 8.3 temp task")
        created_ids.add(temp["id"])

        verify(
            temp["status"] == "pending",
            "create_task() still returns a pending task"
        )

        titles = [task["title"] for task in list_tasks()]

        verify(
            "Phase 8.3 temp task" in titles,
            "list_tasks() still returns created tasks"
        )

        verify(
            complete_task(temp["id"]) is True,
            "complete_task() still completes tasks"
        )

        verify(
            task_status(temp["id"]) == "completed",
            "temp task is now completed"
        )

        print("\n" + "=" * 60)
        print("PHASE 8.3 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(CLEANUP_TITLES)

        print("\nCLEANUP: removed all test-created task rows")


if __name__ == "__main__":
    main()
