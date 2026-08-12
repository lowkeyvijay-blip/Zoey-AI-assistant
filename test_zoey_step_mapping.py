from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from database.db import get_connection


VALID_TITLES = [
    "Create a review task",
    "List current tasks",
]

INVALID_TOOL_TITLES = [
    "Open Notepad",
    "Use Forbidden Tool",
]

MISSING_ARG_TITLES = [
    "Open Notepad",
    "Open Calculator",
]

WRONG_TYPE_TITLES = [
    "Complete a task",
]

SEMANTIC_TITLES = [
    "Open Notepad",
    "Open Banned App",
]

ALL_TITLES = sorted(set(
    VALID_TITLES
    + INVALID_TOOL_TITLES
    + MISSING_ARG_TITLES
    + WRONG_TYPE_TITLES
    + SEMANTIC_TITLES
))


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


VALID_PLAN = {
    "goal": "Run Valid",
    "steps": [
        {
            "number": 1,
            "title": "Create a review task",
            "description": "Create a task",
            "tool": "create_task",
            "arguments": {"title": "Review the mapping"},
        },
        {
            "number": 2,
            "title": "List current tasks",
            "description": "List tasks",
            "tool": "list_tasks",
        },
    ],
}

INVALID_TOOL_PLAN = {
    "goal": "Run Invalid Tool",
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
            "title": "Use Forbidden Tool",
            "description": "Not an allowed tool",
            "tool": "bogus_tool",
            "arguments": {},
        },
    ],
}

MISSING_ARG_PLAN = {
    "goal": "Run Missing Arg",
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
            "description": "Omits the required argument",
            "tool": "open_app",
        },
    ],
}

WRONG_TYPE_PLAN = {
    "goal": "Run Wrong Type",
    "steps": [
        {
            "number": 1,
            "title": "Complete a task",
            "description": "Wrong task_id type",
            "tool": "complete_task",
            "arguments": {"task_id": "not-an-int"},
        },
    ],
}

SEMANTIC_PLAN = {
    "goal": "Run Semantic",
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
            "description": "Structurally valid, semantically banned",
            "tool": "open_app",
            "arguments": {"app_name": "banned"},
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
        "I want to run a valid plan": {
            "intent": "goal",
            "goal": "Run Valid",
            "confidence": 0.95,
        },
        "I want to run an invalid tool plan": {
            "intent": "goal",
            "goal": "Run Invalid Tool",
            "confidence": 0.95,
        },
        "I want to run a missing-arg plan": {
            "intent": "goal",
            "goal": "Run Missing Arg",
            "confidence": 0.95,
        },
        "I want to run a wrong-type plan": {
            "intent": "goal",
            "goal": "Run Wrong Type",
            "confidence": 0.95,
        },
        "I want to run a semantic plan": {
            "intent": "goal",
            "goal": "Run Semantic",
            "confidence": 0.95,
        },
    }


def build_plans():
    return {
        "Run Valid": VALID_PLAN,
        "Run Invalid Tool": INVALID_TOOL_PLAN,
        "Run Missing Arg": MISSING_ARG_PLAN,
        "Run Wrong Type": WRONG_TYPE_PLAN,
        "Run Semantic": SEMANTIC_PLAN,
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
        "\nPHASE 9.6 TEST: STEP MAPPING THROUGH ZOEY "
        "(deterministic)\n"
    )
    print("=" * 60)

    try:

        delete_by_titles(ALL_TITLES)

        print("\nTEST 1: STEPS WITHOUT ARGUMENTS ARE NORMALIZED")

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a valid plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I executed the approved plan:" in response,
            "the valid plan executes"
        )
        verify(
            "Create a review task: done" in response,
            "the create_task step reports done"
        )
        verify(
            "List current tasks: done" in response,
            "the argument-less list_tasks step runs"
        )
        verify(
            executor.calls == [
                (
                    "create_task",
                    {"title": "Review the mapping"},
                ),
                ("list_tasks", {}),
            ],
            "the omitted arguments were normalized to {} "
            "and the executor received valid objects"
        )

        print("\nTEST 2: AN UNKNOWN TOOL NEVER EXECUTES")

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run an invalid tool plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the run stops on the invalid step"
        )
        verify(
            "Use Forbidden Tool: FAILED - "
            "Tool 'bogus_tool' is not allowed."
            in response,
            "the validation error is reported for the "
            "invalid tool"
        )
        verify(
            "Open Notepad: done" in response,
            "the earlier valid step still ran"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
            ],
            "the invalid tool never reached the executor"
        )
        verify(
            orchestrator.approved_plan["status"] == "failed",
            "the run is marked failed"
        )

        print("\nTEST 3: A MISSING REQUIRED ARGUMENT NEVER EXECUTES")

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a missing-arg plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the run stops on the invalid step"
        )
        verify(
            "Open Calculator: FAILED - "
            "Tool 'open_app' requires 'app_name'."
            in response,
            "the missing-argument error is reported"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
            ],
            "the argument-less open_app never executed"
        )

        print("\nTEST 4: A WRONG ARGUMENT TYPE NEVER EXECUTES")

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a wrong-type plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the run stops on the wrong-type step"
        )
        verify(
            "Complete a task: FAILED - "
            "Tool 'complete_task' argument 'task_id' "
            "must be an integer."
            in response,
            "the wrong-type error is reported"
        )
        verify(
            executor.calls == [],
            "the wrong-type step never reached the executor"
        )

        print("\nTEST 5: SEMANTIC FAILURES STILL HAPPEN AT RUNTIME")

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a semantic plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the run stops on the runtime failure"
        )
        verify(
            "Open Banned App: FAILED - "
            "I don't have permission to open 'banned'."
            in response,
            "the semantic failure is reported at runtime"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "banned"}),
            ],
            "the structurally valid step WAS passed to "
            "the executor and failed there"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.6 STEP MAPPING TESTS PASSED")

    finally:

        delete_by_titles(ALL_TITLES)

        print("\nCLEANUP: removed all test-created task rows")


if __name__ == "__main__":
    main()
