import urllib.request

from core.orchestrator import Orchestrator
from database.db import get_connection


PLAN_TITLES = [
    "Test the memory system",
    "Test the agent and tool execution system",
    "Test the planning system",
]

CLEANUP_TITLES = list(PLAN_TITLES)

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
    if not ids:
        return

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


def ollama_reachable() -> bool:
    try:
        urllib.request.urlopen(
            "http://localhost:11434/api/tags",
            timeout=3
        )
        return True
    except Exception:
        return False


class FakeClassifier:

    def classify(self, message):
        return {
            "intent": "conversation",
            "goal": None,
            "confidence": 1.0,
        }


class FakePlanner:

    def create_plan(self, goal):
        return {
            "goal": goal,
            "steps": [
                {
                    "number": 1,
                    "title": PLAN_TITLES[0],
                    "description": "Run the memory tests",
                },
                {
                    "number": 2,
                    "title": PLAN_TITLES[1],
                    "description": "Run the agent and tool tests",
                },
                {
                    "number": 3,
                    "title": PLAN_TITLES[2],
                    "description": "Run the planner tests",
                },
            ],
        }


def main():
    print("\nPHASE 9.0 TEST: ORCHESTRATOR (9.3 approval flow)\n")
    print("=" * 60)

    try:

        delete_by_titles(CLEANUP_TITLES)

        print("\nSECTION 1: INPUT HANDLING (deterministic)")

        orchestrator = Orchestrator(
            planner=FakePlanner(),
            classifier=FakeClassifier()
        )

        result = orchestrator.create_plan(None)
        verify(
            result.get("type") == "error",
            "create_plan(None) returns an error result"
        )

        result = orchestrator.create_plan("")
        verify(
            result.get("type") == "error",
            "create_plan('') returns an error result"
        )

        result = orchestrator.create_plan("   ")
        verify(
            result.get("type") == "error",
            "create_plan('   ') returns an error result"
        )

        result = orchestrator.create_plan(123)
        verify(
            result.get("type") == "error",
            "create_plan(123) returns an error result"
        )

        result = orchestrator.handle("")
        verify(
            result.get("type") == "error",
            "handle('') returns an error result"
        )

        result = orchestrator.handle("   ")
        verify(
            result.get("type") == "error",
            "handle('   ') returns an error result"
        )

        message = "What's the capital of France?"
        result = orchestrator.handle(message)
        verify(
            result.get("type") == "conversation",
            "normal conversation is not treated as a goal"
        )
        verify(
            result.get("message") == message,
            "conversation message is preserved"
        )

        result = orchestrator.handle("yes")
        verify(
            result.get("type") == "conversation",
            "approval words without a pending plan "
            "stay conversation"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 0,
                f"no tasks created for '{title}' before a goal is submitted"
            )

        print("\nSECTION 2: CREATE PLAN (deterministic, fake planner)")

        goal = "I want to finish Zoey today."

        result = orchestrator.create_plan(goal)

        verify(
            isinstance(result, dict),
            "a structured result is returned"
        )
        verify(
            result.get("type") == "plan_pending",
            "result type is 'plan_pending'"
        )
        verify(
            result.get("goal") == goal,
            "the goal is preserved"
        )

        plan = result.get("plan")
        verify(
            isinstance(plan, dict),
            "a plan exists"
        )

        steps = plan.get("steps", [])
        verify(
            isinstance(steps, list) and len(steps) == 3,
            "the plan has 3 steps"
        )

        verify(
            "tasks" not in result,
            "a pending plan carries no tasks"
        )
        verify(
            orchestrator.pending_plan is not None,
            "the pending plan is stored"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 0,
                f"ZERO tasks created for '{title}' before approval"
            )

        print("\nSECTION 3: APPROVE (deterministic)")

        result = orchestrator.approve()

        verify(
            result.get("type") == "goal",
            "approval returns a goal result"
        )
        verify(
            orchestrator.pending_plan is None,
            "the pending plan is cleared after approval"
        )

        tasks = result.get("tasks", [])
        verify(
            isinstance(tasks, list) and len(tasks) == 3,
            "approval creates one task per plan step"
        )

        for task in tasks:
            created_ids.add(task["id"])
            verify(
                isinstance(task.get("id"), int),
                f"task has an integer id ({task['id']})"
            )
            verify(
                task.get("status") == "pending",
                f"task '{task['title']}' is pending"
            )
            verify(
                task.get("due_at") is None,
                f"task '{task['title']}' has no due date"
            )

        verify(
            [task["title"] for task in tasks] == PLAN_TITLES,
            "task titles match plan step titles in order"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"'{title}' persisted in SQLite"
            )

        print("\nSECTION 4: DUPLICATE PROTECTION (deterministic)")

        orchestrator.create_plan(goal)
        result_again = orchestrator.approve()

        verify(
            [task["id"] for task in result_again["tasks"]]
            == [task["id"] for task in tasks],
            "repeated goal+approval reuses the same pending task IDs"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"repeated goal+approval created no duplicates for '{title}'"
            )

        orchestrator.create_plan(goal)
        result_no_dedup = orchestrator.approve(
            check_duplicates=False
        )

        for task in result_no_dedup["tasks"]:
            created_ids.add(task["id"])

        verify(
            [task["id"] for task in result_no_dedup["tasks"]]
            != [task["id"] for task in tasks],
            "approve(check_duplicates=False) creates new tasks"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 2,
                f"check_duplicates=False adds a second '{title}' row"
            )

        print("\nSECTION 5: REJECT (deterministic)")

        other_goal = "I want to build a website."
        result = orchestrator.create_plan(other_goal)

        verify(
            result.get("type") == "plan_pending",
            "a new goal creates a pending plan"
        )

        result = orchestrator.reject()

        verify(
            result.get("type") == "goal_rejected",
            "rejection returns a goal_rejected result"
        )
        verify(
            result.get("goal") == other_goal,
            "rejection names the discarded goal"
        )
        verify(
            orchestrator.pending_plan is None,
            "the pending plan is cleared after rejection"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 2,
                f"rejection created no new '{title}' rows"
            )

        result = orchestrator.approve()
        verify(
            result.get("type") == "error",
            "approving with no pending plan returns an error"
        )

        result = orchestrator.reject()
        verify(
            result.get("type") == "error",
            "rejecting with no pending plan returns an error"
        )

        print("\nSECTION 6: REAL PLANNER (Ollama-dependent)")

        reachable = ollama_reachable()
        print(f"  Ollama reachable: {reachable}")
        print("  (If unreachable, Planner returns its fallback plan.)")

        real_orchestrator = Orchestrator()
        result = real_orchestrator.create_plan(goal)

        verify(
            result.get("type") == "plan_pending",
            "real planner returns a pending plan"
        )
        verify(
            real_orchestrator.pending_plan is not None,
            "the real pending plan is stored"
        )

        result = real_orchestrator.approve()

        verify(
            result.get("type") == "goal",
            "approving the real plan returns a goal result"
        )

        plan = result.get("plan", {})
        steps = plan.get("steps", [])
        verify(
            isinstance(steps, list) and len(steps) >= 3,
            "the real plan has steps"
        )

        tasks = result.get("tasks", [])
        verify(
            len(tasks) >= 3,
            "approval created tasks for the real plan"
        )

        step_titles = [step["title"] for step in steps]

        for task in tasks:
            created_ids.add(task["id"])
            verify(
                task["title"] in step_titles,
                f"task '{task['title']}' matches a plan step title"
            )
            verify(
                task.get("status") == "pending",
                f"task '{task['title']}' was not auto-executed"
            )

        print("\n" + "=" * 60)
        print("PHASE 9.0 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(CLEANUP_TITLES)

        print("\nCLEANUP: removed all test-created task rows")


if __name__ == "__main__":
    main()
