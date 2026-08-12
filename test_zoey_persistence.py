from core.orchestrator import Orchestrator
from core.planner import Planner
from core.zoey import Zoey
from core import run_store
from database.db import get_connection
from tools.tasks import complete_task


PLAN_TITLES = [
    "Open Notepad",
    "Open Calculator",
    "Open Chrome",
]

ALL_TITLES = sorted(set(PLAN_TITLES))


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
        "Run Persist": {
            "goal": "Run Persist",
            "steps": [
                step(1, "Open Notepad", "open_app",
                     {"app_name": "notepad"}),
                step(2, "Open Calculator", "open_app",
                     {"app_name": "calculator"}),
                step(3, "Open Chrome", "open_app",
                     {"app_name": "chrome"}),
            ],
        },
        "Run Persist Fail": {
            "goal": "Run Persist Fail",
            "steps": [
                step(1, "Open Notepad", "open_app",
                     {"app_name": "notepad"}),
                step(2, "Open Banned App", "open_app",
                     {"app_name": "banned"}),
                step(3, "Open Chrome", "open_app",
                     {"app_name": "chrome"}),
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
        "I want to run a persist plan": {
            "intent": "goal",
            "goal": "Run Persist",
            "confidence": 0.95,
        },
        "I want to run a persist-fail plan": {
            "intent": "goal",
            "goal": "Run Persist Fail",
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


def approve_and_execute(zoey, message):
    zoey.respond(message)
    zoey.respond("yes")
    return zoey.respond("execute the plan")


def main():
    print(
        "\nPHASE 9.8 TEST: PERSISTENT RUN STATE "
        "(deterministic)\n"
    )
    print("=" * 60)

    try:

        delete_all_runs_and_tasks()

        print("\nTEST 1: APPROVAL PERSISTS A RUN")

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")

        run_id = orchestrator.approved_plan["run_id"]

        verify(
            isinstance(run_id, int) and run_id > 0,
            "approval creates a persisted run"
        )

        runs = run_store.list_runs()

        verify(
            any(run["run_id"] == run_id for run in runs),
            "the run is listed after approval"
        )
        verify(
            run_store.load_run(run_id)["status"] == "approved",
            "the run is stored as approved"
        )
        verify(
            len(run_store.load_run(run_id)["steps"]) == 3,
            "the run's steps are persisted at approval"
        )

        print("\nTEST 2: EXECUTION WRITES THROUGH TERMINAL STATE")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")
        run_id = orchestrator.approved_plan["run_id"]

        zoey.respond("execute the plan")

        loaded = run_store.load_run(run_id)

        verify(
            loaded["status"] == "completed",
            "the run status is written through"
        )
        verify(
            [step["status"] for step in loaded["steps"]]
            == ["completed", "completed", "completed"],
            "every step status is written through"
        )
        verify(
            loaded["steps"][0]["result"]["success"] is True,
            "step results are written through"
        )

        print("\nTEST 3: COOPERATIVE CANCEL WRITES THROUGH")

        delete_all_runs_and_tasks()

        executor = CancellingExecutor(
            None,
            cancel_on=(
                "open_app",
                {"app_name": "calculator"}
            )
        )
        orchestrator, zoey = build_fixture(executor=executor)
        executor.orchestrator = orchestrator

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")
        run_id = orchestrator.approved_plan["run_id"]

        zoey.respond("execute the plan")

        loaded = run_store.load_run(run_id)

        verify(
            loaded["status"] == "cancelled",
            "the cancelled run is persisted as cancelled"
        )
        verify(
            [step["status"] for step in loaded["steps"]]
            == ["completed", "completed", "cancelled"],
            "partial progress is persisted per step"
        )

        print("\nTEST 4: RESTART MARKS AN IN-FLIGHT RUN "
              "INTERRUPTED WITHOUT EXECUTING")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist-fail plan")
        zoey.respond("yes")
        run_id = orchestrator.approved_plan["run_id"]

        zoey.respond("execute the plan")

        verify(
            run_store.load_run(run_id)["status"] == "failed",
            "the run failed before the simulated crash"
        )

        # Simulate a process crash mid-run: the persisted
        # run is still marked in-flight.
        run_store.update_run(run_id, "running")

        new_executor = FakeExecutor()
        new_orchestrator = Orchestrator(
            planner=ToolPlanner(build_plans()),
            classifier=RuleClassifier(build_rules()),
            executor=new_executor
        )

        verify(
            new_orchestrator.approved_plan is not None,
            "the in-flight run is recovered on restart"
        )
        verify(
            new_orchestrator.approved_plan["status"]
            == "interrupted",
            "recovery marks the run interrupted"
        )
        verify(
            new_orchestrator.approved_plan["run_id"] == run_id,
            "the same run id is recovered"
        )
        verify(
            new_executor.calls == [],
            "recovery never executes anything"
        )

        recovered_steps = new_orchestrator.approved_plan["steps"]

        verify(
            [step["status"] for step in recovered_steps]
            == ["completed", "failed", "pending"],
            "recovery preserves per-step state"
        )
        verify(
            run_store.load_run(run_id)["status"]
            == "interrupted",
            "the interrupted status is persisted"
        )

        print("\nTEST 5: EXPLICIT EXECUTE CONTINUES AN "
              "INTERRUPTED RUN")

        new_completer = CountingCompleter()
        new_orchestrator._task_completer = new_completer
        new_zoey = StubZoey(orchestrator=new_orchestrator)

        chrome_task_id = [
            row["id"]
            for row in task_rows_by_title("Open Chrome")
        ][-1]

        response = new_zoey.respond("execute the plan")

        verify(
            "I continued the interrupted plan" in response,
            "explicit execute acknowledges the restore"
        )
        verify(
            "Open Chrome: done" in response,
            "the pending step ran"
        )
        verify(
            new_executor.calls == [
                ("open_app", {"app_name": "chrome"}),
            ],
            "completed work was NOT re-executed"
        )
        verify(
            "Open Banned App: FAILED" in response,
            "the failed step was not auto-retried"
        )
        verify(
            new_completer.calls == [chrome_task_id],
            "only the continued step's task was completed"
        )
        verify(
            new_orchestrator.approved_plan["status"]
            == "failed",
            "the run finishes with the failed step reported"
        )

        print("\nTEST 6: RESUME ALSO WORKS ON AN "
              "INTERRUPTED RUN")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist-fail plan")
        zoey.respond("yes")
        run_id = orchestrator.approved_plan["run_id"]
        zoey.respond("execute the plan")

        run_store.update_run(run_id, "running")

        new_executor = FakeExecutor()
        new_orchestrator = Orchestrator(
            planner=ToolPlanner(build_plans()),
            classifier=RuleClassifier(build_rules()),
            executor=new_executor
        )
        new_zoey = StubZoey(orchestrator=new_orchestrator)

        response = new_zoey.respond("resume the plan")

        verify(
            "I resumed the plan" in response,
            "resume is accepted for an interrupted run"
        )
        verify(
            "Open Chrome: done" in response,
            "the pending step ran on resume"
        )
        verify(
            new_executor.calls == [
                ("open_app", {"app_name": "chrome"}),
            ],
            "resume did not re-run completed work"
        )

        print("\nTEST 7: SHOW MY PLANS LISTS RUNS READ-ONLY")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        response = zoey.respond("show my plans")

        verify(
            "There are no saved plans." in response,
            "an empty list is reported honestly"
        )

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")
        run_id = orchestrator.approved_plan["run_id"]

        response = zoey.respond("show my plans")

        verify(
            "Saved plans:" in response,
            "plans are listed"
        )
        verify(
            f"Run {run_id}" in response,
            "the listing includes the run id"
        )
        verify(
            "Run Persist" in response,
            "the listing includes the goal"
        )
        verify(
            "approved" in response,
            "the listing includes the status"
        )

        zoey.respond("execute the plan")

        response = zoey.respond("show my plans")

        verify(
            "completed" in response,
            "the terminal status is listed after execution"
        )

        print("\nTEST 8: DISCARD THE PLAN")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")
        run_id = orchestrator.approved_plan["run_id"]
        zoey.respond("execute the plan")

        response = zoey.respond("discard the plan")

        verify(
            "I discarded the plan" in response,
            "discard is acknowledged"
        )
        verify(
            run_store.load_run(run_id) is None,
            "the persisted run is deleted"
        )
        verify(
            orchestrator.approved_plan is None,
            "the in-memory plan is cleared"
        )

        response = zoey.respond("execute the plan")

        verify(
            "There's no approved plan to execute." in response,
            "execution is refused after discard"
        )

        print("\nTEST 9: DISCARD OF A PENDING PLAN")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist plan")

        response = zoey.respond("discard the plan")

        verify(
            "cleared the pending plan" in response,
            "a pending plan is discarded"
        )

        response = zoey.respond("yes")

        verify(
            orchestrator.approved_plan is None,
            "a stale approval cannot resurrect the discarded "
            "plan"
        )
        verify(
            "I've saved these as tasks:" not in response,
            "no approval response is produced"
        )

        print("\nTEST 10: A TERMINAL RUN IS NOT AUTO-RESTORED")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")
        zoey.respond("execute the plan")

        new_orchestrator = Orchestrator(
            planner=ToolPlanner(build_plans()),
            classifier=RuleClassifier(build_rules()),
            executor=FakeExecutor()
        )

        verify(
            new_orchestrator.approved_plan is None,
            "a completed run is not restored to memory"
        )
        verify(
            new_orchestrator.execution_status()["status"]
            == "idle",
            "a fresh orchestrator reports idle"
        )
        verify(
            len(run_store.list_runs()) == 1,
            "the completed run stays in the database as "
            "history"
        )

        print("\nTEST 11: AN APPROVED-NEVER-EXECUTED RUN IS "
              "NOT AUTO-RESTORED")

        delete_all_runs_and_tasks()

        executor = FakeExecutor()
        orchestrator, zoey = build_fixture(executor=executor)

        zoey.respond("I want to run a persist plan")
        zoey.respond("yes")

        new_orchestrator = Orchestrator(
            planner=ToolPlanner(build_plans()),
            classifier=RuleClassifier(build_rules()),
            executor=FakeExecutor()
        )

        verify(
            new_orchestrator.approved_plan is None,
            "an approved-but-unstarted run is not "
            "auto-restored"
        )

        response = StubZoey(
            orchestrator=new_orchestrator
        ).respond("show my plans")

        verify(
            "Run Persist" in response
            and "approved" in response,
            "it remains queryable through show my plans"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.8 PERSISTENCE TESTS PASSED")

    finally:

        delete_all_runs_and_tasks()

        print("\nCLEANUP: removed all test-created runs/tasks")


def delete_all_runs_and_tasks():
    run_store.delete_all_runs()
    delete_by_titles(ALL_TITLES)


if __name__ == "__main__":
    main()
