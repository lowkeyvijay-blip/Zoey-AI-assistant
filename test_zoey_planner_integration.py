from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from database.db import get_connection


PLAN_TITLES = [
    "Test the memory system",
    "Test the agent and tool execution system",
    "Test the planning system",
]

CLEANUP_TITLES = list(PLAN_TITLES)

TEST_MEMORY = "Phase 9.1 test memory"

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


def task_ids_by_title(title: str) -> list:
    connection = get_connection()

    rows = connection.execute(
        "SELECT id FROM tasks WHERE title = ? ORDER BY id ASC",
        (title,)
    ).fetchall()

    connection.close()

    return [row["id"] for row in rows]


def count_memories(content: str) -> int:
    connection = get_connection()

    row = connection.execute(
        "SELECT COUNT(*) AS total FROM memories WHERE content = ?",
        (content,)
    ).fetchone()

    connection.close()

    return row["total"]


def delete_memories_by_content(content: str):
    connection = get_connection()

    connection.execute(
        "DELETE FROM memories WHERE content = ?",
        (content,)
    )

    connection.commit()
    connection.close()


class FakePlanner(Planner):

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


class FakeClassifier:

    def classify(self, message):
        return {
            "intent": "conversation",
            "goal": None,
            "confidence": 1.0,
        }


class StubZoey(Zoey):

    def __init__(self, orchestrator=None):
        super().__init__(orchestrator=orchestrator)

    def analyze_memory(self, message):
        return None

    def compare_memory(self, new_memory):
        return {
            "action": "save",
            "memory_id": None,
        }

    def ask_ai(self, message):
        return f"Stub answer: {message}"


def main():
    print("\nPHASE 9.1 TEST: ORCHESTRATOR IN ZOEY\n")
    print("=" * 60)

    try:

        delete_by_titles(CLEANUP_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        orchestrator = Orchestrator(
            planner=FakePlanner(),
            classifier=FakeClassifier()
        )
        zoey = StubZoey(orchestrator=orchestrator)

        print("\nTEST 1: NORMAL CONVERSATION STILL WORKS")

        response = zoey.respond("What's the capital of France?")

        verify(
            response == "Stub answer: What's the capital of France?",
            "conversational question is answered normally"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 0,
                f"no tasks created for '{title}'"
            )

        print("\nTEST 2: EXPLICIT GOAL PRESENTS A PLAN, WAITS FOR APPROVAL")

        response = zoey.respond(
            "Make a plan to finish Zoey today."
        )

        verify(
            "PLAN:" in response,
            "response contains the plan header"
        )
        verify(
            "Should I add these as tasks?" in response,
            "response asks for approval"
        )
        verify(
            "I've saved these as tasks:" not in response,
            "response does NOT claim tasks were saved yet"
        )

        for title in PLAN_TITLES:
            verify(
                title in response,
                f"response contains '{title}'"
            )
            verify(
                count_tasks(title) == 0,
                f"'{title}' is NOT persisted before approval"
            )

        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" in response,
            "approval response lists saved tasks"
        )

        for title in PLAN_TITLES:
            verify(
                title in response,
                f"approval response contains '{title}'"
            )
            verify(
                count_tasks(title) == 1,
                f"'{title}' persisted as a task after approval"
            )

        first_ids = {}

        for title in PLAN_TITLES:
            ids = task_ids_by_title(title)
            created_ids.update(ids)
            first_ids[title] = ids

        print("\nTEST 3: 'plan:' SYNTAX REACHES THE ORCHESTRATOR")

        response = zoey.respond(
            "plan: I want to finish Zoey today."
        )

        verify(
            "I want to finish Zoey today." in response,
            "the full goal is preserved in the response"
        )

        response = zoey.respond("do it")

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"'{title}' still has exactly 1 row"
            )

        print("\nTEST 4: GOAL COMMAND WITH NO GOAL")

        response = zoey.respond("Make a plan")

        verify(
            response == "What goal should I plan for?",
            "missing goal is handled cleanly"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"no new tasks added for '{title}'"
            )

        print("\nTEST 5: DUPLICATE PROTECTION VIA ZOEY")

        response = zoey.respond(
            "Create a plan to finish Zoey today."
        )

        response = zoey.respond("add them")

        for title in PLAN_TITLES:
            ids = task_ids_by_title(title)
            created_ids.update(ids)
            verify(
                count_tasks(title) == 1,
                f"'{title}' not duplicated on re-run"
            )
            verify(
                ids == first_ids[title],
                f"'{title}' reuses the same task IDs"
            )

        print("\nTEST 6: MEMORY COMMANDS STILL WORK")

        response = zoey.respond("remember " + TEST_MEMORY)

        verify(
            response == "I'll remember that.",
            "the remember command stores a memory"
        )
        verify(
            count_memories(TEST_MEMORY) == 1,
            "the memory is persisted in SQLite"
        )

        response = zoey.respond("memory")

        verify(
            isinstance(response, str) and response,
            "the recall command still returns memories"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.1 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(CLEANUP_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        print("\nCLEANUP: removed all test-created task and memory rows")


if __name__ == "__main__":
    main()
