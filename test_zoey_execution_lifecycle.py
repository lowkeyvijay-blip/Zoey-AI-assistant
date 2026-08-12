from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from database.db import get_connection


TEST_MEMORY = "Phase 9.5 test memory"

ALPHA_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Finish Alpha - review",
]

EPSILON_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
    "Review Epsilon",
]

ALL_TITLES = sorted(set(ALPHA_TITLES + EPSILON_TITLES))

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


def task_rows_by_title(title: str) -> list:
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT id, title, status
        FROM tasks
        WHERE title = ?
        ORDER BY id ASC
        """,
        (title,)
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


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


class ToolPlanner(Planner):

    def __init__(self, plans=None):
        self.plans = dict(plans or {})

    def create_plan(self, goal):
        plan = self.plans.get(goal)

        if plan is not None:
            return plan

        return {
            "goal": goal,
            "steps": [],
        }


ALPHA_PLAN = {
    "goal": "Finish Alpha",
    "steps": [
        {
            "number": 1,
            "title": "Open Notepad",
            "description": "Open the editor",
            "tool": "open_app",
            "arguments": {"app_name": "notepad"},
        },
        {
            "number": 2,
            "title": "Open Calculator",
            "description": "Open the calculator",
            "tool": "open_app",
            "arguments": {"app_name": "calculator"},
        },
        {
            "number": 3,
            "title": "Finish Alpha - review",
            "description": "Review the result",
        },
    ],
}

BETA_PLAN = {
    "goal": "Finish Beta",
    "steps": [
        {
            "number": 1,
            "title": "Open Calculator",
            "description": "Open the calculator",
            "tool": "open_app",
            "arguments": {"app_name": "calculator"},
        },
        {
            "number": 2,
            "title": "Open Chrome",
            "description": "Open the browser",
            "tool": "open_app",
            "arguments": {"app_name": "chrome"},
        },
    ],
}

EPSILON_PLAN = {
    "goal": "Finish Epsilon",
    "steps": [
        {
            "number": 1,
            "title": "Open Notepad",
            "description": "Open the editor",
            "tool": "open_app",
            "arguments": {"app_name": "notepad"},
        },
        {
            "number": 2,
            "title": "Open Calculator",
            "description": "Open the calculator",
            "tool": "open_app",
            "arguments": {"app_name": "calculator"},
        },
        {
            "number": 3,
            "title": "Open Chrome",
            "description": "Open the browser",
            "tool": "open_app",
            "arguments": {"app_name": "chrome"},
        },
        {
            "number": 4,
            "title": "Review Epsilon",
            "description": "Review the result",
        },
    ],
}


class FakeExecutor:

    def __init__(self):
        self.calls = []

    def __call__(self, tool_name, arguments):
        arguments = dict(arguments or {})
        self.calls.append((tool_name, arguments))

        return {
            "success": True,
            "result": {
                "tool": tool_name,
                **arguments
            }
        }


class CancellingExecutor:

    def __init__(self, orchestrator=None, cancel_on=None):
        self.calls = []
        self.orchestrator = orchestrator
        self.cancel_on = cancel_on
        self.running_snapshot = None

    def __call__(self, tool_name, arguments):
        arguments = dict(arguments or {})
        self.calls.append((tool_name, arguments))

        if (tool_name, arguments) == self.cancel_on:
            self.running_snapshot = (
                self.orchestrator.execution_status()
            )
            self.orchestrator.cancel_execution()

        return {
            "success": True,
            "result": {
                "tool": tool_name,
                **arguments
            }
        }


class ReentryExecutor:

    def __init__(self, orchestrator=None):
        self.calls = []
        self.orchestrator = orchestrator
        self.reentry_result = None

    def __call__(self, tool_name, arguments):
        arguments = dict(arguments or {})
        self.calls.append((tool_name, arguments))

        if len(self.calls) == 2:
            self.reentry_result = self.orchestrator.handle(
                "execute the plan"
            )

        return {
            "success": True,
            "result": {
                "tool": tool_name,
                **arguments
            }
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


def build_rules():
    return {
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
        "I want to finish Epsilon": {
            "intent": "goal",
            "goal": "Finish Epsilon",
            "confidence": 0.95,
        },
    }


def build_plans():
    return {
        "Finish Alpha": ALPHA_PLAN,
        "Finish Beta": BETA_PLAN,
        "Finish Epsilon": EPSILON_PLAN,
    }


def build_fixture(
    executor=None,
    task_completer=None
):
    orchestrator = Orchestrator(
        planner=ToolPlanner(build_plans()),
        classifier=RuleClassifier(build_rules()),
        executor=executor,
        task_completer=task_completer
    )

    zoey = StubZoey(orchestrator=orchestrator)

    return orchestrator, zoey


def main():
    print(
        "\nPHASE 9.5 TEST: EXECUTION LIFECYCLE "
        "(deterministic)\n"
    )
    print("=" * 60)

    try:

        delete_by_titles(ALL_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        print("\nTEST 1: NO EXECUTION BEFORE APPROVAL")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Alpha")

        response = zoey.respond("execute the plan")

        verify(
            "no approved plan" in response.lower(),
            "execution before approval is refused"
        )
        verify(
            executor.calls == [],
            "no tool ran before approval"
        )

        print("\nTEST 2: APPROVAL ALONE DOES NOT EXECUTE "
              "AND A FINISHED PLAN REFUSES RE-EXECUTION")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Alpha")
        zoey.respond("yes")

        verify(
            executor.calls == [],
            "approval by itself executed nothing"
        )

        response = zoey.respond("execute the plan")

        verify(
            "I executed the approved plan:" in response,
            "the plan executes once approved"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the run reaches completed"
        )
        verify(
            len(executor.calls) == 2,
            "both executable steps ran"
        )

        calls_after_first = list(executor.calls)

        response = zoey.respond("execute the plan")

        verify(
            "already finished" in response.lower(),
            "a completed run refuses to execute again"
        )
        verify(
            executor.calls == calls_after_first,
            "the refused re-execution ran no tools"
        )

        response = zoey.respond("stop the plan")

        verify(
            "already finished" in response.lower(),
            "stopping a completed run is refused"
        )

        print("\nTEST 3: EXPLICIT RE-RUN")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Alpha")
        zoey.respond("yes")
        zoey.respond("execute the plan")

        verify(
            len(executor.calls) == 2,
            "first execution ran both steps"
        )

        response = zoey.respond("re-run the plan")

        verify(
            "I executed the approved plan:" in response,
            "an explicit re-run executes again"
        )
        verify(
            len(executor.calls) == 4,
            "the re-run executed both steps again"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the re-run completes"
        )

        print("\nTEST 4: CANCEL BEFORE START")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Beta")
        zoey.respond("yes")

        response = zoey.respond("stop the plan")

        verify(
            "I stopped the plan" in response,
            "cancelling an approved-but-unrun plan is acked"
        )
        verify(
            "cancelled" in response,
            "the steps are reported as cancelled"
        )
        verify(
            executor.calls == [],
            "cancellation before start ran no tools"
        )
        verify(
            orchestrator.approved_plan["status"] == "cancelled",
            "the run is marked cancelled"
        )

        response = zoey.respond("execute the plan")

        verify(
            "already finished" in response.lower(),
            "a cancelled run refuses to execute"
        )
        verify(
            executor.calls == [],
            "no tools ran for the cancelled run"
        )

        response = zoey.respond("re-run the plan")

        verify(
            "I executed the approved plan:" in response,
            "re-run resets a cancelled plan and executes it"
        )
        verify(
            len(executor.calls) == 2,
            "the re-run executed both steps"
        )

        print("\nTEST 5: COOPERATIVE CANCEL BETWEEN STEPS")

        delete_by_titles(ALL_TITLES)

        executor = CancellingExecutor(
            None,
            cancel_on=(
                "open_app",
                {"app_name": "calculator"}
            )
        )
        orchestrator, zoey = build_fixture(executor=executor)
        executor.orchestrator = orchestrator

        zoey.respond("I want to finish Epsilon")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan" in response,
            "the run reports a mid-run stop"
        )
        verify(
            "Open Notepad: done" in response,
            "completed work before the cancel is kept"
        )
        verify(
            "Open Calculator: done" in response,
            "the in-flight step that requested cancel finished"
        )
        verify(
            "Open Chrome: cancelled" in response,
            "the later step is cancelled"
        )
        verify(
            "Review Epsilon: cancelled" in response,
            "the tool-less later step is cancelled too"
        )

        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
            ],
            "the executor never ran the cancelled step"
        )
        verify(
            orchestrator.approved_plan["status"] == "cancelled",
            "the run is marked cancelled"
        )

        snapshot = executor.running_snapshot
        verify(
            snapshot is not None
            and snapshot["status"] == "running",
            "the status query during a run reports running"
        )

        notepad_rows = task_rows_by_title("Open Notepad")
        verify(
            all(
                row["status"] == "completed"
                for row in notepad_rows
            ),
            "the completed step's task is marked done"
        )

        chrome_rows = task_rows_by_title("Open Chrome")
        verify(
            all(
                row["status"] == "pending"
                for row in chrome_rows
            ),
            "the cancelled step's task stays pending"
        )

        print("\nTEST 6: RE-ENTRY WHILE RUNNING IS REFUSED")

        delete_by_titles(ALL_TITLES)

        executor = ReentryExecutor(None)
        orchestrator, zoey = build_fixture(executor=executor)
        executor.orchestrator = orchestrator

        zoey.respond("I want to finish Beta")
        zoey.respond("yes")

        zoey.respond("execute the plan")

        reentry = executor.reentry_result

        verify(
            reentry is not None,
            "the nested execution attempt returned a result"
        )
        verify(
            reentry.get("type") == "error",
            "the nested execution is refused"
        )
        verify(
            "already running" in reentry.get(
                "error",
                ""
            ).lower(),
            "the refusal says the plan is already running"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the outer run still completes"
        )

        print("\nTEST 7: TASK-WRITE FAILURE IS REPORTED HONESTLY")

        delete_by_titles(ALL_TITLES)

        def failing_task_completer(task_id):
            raise RuntimeError(
                "simulated task write failure"
            )

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(
            executor=executor,
            task_completer=failing_task_completer
        )

        zoey.respond("I want to finish Alpha")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I executed the approved plan:" in response,
            "the run still reports the executed steps"
        )
        verify(
            "Note:" in response,
            "the response surfaces a warnings note"
        )
        verify(
            "couldn't mark task" in response,
            "the task-write failure is reported honestly"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the run is completed because the tools ran"
        )

        print("\nTEST 8: STATUS QUERY")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("plan status")

        verify(
            "There's no plan in progress" in response,
            "idle status is reported"
        )

        zoey.respond("I want to finish Alpha")

        response = zoey.respond("plan status")

        verify(
            "Plan status: pending_approval" in response,
            "pending approval status is reported"
        )

        zoey.respond("yes")

        response = zoey.respond("plan status")

        verify(
            "Plan status: approved" in response,
            "approved status is reported"
        )

        zoey.respond("execute the plan")

        response = zoey.respond("plan status")

        verify(
            "Plan status: completed" in response,
            "completed status is reported"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
            ],
            "the status queries themselves ran no tools"
        )

        print("\nTEST 9: CANCEL VS REJECT DO NOT COLLIDE")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Beta")

        response = zoey.respond("cancel")

        verify(
            response == "OK, I won't add those tasks.",
            "'cancel' while awaiting approval rejects the plan"
        )
        verify(
            orchestrator.approved_plan is None,
            "the rejected plan left no approved plan"
        )

        zoey.respond("I want to finish Beta")

        response = zoey.respond("stop the plan")

        verify(
            "no plan to stop" in response.lower(),
            "'stop the plan' is an execution command, "
            "not a rejection"
        )
        verify(
            count_tasks("Open Calculator") == 0,
            "the pending plan was not approved or created"
        )

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Alpha")
        zoey.respond("yes")
        zoey.respond("execute the plan")

        response = zoey.respond("cancel")

        verify(
            "Stub answer: cancel" in response,
            "after approval 'cancel' is ordinary "
            "conversation, not an execution command"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
            ],
            "the post-approval 'cancel' ran no extra tools"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.5 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(ALL_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        print("\nCLEANUP: removed all test-created task and memory rows")


if __name__ == "__main__":
    main()
