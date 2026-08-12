from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from database.db import get_connection


TEST_MEMORY = "Phase 9.3 test memory"

APPROVAL_WORDS = [
    "yes",
    "do it",
    "approve",
    "add them",
    "go ahead",
    "sure",
    "ok",
]

REJECTION_WORDS = [
    "no",
    "cancel",
    "don't do it",
    "discard",
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


class GoalPlanner(Planner):

    def create_plan(self, goal):
        return {
            "goal": goal,
            "steps": [
                {
                    "number": 1,
                    "title": f"{goal} - step 1",
                    "description": f"First action for {goal}",
                },
                {
                    "number": 2,
                    "title": f"{goal} - step 2",
                    "description": f"Second action for {goal}",
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


def build_fixture():
    rules = {
        "I want to finish Alpha": {
            "intent": "goal",
            "goal": "Finish Alpha",
            "confidence": 0.95,
        },
        "I want to finish Beta": {
            "intent": "goal",
            "goal": "Finish Beta",
            "confidence": 0.95,
        },
        "What's the capital of France?": CONVERSATION,
        "Open Notepad": {
            "intent": "tool",
            "goal": None,
            "confidence": 0.95,
        },
    }

    orchestrator = Orchestrator(
        planner=GoalPlanner(),
        classifier=RuleClassifier(rules)
    )

    zoey = StubZoey(orchestrator=orchestrator)

    return orchestrator, zoey


def alpha_titles():
    return [
        "Finish Alpha - step 1",
        "Finish Alpha - step 2",
    ]


def beta_titles():
    return [
        "Finish Beta - step 1",
        "Finish Beta - step 2",
    ]


def all_titles():
    return alpha_titles() + beta_titles()


def main():
    print("\nPHASE 9.3 TEST: PLAN APPROVAL (deterministic)\n")
    print("=" * 60)

    try:

        delete_by_titles(all_titles())
        delete_memories_by_content(TEST_MEMORY)

        orchestrator, zoey = build_fixture()

        print("\nTEST 1: GOAL GENERATES A PLAN BUT ZERO TASKS")

        response = zoey.respond("I want to finish Alpha")

        verify(
            "PLAN:" in response,
            "a plan is presented"
        )
        verify(
            "Should I add these as tasks?" in response,
            "Zoey asks for approval"
        )
        verify(
            "I've saved these as tasks:" not in response,
            "tasks are not claimed as saved"
        )
        verify(
            orchestrator.pending_plan is not None,
            "the pending plan is stored"
        )

        for title in all_titles():
            verify(
                count_tasks(title) == 0,
                f"ZERO tasks created for '{title}'"
            )

        print("\nTEST 2: APPROVAL CREATES THE EXPECTED TASKS")

        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" in response,
            "approval saves the tasks"
        )
        verify(
            orchestrator.pending_plan is None,
            "the pending plan is cleared after approval"
        )

        for title in alpha_titles():
            verify(
                count_tasks(title) == 1,
                f"'{title}' persisted as a task"
            )

        for title in beta_titles():
            verify(
                count_tasks(title) == 0,
                f"'{title}' was not created"
            )

        first_ids = {}

        for title in alpha_titles():
            ids = task_ids_by_title(title)
            created_ids.update(ids)
            first_ids[title] = ids

        print("\nTEST 3: REJECTION CREATES ZERO TASKS")

        response = zoey.respond("I want to finish Alpha")
        verify(
            "Should I add these as tasks?" in response,
            "a new plan awaits approval"
        )

        response = zoey.respond("no")

        verify(
            response == "OK, I won't add those tasks.",
            "rejection is acknowledged"
        )
        verify(
            orchestrator.pending_plan is None,
            "the pending plan is discarded"
        )

        for title in alpha_titles():
            verify(
                count_tasks(title) == 1,
                f"rejection added no '{title}' tasks"
            )

        print("\nTEST 4: DUPLICATE PROTECTION AFTER APPROVAL")

        response = zoey.respond("I want to finish Alpha")
        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" in response,
            "the plan is approved again"
        )

        for title in alpha_titles():
            ids = task_ids_by_title(title)
            created_ids.update(ids)
            verify(
                count_tasks(title) == 1,
                f"'{title}' not duplicated after re-approval"
            )
            verify(
                ids == first_ids[title],
                f"'{title}' reuses the same task IDs"
            )

        print("\nTEST 5: MULTIPLE GOALS DO NOT OVERWRITE STATE INCORRECTLY")

        response = zoey.respond("I want to finish Alpha")
        verify(
            "Finish Alpha - step 1" in response,
            "goal Alpha is pending"
        )

        response = zoey.respond("I want to finish Beta")
        verify(
            "Finish Beta - step 1" in response,
            "goal Beta replaces the pending plan"
        )

        response = zoey.respond("yes")

        for title in beta_titles():
            verify(
                count_tasks(title) == 1,
                f"approval created '{title}' from the NEW plan"
            )

        for title in alpha_titles():
            verify(
                count_tasks(title) == 1,
                f"'{title}' was NOT duplicated by Beta approval"
            )

        print("\nTEST 6: STALE PLAN IS NOT ACCIDENTALLY APPROVED")

        response = zoey.respond("I want to finish Beta")
        response = zoey.respond("cancel")

        verify(
            response == "OK, I won't add those tasks.",
            "the plan is rejected"
        )

        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" not in response,
            "a stale 'yes' cannot approve a discarded plan"
        )

        for title in beta_titles():
            verify(
                count_tasks(title) == 1,
                f"stale approval created no new '{title}'"
            )

        print("\nTEST 7: UNRELATED MESSAGES WHILE AWAITING APPROVAL")

        response = zoey.respond("I want to finish Alpha")
        verify(
            "Should I add these as tasks?" in response,
            "a plan is pending"
        )

        response = zoey.respond("What's the capital of France?")

        verify(
            response == "Stub answer: What's the capital of France?",
            "the unrelated message is answered normally"
        )
        verify(
            orchestrator.pending_plan is not None,
            "the pending plan survives the unrelated message"
        )

        for title in alpha_titles():
            verify(
                count_tasks(title) == 1,
                f"unrelated message created no tasks for '{title}'"
            )

        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" in response,
            "the surviving plan can still be approved"
        )

        print("\nTEST 8: NORMAL CONVERSATION STILL WORKS")

        response = zoey.respond("What's the capital of France?")

        verify(
            response == "Stub answer: What's the capital of France?",
            "conversational question is answered normally"
        )

        response = zoey.respond("yes")

        verify(
            response == "Stub answer: yes",
            "approval words without a pending plan "
            "do not break conversation"
        )

        print("\nTEST 9: MEMORY COMMANDS STILL WORK")

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

        print("\nTEST 10: TOOL EXECUTION IS PRESERVED")

        response = zoey.respond("Open Notepad")

        verify(
            response == "Stub answer: Open Notepad",
            "a tool command is not hijacked by the plan flow"
        )

        for title in all_titles():
            verify(
                count_tasks(title) == 1,
                f"tool command created no '{title}' tasks"
            )

        print("\nTEST 11: APPROVAL / REJECTION KEYWORD VARIANTS")

        for word in APPROVAL_WORDS:

            zoey.respond("I want to finish Alpha")
            response = zoey.respond(word)

            verify(
                "I've saved these as tasks:" in response,
                f"'{word}' approves the plan"
            )

        for title in alpha_titles():
            verify(
                count_tasks(title) == 1,
                f"'{title}' not duplicated across approval variants"
            )

        for word in REJECTION_WORDS:

            zoey.respond("I want to finish Alpha")
            response = zoey.respond(word)

            verify(
                response == "OK, I won't add those tasks.",
                f"'{word}' rejects the plan"
            )

        for title in alpha_titles():
            verify(
                count_tasks(title) == 1,
                f"rejection variants created no '{title}' tasks"
            )

        print("\n" + "=" * 60)
        print("PHASE 9.3 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(all_titles())
        delete_memories_by_content(TEST_MEMORY)

        print("\nCLEANUP: removed all test-created task and memory rows")


if __name__ == "__main__":
    main()
