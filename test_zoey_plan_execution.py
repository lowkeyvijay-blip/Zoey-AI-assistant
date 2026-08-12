from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from database.db import get_connection


TEST_MEMORY = "Phase 9.4 test memory"

EXEC_TASK_TITLE = "Phase 9.4 execution test task"

ALPHA_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Finish Alpha - review",
]

BETA_TITLES = [
    "Open Calculator",
    "Open Chrome",
]

GAMMA_TITLES = [
    "Open Notepad",
    "Open Banned App",
    "Open Calculator",
]

DELTA_TITLES = [
    "Finish Delta - step 1",
    "Finish Delta - step 2",
]

REAL_TITLES = [
    EXEC_TASK_TITLE,
    "Use Forbidden Tool",
]

ALL_TITLES = sorted(set(
    ALPHA_TITLES + BETA_TITLES + GAMMA_TITLES
    + DELTA_TITLES + REAL_TITLES
))

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

GAMMA_PLAN = {
    "goal": "Finish Gamma",
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
            "title": "Open Banned App",
            "description": "Try an unapproved app",
            "tool": "open_app",
            "arguments": {"app_name": "banned"},
        },
        {
            "number": 3,
            "title": "Open Calculator",
            "description": "Should never run",
            "tool": "open_app",
            "arguments": {"app_name": "calculator"},
        },
    ],
}

DELTA_PLAN = {
    "goal": "Finish Delta",
    "steps": [
        {
            "number": 1,
            "title": "Finish Delta - step 1",
            "description": "First step",
        },
        {
            "number": 2,
            "title": "Finish Delta - step 2",
            "description": "Second step",
        },
    ],
}

REAL_PLAN = {
    "goal": "Run Real",
    "steps": [
        {
            "number": 1,
            "title": EXEC_TASK_TITLE,
            "description": "Create a real task",
            "tool": "create_task",
            "arguments": {"title": EXEC_TASK_TITLE},
        },
        {
            "number": 2,
            "title": "Use Forbidden Tool",
            "description": "Not an allowed tool",
            "tool": "bogus_tool",
            "arguments": {},
        },
    ],
}


class FakeExecutor:

    def __init__(self):
        self.calls = []

    def __call__(self, tool_name, arguments):
        arguments = dict(arguments or {})
        self.calls.append((tool_name, arguments))

        if arguments.get("app_name") == "banned":
            return {
                "success": False,
                "error": (
                    "I don't have permission to open 'banned'."
                ),
            }

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
        "I want to finish Gamma": {
            "intent": "goal",
            "goal": "Finish Gamma",
            "confidence": 0.95,
        },
        "I want to finish Delta": {
            "intent": "goal",
            "goal": "Finish Delta",
            "confidence": 0.95,
        },
        "I want to run a real plan": {
            "intent": "goal",
            "goal": "Run Real",
            "confidence": 0.95,
        },
        "What's the capital of France?": CONVERSATION,
        "Open Notepad": {
            "intent": "tool",
            "goal": None,
            "confidence": 0.95,
        },
    }


def build_plans():
    return {
        "Finish Alpha": ALPHA_PLAN,
        "Finish Beta": BETA_PLAN,
        "Finish Gamma": GAMMA_PLAN,
        "Finish Delta": DELTA_PLAN,
        "Run Real": REAL_PLAN,
    }


def build_fixture(executor=None):
    orchestrator = Orchestrator(
        planner=ToolPlanner(build_plans()),
        classifier=RuleClassifier(build_rules()),
        executor=executor
    )

    zoey = StubZoey(orchestrator=orchestrator)

    return orchestrator, zoey


def main():
    print(
        "\nPHASE 9.4 TEST: APPROVED PLAN EXECUTION "
        "(deterministic)\n"
    )
    print("=" * 60)

    try:

        delete_by_titles(ALL_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        print("\nTEST 1: ZERO EXECUTION BEFORE APPROVAL")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("I want to finish Alpha")

        verify(
            "Should I add these as tasks?" in response,
            "a plan is presented for approval"
        )
        verify(
            executor.calls == [],
            "no tool ran while the plan awaits approval"
        )
        verify(
            orchestrator.approved_plan is None,
            "no approved plan exists before approval"
        )

        response = zoey.respond("run the plan")

        verify(
            "no approved plan" in response.lower(),
            "executing before approval is refused"
        )
        verify(
            executor.calls == [],
            "refusing execution ran no tools"
        )

        print("\nTEST 2: ZERO EXECUTION ON REJECT")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("I want to finish Alpha")
        response = zoey.respond("no")

        verify(
            response == "OK, I won't add those tasks.",
            "the plan is rejected"
        )
        verify(
            orchestrator.approved_plan is None,
            "a rejected plan leaves no approved plan"
        )

        response = zoey.respond("execute the plan")

        verify(
            "no approved plan" in response.lower(),
            "executing a rejected plan is refused"
        )
        verify(
            executor.calls == [],
            "refusing a rejected plan ran no tools"
        )

        for title in ALPHA_TITLES:
            verify(
                count_tasks(title) == 0,
                f"rejection created no '{title}' tasks"
            )

        print("\nTEST 3: APPROVAL ALONE DOES NOT EXECUTE")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("I want to finish Alpha")
        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" in response,
            "approval saves the tasks"
        )
        verify(
            orchestrator.approved_plan is not None,
            "an approved plan is recorded"
        )
        verify(
            orchestrator.approved_plan["status"] == "approved",
            "the approved plan is not yet running"
        )
        verify(
            executor.calls == [],
            "approval by itself executed nothing"
        )

        print("\nTEST 4: EXECUTE RUNS APPROVED STEPS IN ORDER")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Alpha")
        zoey.respond("yes")

        notepad_ids = [
            row["id"]
            for row in task_rows_by_title("Open Notepad")
        ]
        calculator_ids = [
            row["id"]
            for row in task_rows_by_title("Open Calculator")
        ]
        review_ids = [
            row["id"]
            for row in task_rows_by_title(
                "Finish Alpha - review"
            )
        ]

        created_ids.update(
            notepad_ids + calculator_ids + review_ids
        )

        response = zoey.respond("execute the plan")

        verify(
            "I executed the approved plan:" in response,
            "execution is acknowledged"
        )
        verify(
            "Open Notepad: done" in response,
            "step 1 is reported done"
        )
        verify(
            "Open Calculator: done" in response,
            "step 2 is reported done"
        )
        verify(
            "Finish Alpha - review: no automated action"
            in response,
            "a tool-less step is honestly not auto-executed"
        )

        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
            ],
            "steps ran in plan order through the executor"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the run completes"
        )

        statuses = {
            row["id"]: row["status"]
            for row in task_rows_by_title("Open Notepad")
        }
        verify(
            all(
                statuses[task_id] == "completed"
                for task_id in notepad_ids
            ),
            "the step-1 task is marked completed"
        )

        statuses = {
            row["id"]: row["status"]
            for row in task_rows_by_title("Open Calculator")
        }
        verify(
            all(
                statuses[task_id] == "completed"
                for task_id in calculator_ids
            ),
            "the step-2 task is marked completed"
        )

        statuses = {
            row["id"]: row["status"]
            for row in task_rows_by_title(
                "Finish Alpha - review"
            )
        }
        verify(
            all(
                statuses[task_id] == "pending"
                for task_id in review_ids
            ),
            "the tool-less step task stays pending"
        )

        print("\nTEST 5: A FAILED STEP STOPS THE RUN")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Gamma")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the failure is reported honestly"
        )
        verify(
            "Open Notepad: done" in response,
            "the earlier step is reported done"
        )
        verify(
            "Open Banned App: FAILED" in response,
            "the failing step is reported as failed"
        )
        verify(
            "Open Calculator: not run" in response,
            "the later step is reported as not run"
        )

        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "banned"}),
            ],
            "execution stopped after the failure"
        )
        verify(
            orchestrator.approved_plan["status"] == "failed",
            "the run is marked failed, not completed"
        )

        notepad_rows = task_rows_by_title("Open Notepad")
        verify(
            all(
                row["status"] == "completed"
                for row in notepad_rows
            ),
            "the step-1 task was completed"
        )

        banned_rows = task_rows_by_title("Open Banned App")
        verify(
            all(
                row["status"] == "pending"
                for row in banned_rows
            ),
            "the failed step's task was NOT completed"
        )

        calculator_rows = task_rows_by_title(
            "Open Calculator"
        )
        verify(
            all(
                row["status"] == "pending"
                for row in calculator_rows
            ),
            "the un-run step's task stays pending"
        )

        print("\nTEST 6: STALE APPROVAL CANNOT EXECUTE AN OLD PLAN")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Alpha")
        zoey.respond("yes")
        verify(
            orchestrator.approved_plan is not None,
            "Alpha was approved"
        )

        zoey.respond("I want to finish Beta")
        zoey.respond("no")

        response = zoey.respond("yes")

        verify(
            "I've saved these as tasks:" not in response,
            "a stale 'yes' cannot re-approve a discarded plan"
        )

        response = zoey.respond("execute the plan")

        verify(
            "no approved plan" in response.lower(),
            "the old approved plan cannot be executed"
        )
        verify(
            executor.calls == [],
            "no tools ran for the stale plan"
        )

        verify(
            count_tasks("Open Chrome") == 0,
            "the rejected Beta plan created no tasks"
        )
        verify(
            count_tasks("Finish Alpha - review") == 1,
            "the stale approval added no Alpha tasks"
        )

        print("\nTEST 7: TOOL REQUESTS AND MEMORY ARE UNAFFECTED")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("Open Notepad")

        verify(
            response == "Stub answer: Open Notepad",
            "a direct tool command is not hijacked"
        )
        verify(
            executor.calls == [],
            "a direct tool command does not touch plan execution"
        )

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

        response = zoey.respond("execute the plan")

        verify(
            "no approved plan" in response.lower(),
            "execution without an approved plan does nothing"
        )
        verify(
            executor.calls == [],
            "no tools ran during the whole test"
        )

        print("\nTEST 8: EXECUTION COMMAND VARIANTS")

        delete_by_titles(ALL_TITLES)

        for command in [
            "execute the plan",
            "run the plan",
            "start the plan",
        ]:

            executor = FakeExecutor()
            orchestrator, zoey = build_fixture(
                executor=executor
            )

            zoey.respond("I want to finish Alpha")
            zoey.respond("yes")

            response = zoey.respond(command)

            verify(
                "I executed the approved plan:" in response,
                f"'{command}' triggers execution"
            )
            verify(
                len(executor.calls) == 2,
                f"'{command}' ran both executable steps"
            )

        print("\nTEST 9: A PLAN WITH NO EXECUTABLE STEPS")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to finish Delta")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "none of the steps map to actions I can run"
            " automatically" in response,
            "a tool-less plan is reported as not executable"
        )
        verify(
            executor.calls == [],
            "no tools ran for the tool-less plan"
        )
        verify(
            orchestrator.approved_plan["status"]
            == "no_executable_steps",
            "the run is marked no_executable_steps"
        )

        for title in DELTA_TITLES:
            rows = task_rows_by_title(title)
            verify(
                all(
                    row["status"] == "pending"
                    for row in rows
                ),
                f"'{title}' stays pending after the run"
            )

        print("\nTEST 10: DEFAULT EXECUTOR USES THE EXISTING BOUNDARY")

        delete_by_titles(ALL_TITLES)

        orchestrator = Orchestrator(
            planner=ToolPlanner(build_plans()),
            classifier=RuleClassifier(build_rules())
        )

        zoey = StubZoey(orchestrator=orchestrator)

        zoey.respond("I want to run a real plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the real run reports the forbidden-tool failure"
        )
        verify(
            "Use Forbidden Tool: FAILED" in response,
            "the forbidden tool is rejected"
        )
        verify(
            "Tool 'bogus_tool' is not allowed." in response,
            "the error comes from the existing ALLOWED_TOOLS"
        )

        real_rows = task_rows_by_title(EXEC_TASK_TITLE)
        verify(
            len(real_rows) >= 1,
            "the create_task step executed a real task"
        )
        verify(
            any(
                row["status"] == "completed"
                for row in real_rows
            ),
            "the approved plan task was completed"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.4 TESTS PASSED")

    finally:

        delete_by_ids(created_ids)
        delete_by_titles(ALL_TITLES)
        delete_memories_by_content(TEST_MEMORY)

        print("\nCLEANUP: removed all test-created task and memory rows")


if __name__ == "__main__":
    main()
