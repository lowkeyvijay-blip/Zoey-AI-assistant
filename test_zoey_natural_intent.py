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

TEST_MEMORY = "Phase 9.2 test memory"

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


CONVERSATION = {
    "intent": "conversation",
    "goal": None,
    "confidence": 1.0,
}


class RuleClassifier:

    def __init__(self, rules=None):
        self.rules = dict(rules or {})

    def classify(self, message):
        return self.rules.get(
            message,
            CONVERSATION
        )


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


def pending_plan_checks(response, goal_text):
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
    verify(
        goal_text in response,
        f"response contains the cleaned goal '{goal_text}'"
    )
    for title in PLAN_TITLES:
        verify(
            title in response,
            f"response contains '{title}'"
        )


def approve_checks(response):
    verify(
        "I've saved these as tasks:" in response,
        "approval response lists saved tasks"
    )
    for title in PLAN_TITLES:
        verify(
            title in response,
            f"approval response contains '{title}'"
        )


def main():
    print("\nPHASE 9.2 TEST: NATURAL INTENT IN ZOEY (deterministic)\n")
    print("=" * 60)

    try:

        delete_by_titles(CLEANUP_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        rules = {
            "I want to finish Zoey today": {
                "intent": "goal",
                "goal": "Finish Zoey today",
                "confidence": 0.9,
            },
            "I need to build a website for a client": {
                "intent": "goal",
                "goal": "Build a website for a client",
                "confidence": 0.95,
            },
            "Help me prepare for tomorrow's exam": {
                "intent": "goal",
                "goal": "Prepare for tomorrow's exam",
                "confidence": 0.9,
            },
            "What's the capital of France?": CONVERSATION,
            "Open Notepad": {
                "intent": "tool",
                "goal": None,
                "confidence": 0.95,
            },
            "I prefer working at night": {
                "intent": "memory",
                "goal": None,
                "confidence": 0.9,
            },
            "Maybe I should clean my desk sometime": {
                "intent": "goal",
                "goal": "Clean my desk",
                "confidence": 0.4,
            },
        }

        orchestrator = Orchestrator(
            planner=FakePlanner(),
            classifier=RuleClassifier(rules)
        )

        zoey = StubZoey(orchestrator=orchestrator)

        print("\nTEST 1: 'I want to finish Zoey today' -> GOAL")

        response = zoey.respond("I want to finish Zoey today")

        pending_plan_checks(response, "Finish Zoey today")

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 0,
                f"'{title}' NOT persisted before approval"
            )

        response = zoey.respond("yes")

        approve_checks(response)

        first_ids = {}

        for title in PLAN_TITLES:
            ids = task_ids_by_title(title)
            created_ids.update(ids)
            first_ids[title] = ids
            verify(
                count_tasks(title) == 1,
                f"'{title}' persisted as a task after approval"
            )

        print("\nTEST 2: 'I need to build a website for a client' -> GOAL")

        response = zoey.respond(
            "I need to build a website for a client"
        )

        pending_plan_checks(
            response,
            "Build a website for a client"
        )

        response = zoey.respond("approve")

        approve_checks(response)

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"'{title}' not duplicated for the second goal"
            )

        print("\nTEST 3: 'Help me prepare for tomorrow's exam' -> GOAL")

        response = zoey.respond(
            "Help me prepare for tomorrow's exam"
        )

        pending_plan_checks(
            response,
            "Prepare for tomorrow's exam"
        )

        response = zoey.respond("add them")

        approve_checks(response)

        for title in PLAN_TITLES:
            ids = task_ids_by_title(title)
            created_ids.update(ids)
            verify(
                ids == first_ids[title],
                f"'{title}' reuses the same pending task IDs"
            )

        print("\nTEST 4: QUESTION STAYS CONVERSATION")

        response = zoey.respond(
            "What's the capital of France?"
        )

        verify(
            response == "Stub answer: What's the capital of France?",
            "the question is answered normally"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"no new tasks created for '{title}'"
            )

        print("\nTEST 5: 'Open Notepad' IS NOT A GOAL")

        response = zoey.respond("Open Notepad")

        verify(
            response == "Stub answer: Open Notepad",
            "tool command is not treated as a goal"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"no new tasks created for '{title}'"
            )

        print("\nTEST 6: MEMORY STATEMENT IS NOT A GOAL")

        response = zoey.respond("I prefer working at night")

        verify(
            response == "Stub answer: I prefer working at night",
            "memory statement is not treated as a goal"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"no new tasks created for '{title}'"
            )

        print("\nTEST 7: AMBIGUOUS LOW-CONFIDENCE INPUT IS SAFE")

        response = zoey.respond(
            "Maybe I should clean my desk sometime"
        )

        verify(
            response == "Stub answer: Maybe I should clean my desk sometime",
            "low-confidence input stays conversation"
        )

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"no new tasks created for '{title}'"
            )

        print("\nTEST 8: EXPLICIT COMMAND IS PRESERVED")

        response = zoey.respond(
            "Make a plan to finish Zoey today"
        )

        pending_plan_checks(response, "finish Zoey today")

        response = zoey.respond("yes")

        approve_checks(response)

        for title in PLAN_TITLES:
            verify(
                count_tasks(title) == 1,
                f"explicit command reuses existing '{title}'"
            )

        print("\nTEST 9: STRUCTURED INTENT OUTPUT")

        command_intent = orchestrator.detect_intent(
            "Make a plan to build a website"
        )
        verify(
            command_intent.get("type") == "goal"
            and command_intent.get("source") == "command",
            "command input yields a structured goal intent"
        )
        verify(
            command_intent.get("confidence") == 1.0,
            "command intent has maximum confidence"
        )

        natural_intent = orchestrator.detect_intent(
            "I want to finish Zoey today"
        )
        verify(
            natural_intent.get("type") == "goal"
            and natural_intent.get("source") == "classifier",
            "natural goal yields a structured goal intent"
        )
        verify(
            natural_intent.get("goal") == "Finish Zoey today",
            "structured goal carries the cleaned goal"
        )

        conversation_intent = orchestrator.detect_intent(
            "What's the capital of France?"
        )
        verify(
            conversation_intent.get("type") == "conversation"
            and conversation_intent.get("intent") == "conversation",
            "question yields a structured conversation intent"
        )
        verify(
            "confidence" in conversation_intent,
            "conversation intent reports confidence"
        )

        no_input = orchestrator.detect_intent("")
        verify(
            no_input.get("type") == "error",
            "empty input yields an error intent"
        )

        print("\nTEST 10: EXPLICIT MEMORY COMMAND STILL WORKS")

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
        print("PHASE 9.2 INTEGRATION TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(CLEANUP_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        print("\nCLEANUP: removed all test-created task and memory rows")


if __name__ == "__main__":
    main()
