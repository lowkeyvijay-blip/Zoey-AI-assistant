from core import run_store
from core.run_store import (
    create_run,
    update_run,
    update_step,
    load_run,
    load_latest_run,
    list_runs,
    mark_interrupted,
    delete_run,
    delete_all_runs,
)


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def build_record(status="approved"):
    return {
        "goal": "Open the tools",
        "plan": {
            "goal": "Open the tools",
            "steps": [
                {
                    "number": 1,
                    "title": "Open Notepad",
                    "description": "Launch Notepad",
                },
                {
                    "number": 2,
                    "title": "Open Calculator",
                    "tool": "open_app",
                    "arguments": {"app_name": "calculator"},
                    "depends_on": [1],
                },
            ],
        },
        "steps": [
            {
                "number": 1,
                "title": "Open Notepad",
                "tool": None,
                "arguments": {},
                "depends_on": [],
                "task_id": 10,
                "status": "pending",
                "result": None,
            },
            {
                "number": 2,
                "title": "Open Calculator",
                "tool": "open_app",
                "arguments": {"app_name": "calculator"},
                "depends_on": [1],
                "task_id": 11,
                "status": "pending",
                "result": None,
            },
        ],
        "status": status,
    }


def main():
    print(
        "\nPHASE 9.8 TEST: RUN STORE (persistence layer)\n"
    )
    print("=" * 60)

    try:

        delete_all_runs()

        print("\nTEST 1: CREATE AND LOAD A RUN")

        run_id = create_run(build_record())

        verify(
            isinstance(run_id, int) and run_id > 0,
            "create_run returns a positive run id"
        )

        loaded = load_run(run_id)

        verify(
            loaded is not None,
            "load_run finds the created run"
        )
        verify(
            loaded["goal"] == "Open the tools",
            "goal round-trips through JSON"
        )
        verify(
            loaded["status"] == "approved",
            "run status is stored"
        )
        verify(
            len(loaded["steps"]) == 2,
            "both steps are stored"
        )
        verify(
            loaded["steps"][1]["tool"] == "open_app",
            "step tool round-trips"
        )
        verify(
            loaded["steps"][1]["depends_on"] == [1],
            "step depends_on round-trips"
        )
        verify(
            loaded["steps"][1]["arguments"]
            == {"app_name": "calculator"},
            "step arguments round-trip"
        )
        verify(
            loaded["steps"][1]["task_id"] == 11,
            "step task_id round-trips"
        )

        print("\nTEST 2: UPDATE RUN AND STEP")

        update_run(run_id, "running")

        verify(
            load_run(run_id)["status"] == "running",
            "update_run changes the run status"
        )

        update_step(
            run_id,
            1,
            {
                "number": 1,
                "title": "Open Notepad",
                "tool": None,
                "arguments": {},
                "depends_on": [],
                "task_id": 10,
                "status": "completed",
                "result": {"success": True},
            }
        )

        loaded = load_run(run_id)

        verify(
            loaded["steps"][0]["status"] == "completed",
            "update_step changes the step status"
        )
        verify(
            loaded["steps"][0]["result"]
            == {"success": True},
            "step result round-trips"
        )
        verify(
            loaded["steps"][1]["status"] == "pending",
            "the untouched step is unchanged"
        )

        print("\nTEST 3: LATEST RUN AND LISTING")

        second_id = create_run(
            build_record(status="failed")
        )

        latest = load_latest_run()

        verify(
            latest["run_id"] == second_id,
            "load_latest_run returns the newest run"
        )
        verify(
            latest["status"] == "failed",
            "the newest run keeps its own status"
        )

        runs = list_runs()

        verify(
            len(runs) == 2,
            "list_runs returns every persisted run"
        )
        verify(
            {run["run_id"] for run in runs}
            == {run_id, second_id},
            "both run ids are listed"
        )
        verify(
            runs[0]["run_id"] == second_id,
            "list_runs is newest-first"
        )
        verify(
            runs[0]["goal"] == "Open the tools",
            "listing includes the goal"
        )
        verify(
            runs[0]["step_count"] == 2,
            "listing includes the step count"
        )

        print("\nTEST 4: MARK INTERRUPTED AND DELETE")

        mark_interrupted(run_id)

        verify(
            load_run(run_id)["status"] == "interrupted",
            "mark_interrupted sets the status"
        )

        delete_run(run_id)

        verify(
            load_run(run_id) is None,
            "delete_run removes the run"
        )

        remaining = list_runs()

        verify(
            len(remaining) == 1
            and remaining[0]["run_id"] == second_id,
            "deleting one run leaves the other"
        )

        verify(
            load_run(run_id) is None,
            "deleting a run also removes its steps"
        )

        print("\nTEST 5: CREATE WITH A PERSISTED RESULT")

        record = build_record(status="completed")
        record["steps"][0]["status"] = "completed"
        record["steps"][0]["result"] = {
            "success": True,
            "result": {"app_name": "notepad"},
        }

        third_id = create_run(record)

        loaded = load_run(third_id)

        verify(
            loaded["status"] == "completed",
            "a terminal run round-trips"
        )
        verify(
            loaded["steps"][0]["result"]["result"]
            == {"app_name": "notepad"},
            "nested result dict round-trips"
        )

        print("\n" + "=" * 60)
        print("PHASE 9.8 RUN STORE TESTS PASSED")

    finally:

        delete_all_runs()

        print("\nCLEANUP: removed all test-created runs")


if __name__ == "__main__":
    main()
