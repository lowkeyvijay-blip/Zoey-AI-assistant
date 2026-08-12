from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from database.db import get_connection
from tools.tasks import complete_task


SEQ_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
    "Review Sequential",
]

FWD_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
]

INVALID_REF_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
]

CYCLE_TITLES = [
    "Open Notepad",
    "Open Calculator",
]

NOT_AUTO_DEP_TITLES = [
    "Review setup",
    "Open Notepad",
    "Open Calculator",
]

DEP_FAIL_TITLES = [
    "Open Notepad",
    "Open Banned App",
    "Open Chrome",
]

RESUME_CANCEL_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
]

RESUME_FAIL_TITLES = [
    "Open Notepad",
    "Open Banned App",
    "Open Chrome",
]

RETRY_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
]

ALL_TITLES = sorted(set(
    SEQ_TITLES
    + FWD_TITLES
    + INVALID_REF_TITLES
    + CYCLE_TITLES
    + NOT_AUTO_DEP_TITLES
    + DEP_FAIL_TITLES
    + RESUME_CANCEL_TITLES
    + RESUME_FAIL_TITLES
    + RETRY_TITLES
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


def step(number, title, tool=None, arguments=None, depends_on=None):
    item = {
        "number": number,
        "title": title,
    }
    if tool:
        item["tool"] = tool
    if arguments is not None:
        item["arguments"] = arguments
    if depends_on is not None:
        item["depends_on"] = depends_on
    return item


def build_plans():
    return {
        "Run Sequential": {
            "goal": "Run Sequential",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}),
                step(2, "Open Calculator", "open_app", {"app_name": "calculator"}, 1),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}, [1, 2]),
                step(4, "Review Sequential"),
            ],
        },
        "Run Forward": {
            "goal": "Run Forward",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}, 2),
                step(2, "Open Calculator", "open_app", {"app_name": "calculator"}),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}, 1),
            ],
        },
        "Run Invalid Ref": {
            "goal": "Run Invalid Ref",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}),
                step(2, "Open Calculator", "open_app", {"app_name": "calculator"}, 99),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}),
            ],
        },
        "Run Cycle": {
            "goal": "Run Cycle",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}, 2),
                step(2, "Open Calculator", "open_app", {"app_name": "calculator"}, 1),
            ],
        },
        "Run Not Auto Dep": {
            "goal": "Run Not Auto Dep",
            "steps": [
                step(1, "Review setup"),
                step(2, "Open Notepad", "open_app", {"app_name": "notepad"}, 1),
                step(3, "Open Calculator", "open_app", {"app_name": "calculator"}, 1),
            ],
        },
        "Run Dep Fail": {
            "goal": "Run Dep Fail",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}),
                step(2, "Open Banned App", "open_app", {"app_name": "banned"}),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}, 2),
            ],
        },
        "Run Resume Cancel": {
            "goal": "Run Resume Cancel",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}),
                step(2, "Open Calculator", "open_app", {"app_name": "calculator"}),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}),
            ],
        },
        "Run Resume Fail": {
            "goal": "Run Resume Fail",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}),
                step(2, "Open Banned App", "open_app", {"app_name": "banned"}),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}),
            ],
        },
        "Run Retry": {
            "goal": "Run Retry",
            "steps": [
                step(1, "Open Notepad", "open_app", {"app_name": "notepad"}),
                step(2, "Open Calculator", "open_app", {"app_name": "calculator"}),
                step(3, "Open Chrome", "open_app", {"app_name": "chrome"}),
            ],
        },
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


class CancellingExecutor:

    def __init__(self, orchestrator=None, cancel_on=None):
        self.calls = []
        self.orchestrator = orchestrator
        self.cancel_on = cancel_on

    def __call__(self, tool_name, arguments):
        arguments = dict(arguments or {})
        self.calls.append((tool_name, arguments))

        if (tool_name, arguments) == self.cancel_on:
            self.orchestrator.cancel_execution()

        return {
            "success": True,
            "result": {
                "tool": tool_name,
                **arguments
            }
        }


class FlakyExecutor:

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

        if arguments.get("app_name") == "calculator":
            count = self.calls.count(
                ("open_app", {"app_name": "calculator"})
            )
            if count == 1:
                return {
                    "success": False,
                    "error": "simulated flaky failure",
                }

        return {
            "success": True,
            "result": {
                "tool": tool_name,
                **arguments
            }
        }


class CountingCompleter:

    def __init__(self):
        self.calls = []

    def __call__(self, task_id):
        self.calls.append(task_id)
        complete_task(task_id)


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
        "I want to run a sequential plan": {
            "intent": "goal",
            "goal": "Run Sequential",
            "confidence": 0.95,
        },
        "I want to run a forward plan": {
            "intent": "goal",
            "goal": "Run Forward",
            "confidence": 0.95,
        },
        "I want to run an invalid-ref plan": {
            "intent": "goal",
            "goal": "Run Invalid Ref",
            "confidence": 0.95,
        },
        "I want to run a cycle plan": {
            "intent": "goal",
            "goal": "Run Cycle",
            "confidence": 0.95,
        },
        "I want to run a not-auto-dep plan": {
            "intent": "goal",
            "goal": "Run Not Auto Dep",
            "confidence": 0.95,
        },
        "I want to run a dep-fail plan": {
            "intent": "goal",
            "goal": "Run Dep Fail",
            "confidence": 0.95,
        },
        "I want to run a resume-cancel plan": {
            "intent": "goal",
            "goal": "Run Resume Cancel",
            "confidence": 0.95,
        },
        "I want to run a resume-fail plan": {
            "intent": "goal",
            "goal": "Run Resume Fail",
            "confidence": 0.95,
        },
        "I want to run a retry plan": {
            "intent": "goal",
            "goal": "Run Retry",
            "confidence": 0.95,
        },
    }


def build_fixture(executor=None, task_completer=None):
    orchestrator = Orchestrator(
        planner=ToolPlanner(build_plans()),
        classifier=RuleClassifier(build_rules()),
        executor=executor,
        task_completer=task_completer
    )

    zoey = StubZoey(orchestrator=orchestrator)

    return orchestrator, zoey


def approve_and_execute(zoey, message, command="execute the plan"):
    zoey.respond(message)
    zoey.respond("yes")
    return zoey.respond(command)


def main():
    print(
        "\nPHASE 9.7 TEST: MULTI-STEP DEPENDENCIES, RESUME "
        "AND RETRY (deterministic)\n"
    )
    print("=" * 60)

    try:

        print("\nTEST 1: DEPENDENCIES RUN IN DETERMINISTIC ORDER")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = approve_and_execute(
            zoey,
            "I want to run a sequential plan"
        )

        verify(
            "I executed the approved plan:" in response,
            "the sequential plan executes"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
                ("open_app", {"app_name": "chrome"}),
            ],
            "dependent steps run after their dependencies"
        )
        verify(
            "Review Sequential: no automated action" in response,
            "the tool-less step stays not_auto"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the run completes"
        )

        print("\nTEST 2: FORWARD DEPENDENCIES ARE DEFERRED")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = approve_and_execute(
            zoey,
            "I want to run a forward plan"
        )

        verify(
            "I executed the approved plan:" in response,
            "the forward-dependency plan executes"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "calculator"}),
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "chrome"}),
            ],
            "a step waiting on a later step runs once it "
            "satisfies"
        )

        print("\nTEST 3: INVALID DEPENDENCY BLOCKS A STEP")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = approve_and_execute(
            zoey,
            "I want to run an invalid-ref plan"
        )

        verify(
            "I executed the approved plan:" in response,
            "the rest of the plan still executes"
        )
        verify(
            "Open Calculator: blocked" in response,
            "the step with a missing dependency is blocked"
        )
        verify(
            "Open Notepad: done" in response,
            "the independent step ran"
        )
        verify(
            "Open Chrome: done" in response,
            "the other independent step ran"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "chrome"}),
            ],
            "the blocked step never reached the executor"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the run completes with a blocked step reported"
        )

        print("\nTEST 4: CIRCULAR DEPENDENCIES ARE DETECTED")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = approve_and_execute(
            zoey,
            "I want to run a cycle plan"
        )

        verify(
            "depend on steps that can't complete" in response,
            "the blocked run is reported honestly"
        )
        verify(
            "Open Notepad: blocked" in response,
            "the first cyclic step is blocked"
        )
        verify(
            "Open Calculator: blocked" in response,
            "the second cyclic step is blocked"
        )
        verify(
            executor.calls == [],
            "no tool ran for the cyclic steps"
        )
        verify(
            orchestrator.approved_plan["status"] == "blocked",
            "the run is marked blocked"
        )

        print("\nTEST 5: A NOT_AUTO DEPENDENCY IS SATISFIED")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = approve_and_execute(
            zoey,
            "I want to run a not-auto-dep plan"
        )

        verify(
            "I executed the approved plan:" in response,
            "the plan executes"
        )
        verify(
            "Review setup: no automated action" in response,
            "the informational step is not_auto"
        )
        verify(
            "Open Notepad: done" in response,
            "the step depending on not_auto runs"
        )
        verify(
            "Open Calculator: done" in response,
            "the second dependent step runs"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
            ],
            "dependents of the not_auto step ran"
        )

        print("\nTEST 6: A FAILED DEPENDENCY BLOCKS ITS DEPENDENTS")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = approve_and_execute(
            zoey,
            "I want to run a dep-fail plan"
        )

        verify(
            "I stopped the plan because a step failed:"
            in response,
            "the run stops on the failed step"
        )
        verify(
            "Open Banned App: FAILED" in response,
            "the failed step is reported"
        )
        verify(
            "Open Chrome: blocked" in response,
            "the dependent step is blocked"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "banned"}),
            ],
            "the blocked dependent never ran"
        )
        verify(
            orchestrator.approved_plan["status"] == "failed",
            "the run is marked failed"
        )

        print("\nTEST 7: RESUME AFTER CANCELLATION")

        delete_by_titles(ALL_TITLES)

        executor = CancellingExecutor(
            None,
            cancel_on=(
                "open_app",
                {"app_name": "calculator"}
            )
        )
        completer = CountingCompleter()
        orchestrator, zoey = build_fixture(
            executor=executor,
            task_completer=completer
        )
        executor.orchestrator = orchestrator

        zoey.respond("I want to run a resume-cancel plan")
        zoey.respond("yes")

        chrome_task_id = [
            row["id"]
            for row in task_rows_by_title("Open Chrome")
        ][-1]

        response = zoey.respond("execute the plan")

        verify(
            "I stopped the plan" in response,
            "the run is cancelled mid-way"
        )
        verify(
            orchestrator.approved_plan["status"] == "cancelled",
            "the run is marked cancelled"
        )

        response = zoey.respond("resume the plan")

        verify(
            "I resumed the plan:" in response,
            "resume is acknowledged"
        )
        verify(
            "Open Chrome: done" in response,
            "the cancelled step is re-attempted on resume"
        )
        verify(
            len(executor.calls) == 3,
            "completed steps were NOT re-executed on resume"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
                ("open_app", {"app_name": "chrome"}),
            ],
            "each executable step ran exactly once"
        )
        verify(
            len(completer.calls) == 3,
            "tasks were completed exactly once each"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the resumed run completes"
        )

        chrome_rows = task_rows_by_title("Open Chrome")
        verify(
            any(
                row["id"] == chrome_task_id
                and row["status"] == "completed"
                for row in chrome_rows
            ),
            "the resumed step's task is marked completed"
        )

        print("\nTEST 8: RESUME AFTER FAILURE DOES NOT RETRY")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        completer = CountingCompleter()
        orchestrator, zoey = build_fixture(
            executor=executor,
            task_completer=completer
        )

        zoey.respond("I want to run a resume-fail plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            orchestrator.approved_plan["status"] == "failed",
            "the run fails"
        )

        response = zoey.respond("resume the plan")

        verify(
            "I resumed the plan, but a step is still failed:"
            in response,
            "resume reports the still-failed step"
        )
        verify(
            "Open Banned App: FAILED" in response,
            "the failed step was not retried"
        )
        verify(
            "Open Chrome: done" in response,
            "the un-run step ran on resume"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "banned"}),
                ("open_app", {"app_name": "chrome"}),
            ],
            "no automatic retry of the failed step occurred"
        )
        verify(
            len(completer.calls) == 2,
            "no completed task was re-completed on resume"
        )

        print("\nTEST 9: EXPLICIT SINGLE-STEP RETRY")

        delete_by_titles(ALL_TITLES)

        executor = FlakyExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a retry plan")
        zoey.respond("yes")

        response = zoey.respond("execute the plan")

        verify(
            orchestrator.approved_plan["status"] == "failed",
            "the flaky step fails the first run"
        )
        verify(
            len(executor.calls) == 2,
            "only the first two steps ran"
        )

        response = zoey.respond("retry step 2")

        verify(
            "I retried step 2" in response,
            "the explicit retry is acknowledged"
        )
        verify(
            "I retried step 2 (Open Calculator): done."
            in response,
            "the retried step succeeds"
        )
        verify(
            executor.calls == [
                ("open_app", {"app_name": "notepad"}),
                ("open_app", {"app_name": "calculator"}),
                ("open_app", {"app_name": "calculator"}),
                ("open_app", {"app_name": "chrome"}),
            ],
            "retry re-executed only the retried step, then "
            "the remaining pending step ran"
        )
        verify(
            orchestrator.approved_plan["status"] == "completed",
            "the run completes after a successful retry"
        )

        print("\nTEST 10: RETRY AND RESUME GUARDS")

        delete_by_titles(ALL_TITLES)

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("retry step 1")

        verify(
            "There's no plan to retry." in response,
            "retry without a plan is refused"
        )

        zoey.respond("I want to run a sequential plan")
        zoey.respond("yes")
        zoey.respond("execute the plan")

        response = zoey.respond("retry step 1")

        verify(
            "Step 1 can't be retried." in response,
            "retry of a completed step is refused"
        )

        response = zoey.respond("retry step 99")

        verify(
            "There's no step 99 in the plan." in response,
            "retry of a missing step is refused"
        )

        response = zoey.respond("resume the plan")

        verify(
            "There's nothing to resume." in response,
            "resume of a completed run is refused"
        )

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a sequential plan")

        response = zoey.respond("resume the plan")

        verify(
            "There's no plan to resume." in response,
            "resume of an unapproved run is refused"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.7 TESTS PASSED")

    finally:

        delete_by_titles(ALL_TITLES)

        print("\nCLEANUP: removed all test-created task rows")


if __name__ == "__main__":
    main()
