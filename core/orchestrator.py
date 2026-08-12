from database.db import initialize_database
from core.planner import Planner
from core.intent import IntentClassifier
from core.agent_loop import AgentLoop
from core.step_validation import validate_step
from core import run_store
from tools.tasks import plan_to_tasks, complete_task


GOAL_COMMAND_PREFIXES = (
    "plan:",
    "make a plan to ",
    "make a plan for ",
    "create a plan to ",
    "create a plan for ",
    "help me plan to ",
    "help me plan ",
)

GOAL_COMMAND_EXACT = {
    "plan",
    "make a plan",
    "create a plan",
    "help me plan",
}

APPROVAL_RESPONSES = {
    "yes",
    "yeah",
    "approve",
    "approved",
    "do it",
    "add them",
    "add them all",
    "go ahead",
    "sure",
    "sounds good",
    "ok",
    "okay",
    "proceed",
}

REJECTION_RESPONSES = {
    "no",
    "nope",
    "cancel",
    "don't do it",
    "no thanks",
    "not now",
    "discard",
    "skip",
    "forget it",
}

EXECUTE_COMMANDS = {
    "execute the plan",
    "execute plan",
    "run the plan",
    "run plan",
    "start the plan",
    "start plan",
    "execute",
}

CANCEL_EXECUTION_COMMANDS = {
    "stop the plan",
    "stop the run",
    "stop execution",
    "halt the plan",
    "halt execution",
}

RE_RUN_COMMANDS = {
    "re-run the plan",
    "run the plan again",
    "restart the plan",
}

RESUME_COMMANDS = {
    "resume the plan",
    "resume execution",
    "resume the run",
    "resume",
}

RETRY_PREFIXES = (
    "retry step ",
    "retry ",
)

STATUS_COMMANDS = {
    "plan status",
    "execution status",
    "show plan status",
    "what's running?",
    "what's running",
}

# Phase 9.8: read-only run list and explicit discard.
SHOW_PLANS_COMMANDS = {
    "show my plans",
    "show plans",
    "list my plans",
    "list plans",
    "my plans",
    "plan list",
}

DISCARD_COMMANDS = {
    "discard the plan",
    "discard plan",
    "forget the plan",
    "clear the plan",
    "abandon the plan",
}

# Terminal states of a run. A terminal run refuses to execute
# again until an explicit re-run command resets it.
RUN_TERMINAL_STATES = (
    "completed",
    "failed",
    "cancelled",
    "blocked",
    "no_executable_steps",
)

# ----------------------------------------------------------
# RUN LIFECYCLE (PHASE 9.5/9.7/9.8 STATE MACHINE)
#
#   approved ──▶ running ──▶ completed
#      │            │   └──▶ failed
#      │            │   └──▶ cancelled
#      │            │   └──▶ no_executable_steps
#      │            │   └──▶ blocked  (dependencies can
#      │            │          never be satisfied)
#      │            └──▶ interrupted  (9.8: recovery marks
#      │                   an in-flight run interrupted
#      │                   after a restart)
#      └──▶ cancelled  (cancel requested before starting)
#
# Execution is guarded:
#   - only an approved plan may execute
#   - a running plan refuses re-entry
#   - a terminal plan refuses execution until an explicit
#     re-run command resets it to approved
#
# 9.7 additions:
#   - optional depends_on between steps; dependencies are
#     validated (missing references and cycles are detected)
#   - a step whose dependencies can never be satisfied is
#     marked blocked and never executes
#   - resume (9.7) re-attempts un-run steps after a failed
#     or cancelled run; completed/not_auto steps are never
#     re-executed and failed steps are never auto-retried
#   - `retry step <N>` explicitly re-executes one failed
#     step and then lets the remaining pending steps run
#
# 9.8 additions (persistence):
#   - the approved plan is persisted (plan_runs/plan_steps)
#     and every step mutation is written through to disk
#   - recovery marks an in-flight run interrupted; the run is
#     restored to memory but NEVER auto-executed - the user
#     must explicitly execute or resume it
#   - an interrupted run executes again on an explicit
#     execute/resume command; completed/not_auto steps are
#     not re-run, failed steps are not auto-retried, and
#     steps stuck in 'running' are re-attempted
#   - `discard the plan` deletes the persisted run; `show my
#     plans` lists runs read-only; no background thread
# ----------------------------------------------------------


class Orchestrator:

    def __init__(
        self,
        planner=None,
        classifier=None,
        executor=None,
        task_completer=None
    ):
        initialize_database()
        self.planner = (
            planner if planner is not None else Planner()
        )
        self.classifier = (
            classifier if classifier is not None
            else IntentClassifier()
        )
        self.executor = executor
        self._task_completer = (
            task_completer
            if task_completer is not None
            else complete_task
        )

        if self.executor is None:
            self._agent_loop = AgentLoop()
            self.executor = self._agent_loop.execute_one

        self._pending = None
        self._approved = None

        # Cooperative cancellation flag. Set by
        # cancel_execution() while a run is active and
        # consumed by the execution loop between steps.
        self._cancel_requested = False

        # Phase 9.8: recovery only restores an in-flight run
        # (marked interrupted). A terminal run is left in the
        # database as history; an approved-but-never-started
        # run is never auto-restored. Nothing executes here:
        # the user must explicitly execute a restored run.
        self._recover_persisted_run()

    # --------------------------------------------------
    # PHASE 9.3 PENDING PLAN / APPROVAL STATE
    # --------------------------------------------------

    @property
    def pending_plan(self):
        return self._pending

    @property
    def approved_plan(self):
        return self._approved

    def create_plan(self, goal):

        if not isinstance(goal, str) or not goal.strip():
            return {
                "type": "error",
                "error": "No goal provided.",
            }

        goal = goal.strip()

        try:

            plan = self.planner.create_plan(goal)

        except Exception as error:

            return {
                "type": "error",
                "error": str(error),
            }

        # A new goal supersedes any previously approved
        # plan. The new plan must be approved again before
        # it can be executed. The superseded run is removed
        # from the database so the latest persisted run is
        # always the current plan.
        if (
            self._approved is not None
            and self._approved.get("run_id") is not None
        ):
            run_store.delete_run(
                self._approved["run_id"]
            )

        self._approved = None
        self._cancel_requested = False

        self._pending = {
            "goal": goal,
            "plan": plan,
        }

        return {
            "type": "plan_pending",
            "goal": goal,
            "plan": plan,
        }

    def approve(
        self,
        check_duplicates: bool = True
    ):

        if not self._pending:
            return {
                "type": "error",
                "error": (
                    "There's no plan waiting for approval."
                ),
            }

        goal = self._pending["goal"]
        plan = self._pending["plan"]

        try:

            tasks = plan_to_tasks(
                plan,
                check_duplicates=check_duplicates
            )

        except Exception as error:

            self._pending = None

            return {
                "type": "error",
                "error": str(error),
            }

        self._pending = None
        self._cancel_requested = False

        # The approved plan is the ONLY execution source.
        # Execution never runs from a pending plan.
        self._approved = self._build_approved_record(
            goal,
            plan,
            tasks
        )

        # Phase 9.8: the run is persisted at approval. Every
        # step mutation is written through during execution.
        self._approved["run_id"] = run_store.create_run(
            self._approved
        )

        return {
            "type": "goal",
            "goal": goal,
            "plan": plan,
            "tasks": tasks,
        }

    def _normalize_arguments(self, arguments):

        # A tool step that omits its arguments must behave
        # exactly like one that passes an empty object.
        if arguments is None:
            return {}

        return arguments

    def _normalize_depends_on(self, depends_on):

        # depends_on is optional. It may be a single step
        # number or a list of step numbers. Invalid entries
        # are dropped; a step left with no dependencies is
        # fully backward-compatible with 9.4/9.5/9.6 plans.
        if depends_on is None:
            return []

        if isinstance(depends_on, bool):
            return []

        if isinstance(depends_on, int):
            return [depends_on]

        if isinstance(depends_on, list):
            return [
                item for item in depends_on
                if isinstance(item, int)
                and not isinstance(item, bool)
            ]

        return []

    def _build_approved_record(self, goal, plan, tasks):

        steps = plan.get("steps", [])

        step_records = []

        for index, step in enumerate(steps):

            # Defensive mapping: a step that has no backing
            # task is still recorded, just without a task_id.
            task = (
                tasks[index]
                if index < len(tasks) else None
            )

            step_records.append({
                "number": step.get("number"),
                "title": step.get("title"),
                "tool": step.get("tool"),
                "arguments": self._normalize_arguments(
                    step.get("arguments")
                ),
                "depends_on": self._normalize_depends_on(
                    step.get("depends_on")
                ),
                "task_id": (
                    task.get("id")
                    if task is not None else None
                ),
                "status": "pending",
                "result": None,
            })

        return {
            "goal": goal,
            "plan": plan,
            "tasks": tasks,
            "steps": step_records,
            "status": "approved",
        }

    def reject(self):

        if not self._pending:
            return {
                "type": "error",
                "error": (
                    "There's no plan waiting for approval."
                ),
            }

        pending = self._pending
        self._pending = None

        # A rejected plan never executes. Any previously
        # approved plan is also discarded so a stale approval
        # cannot resurrect an old execution.
        self._approved = None

        return {
            "type": "goal_rejected",
            "goal": pending["goal"],
            "plan": pending["plan"],
        }

    def _parse_approval(self, message):

        lower = message.lower()

        if lower in APPROVAL_RESPONSES:
            return "approve"

        if lower in REJECTION_RESPONSES:
            return "reject"

        return None

    # --------------------------------------------------
    # PHASE 9.4/9.5 APPROVED PLAN EXECUTION
    # --------------------------------------------------

    def _parse_execution(self, message):

        if message.lower() in EXECUTE_COMMANDS:
            return "execute"

        return None

    def _parse_cancel_execution(self, message):

        if message.lower() in CANCEL_EXECUTION_COMMANDS:
            return "cancel_execution"

        return None

    def _parse_rerun(self, message):

        if message.lower() in RE_RUN_COMMANDS:
            return "rerun"

        return None

    def _parse_resume(self, message):

        if message.lower() in RESUME_COMMANDS:
            return "resume"

        return None

    def _parse_retry(self, message):

        lower = message.lower()

        for prefix in RETRY_PREFIXES:

            if lower.startswith(prefix):

                token = lower[len(prefix):].strip()

                if token.isdigit():
                    return int(token)

                return None

        return None

    def _parse_status(self, message):

        if message.lower() in STATUS_COMMANDS:
            return "status"

        return None

    def _step_snapshots(self, record):

        return [
            {
                "number": step["number"],
                "title": step["title"],
                "tool": step.get("tool"),
                "task_id": step.get("task_id"),
                "depends_on": step.get("depends_on") or [],
                "status": step["status"],
                "result": step.get("result"),
            }
            for step in record["steps"]
        ]

    def _execution_result(
        self,
        result_type,
        record,
        warnings,
    ):

        return {
            "type": result_type,
            "goal": record["goal"],
            "plan": record["plan"],
            "steps": self._step_snapshots(record),
            "status": record["status"],
            "warnings": warnings,
        }

    # --------------------------------------------------
    # PHASE 9.8 PERSISTENCE
    # --------------------------------------------------

    def _persist_all(self, record):
        """Write-through: persist the run status and every
        step so a crash can only lose the current tool call,
        never already-completed work."""

        run_id = record.get("run_id")

        if run_id is None:
            return

        for step in record["steps"]:
            run_store.update_step(
                run_id,
                step["number"],
                step
            )

        run_store.update_run(run_id, record["status"])

    def _recover_persisted_run(self):
        """Restore state after a restart. Only an in-flight
        run (status 'running') is recovered and marked
        interrupted. Terminal runs stay in the database as
        history; an approved-but-never-started run is not
        auto-restored. Recovery restores STATE only and never
        grants execution: the user must explicitly execute."""

        record = run_store.load_latest_run()

        if record is None:
            return

        if record["status"] != "running":
            return

        record["status"] = "interrupted"

        run_store.update_run(
            record["run_id"],
            "interrupted"
        )

        self._approved = record

    def _run_restored(self, record):
        """Explicit execution of a recovered interrupted run.
        Completed and not_auto steps are never re-executed,
        failed steps are never auto-retried, and steps stuck
        in 'running' (the process died mid-step) are
        re-attempted because their completion was never
        confirmed."""

        for step in record["steps"]:

            if step["status"] in (
                "running",
                "cancelled",
                "blocked",
            ):
                step["status"] = "pending"
                step["result"] = None

        result, made_progress = self._run_plan()

        result["restored"] = True
        result["nothing_left"] = not made_progress

        return result

    def discard_run(self):
        """Explicitly discard the current plan (pending or
        approved) and remove its persisted run."""

        if (
            self._pending is None
            and self._approved is None
        ):
            return {
                "type": "error",
                "error": "There's no plan to discard.",
            }

        goal = None
        run_id = None

        if self._approved is not None:
            goal = self._approved.get("goal")
            run_id = self._approved.get("run_id")

        if goal is None and self._pending is not None:
            goal = self._pending.get("goal")

        self._pending = None
        self._approved = None
        self._cancel_requested = False

        if run_id is not None:
            run_store.delete_run(run_id)

        return {
            "type": "plan_discarded",
            "goal": goal,
            "saved_run": run_id is not None,
        }

    def plan_list(self):
        """Read-only listing of every persisted run."""

        return {
            "type": "plan_list",
            "runs": run_store.list_runs(),
        }

    def _parse_discard(self, message):

        if message.lower() in DISCARD_COMMANDS:
            return "discard"

        return None

    def _parse_list_plans(self, message):

        if message.lower() in SHOW_PLANS_COMMANDS:
            return "list_plans"

        return None

    # --------------------------------------------------
    # PHASE 9.7 DEPENDENCIES
    # --------------------------------------------------

    def _dependency_map(self, record):

        numbers = {
            step["number"]
            for step in record["steps"]
        }

        dep_map = {}

        for step in record["steps"]:

            deps = step.get("depends_on") or []

            dep_map[step["number"]] = {
                "deps": deps,
                "missing": [
                    dep for dep in deps
                    if dep not in numbers
                ],
            }

        return dep_map

    def _step_by_number(self, record, number):

        for step in record["steps"]:

            if step["number"] == number:
                return step

        return None

    def _can_reach(self, dep_map, start, target, seen):

        if start == target:
            return True

        if start in seen:
            return False

        seen.add(start)

        for dep in dep_map.get(start, {}).get(
            "deps",
            []
        ):
            if dep in dep_map:
                if self._can_reach(
                    dep_map,
                    dep,
                    target,
                    seen
                ):
                    return True

        return False

    def _in_dependency_cycle(self, dep_map, number):

        for dep in dep_map[number]["deps"]:

            if dep not in dep_map:
                continue

            if self._can_reach(
                dep_map,
                dep,
                number,
                set()
            ):
                return True

        return False

    def _pre_block_unrunnable(self, record, dep_map):

        # Steps whose dependencies can never be satisfied are
        # marked blocked before execution starts: references
        # to missing steps, and steps inside dependency
        # cycles.
        for step in record["steps"]:

            number = step["number"]

            if step["status"] != "pending":
                continue

            if dep_map[number]["missing"]:
                step["status"] = "blocked"
            elif self._in_dependency_cycle(
                dep_map,
                number
            ):
                step["status"] = "blocked"

    def _dependencies_satisfied(self, record, dep_map, step):

        for dep_number in dep_map[step["number"]]["deps"]:

            dep = self._step_by_number(
                record,
                dep_number
            )

            # A missing reference is never satisfied.
            if dep is None:
                return False

            # A dependency on an informational step counts
            # as satisfied: it needs no execution.
            if dep["status"] in (
                "completed",
                "not_auto",
            ):
                continue

            # Pending, running, failed, cancelled and
            # blocked dependencies are not satisfied.
            return False

        return True

    def _mark_dependents_blocked(self, record, dep_map, step):

        pending = [step["number"]]
        seen = set()

        while pending:

            dep_number = pending.pop()

            if dep_number in seen:
                continue

            seen.add(dep_number)

            for candidate in record["steps"]:

                if candidate["status"] in (
                    "completed",
                    "not_auto",
                    "blocked",
                ):
                    continue

                if dep_number in dep_map[
                    candidate["number"]
                ]["deps"]:
                    candidate["status"] = "blocked"
                    pending.append(
                        candidate["number"]
                    )

    def _finalize_run_status(self, record):

        statuses = {
            step["status"]
            for step in record["steps"]
        }

        if "failed" in statuses:
            record["status"] = "failed"
        elif "cancelled" in statuses:
            record["status"] = "cancelled"
        elif "completed" in statuses:
            record["status"] = "completed"
        elif "blocked" in statuses:
            record["status"] = "blocked"
        else:
            record["status"] = "no_executable_steps"

    def _run_plan(self):

        record = self._approved

        dep_map = self._dependency_map(record)

        self._pre_block_unrunnable(record, dep_map)

        record["status"] = "running"

        warnings = []
        made_progress = False

        while True:

            pass_progress = False

            for step in record["steps"]:

                # Completed and not_auto steps are never
                # re-executed. Failed, blocked and cancelled
                # steps are not part of a normal run.
                if step["status"] in (
                    "completed",
                    "not_auto",
                    "failed",
                    "blocked",
                    "cancelled",
                ):
                    continue

                # Cooperative cancellation: checked between
                # steps, never while a tool call is blocking.
                if self._cancel_requested:
                    self._cancel_requested = False
                    self._mark_remaining_cancelled(
                        record,
                        step
                    )
                    return self._execution_result(
                        "execution_cancelled",
                        record,
                        warnings,
                    ), True

                tool = step.get("tool")

                # A step without a tool action is
                # informational only. It is reported
                # honestly as not auto-executable and is
                # never treated as a success or a failure.
                if not tool:
                    step["status"] = "not_auto"
                    made_progress = True
                    pass_progress = True
                    self._persist_all(record)
                    continue

                # A step runs only when every dependency is
                # satisfied. Otherwise it is deferred and
                # reconsidered on the next pass.
                if not self._dependencies_satisfied(
                    record,
                    dep_map,
                    step
                ):
                    continue

                step["status"] = "running"

                # Write-through: an in-flight step stays
                # visible on disk so recovery can distinguish
                # it from never-started work.
                self._persist_all(record)

                # A step is validated before it is executed.
                # An invalid step never runs: it fails the
                # run with the validation error. Semantic
                # values (e.g. a banned app) are NOT
                # validated here and still fail at runtime
                # through the executor.
                validation = validate_step(step)

                if not validation["valid"]:

                    step["result"] = {
                        "success": False,
                        "error": validation["error"],
                    }
                    step["status"] = "failed"
                    record["status"] = "failed"
                    self._mark_dependents_blocked(
                        record,
                        dep_map,
                        step
                    )
                    made_progress = True
                    self._persist_all(record)
                    break

                arguments = validation["arguments"]

                try:

                    result = self.executor(
                        tool,
                        arguments
                    )

                except Exception as error:

                    result = {
                        "success": False,
                        "error": str(error)
                    }

                step["result"] = result

                if not result.get("success", False):

                    step["status"] = "failed"
                    record["status"] = "failed"
                    self._mark_dependents_blocked(
                        record,
                        dep_map,
                        step
                    )
                    made_progress = True
                    self._persist_all(record)
                    break

                step["status"] = "completed"
                made_progress = True
                pass_progress = True

                task_id = step.get("task_id")

                if task_id is not None:

                    # The tool ran successfully. If marking
                    # the backing task done fails, the step
                    # stays completed (the tool did run) but
                    # the failure is reported honestly
                    # instead of being swallowed.
                    try:
                        self._task_completer(task_id)
                    except Exception as error:
                        warnings.append({
                            "step_number": step.get(
                                "number"
                            ),
                            "task_id": task_id,
                            "error": str(error),
                        })

                self._persist_all(record)

            if record["status"] == "failed":
                break

            # A cancellation that arrived after the last
            # step has nothing left to cancel.
            if self._cancel_requested:
                self._cancel_requested = False
                break

            if not pass_progress:

                # Nothing could run this pass. Any step still
                # pending can never satisfy its dependencies,
                # so it is blocked and never executed.
                for step in record["steps"]:

                    if step["status"] == "pending":
                        step["status"] = "blocked"
                        made_progress = True

                self._persist_all(record)

                break

        # A stale cancellation request from a completed run
        # must not bleed into a future re-run.
        self._cancel_requested = False

        self._finalize_run_status(record)

        # Final write-through of the terminal run state.
        self._persist_all(record)

        return self._execution_result(
            "plan_executed",
            record,
            warnings,
        ), made_progress

    def execute_approved_plan(self):

        if not self._approved:
            return {
                "type": "error",
                "error": (
                    "There's no approved plan to execute."
                ),
            }

        record = self._approved

        # Re-entry protection: a running plan refuses a
        # second execution while the first is still active.
        if record["status"] == "running":
            return {
                "type": "error",
                "error": (
                    "The plan is already running."
                ),
            }

        # Phase 9.8: an interrupted run (recovered after a
        # restart) executes again on an EXPLICIT execute
        # command. State is restored, not authorization:
        # nothing runs until this command is given.
        if record["status"] == "interrupted":
            return self._run_restored(record)

        # A finished plan never executes again without an
        # explicit re-run command.
        if record["status"] in RUN_TERMINAL_STATES:
            return {
                "type": "error",
                "error": (
                    "This plan has already finished. "
                    "Say 're-run the plan' to execute "
                    "it again."
                ),
            }

        result, _ = self._run_plan()

        return result

    def resume_execution(self):

        if not self._approved:
            return {
                "type": "error",
                "error": (
                    "There's no plan to resume."
                ),
            }

        record = self._approved

        if record["status"] == "running":
            return {
                "type": "error",
                "error": (
                    "The plan is currently running."
                ),
            }

        # Resume is for a failed, cancelled or interrupted
        # run. An interrupted run is treated like a cancelled
        # one: un-run work is re-attempted on the explicit
        # resume command.
        if record["status"] not in (
            "failed",
            "cancelled",
            "interrupted",
        ):
            return {
                "type": "error",
                "error": (
                    "There's nothing to resume."
                ),
            }

        # Cancelled and blocked steps go back to pending so
        # they can be re-attempted. Steps stuck in 'running'
        # (from a recovered interrupted run) are re-attempted
        # too. Completed and not_auto steps are never
        # re-executed, and a failed step is never auto-retried
        # by resume (use 'retry step N').
        for step in record["steps"]:

            if step["status"] in (
                "cancelled",
                "blocked",
                "running",
            ):
                step["status"] = "pending"
                step["result"] = None

        result, made_progress = self._run_plan()

        result["resumed"] = True
        result["nothing_left"] = not made_progress

        return result

    def retry_step(self, number):

        if not self._approved:
            return {
                "type": "error",
                "error": (
                    "There's no plan to retry."
                ),
            }

        record = self._approved

        if record["status"] == "running":
            return {
                "type": "error",
                "error": (
                    "The plan is currently running."
                ),
            }

        target = self._step_by_number(record, number)

        if target is None:
            return {
                "type": "error",
                "error": (
                    f"There's no step {number} in the plan."
                ),
            }

        if target["status"] not in (
            "failed",
            "cancelled",
            "blocked",
        ):
            return {
                "type": "error",
                "error": (
                    f"Step {number} can't be retried."
                ),
            }

        # Reset ONLY this step. Every other step keeps its
        # state: completed/not_auto steps are never
        # re-executed and other failed steps are never
        # auto-retried.
        target["status"] = "pending"
        target["result"] = None

        self._persist_all(record)

        result, _ = self._run_plan()

        result["type"] = "step_retried"
        result["retried_number"] = number

        return result

    def _mark_remaining_cancelled(self, record, from_step):

        started = False

        for step in record["steps"]:

            if step is from_step or started:
                started = True

                # Completed and not_auto steps keep their
                # state. Only un-run steps are cancelled.
                if step["status"] in (
                    "pending",
                    "running",
                    "blocked",
                ):
                    step["status"] = "cancelled"

        record["status"] = "cancelled"

        # Write-through the cancelled state before returning
        # (the cancel path returns before finalization).
        self._persist_all(record)

    def cancel_execution(self):

        if not self._approved:
            return {
                "type": "error",
                "error": (
                    "There's no plan to stop."
                ),
            }

        record = self._approved

        if record["status"] in RUN_TERMINAL_STATES:
            return {
                "type": "error",
                "error": (
                    "The plan has already finished; "
                    "there's nothing to stop."
                ),
            }

        if record["status"] == "running":

            # Cooperative cancel: the running loop picks the
            # flag up between steps. The blocking executor
            # call is never interrupted.
            self._cancel_requested = True

            return {
                "type": "execution_cancelled",
                "status": "cancelling",
                "goal": record["goal"],
                "steps": [],
                "warnings": [],
            }

        # Approved but not yet started: cancellation happens
        # immediately and no tool ever runs.
        self._cancel_requested = False

        for step in record["steps"]:
            step["status"] = "cancelled"

        record["status"] = "cancelled"

        self._persist_all(record)

        return {
            "type": "execution_cancelled",
            "status": "cancelled",
            "goal": record["goal"],
            "plan": record["plan"],
            "steps": self._step_snapshots(record),
            "warnings": [],
        }

    def reset_execution(self):

        if not self._approved:
            return {
                "type": "error",
                "error": (
                    "There's no plan to re-run."
                ),
            }

        record = self._approved

        if record["status"] == "running":
            return {
                "type": "error",
                "error": (
                    "The plan is currently running; "
                    "stop it first."
                ),
            }

        self._cancel_requested = False

        record["status"] = "approved"

        for step in record["steps"]:
            step["status"] = "pending"
            step["result"] = None

        self._persist_all(record)

        return {
            "type": "execution_reset",
            "goal": record["goal"],
            "plan": record["plan"],
            "status": "approved",
            "steps": self._step_snapshots(record),
        }

    def rerun_execution(self):

        reset = self.reset_execution()

        if reset.get("type") == "error":
            return reset

        # An explicit re-run command is an explicit
        # execution request for an already-approved plan.
        return self.execute_approved_plan()

    def execution_status(self):

        if self._approved is not None:

            record = self._approved

            return {
                "type": "execution_status",
                "status": record["status"],
                "goal": record["goal"],
                "plan": record["plan"],
                "steps": self._step_snapshots(record),
            }

        if self._pending is not None:

            return {
                "type": "execution_status",
                "status": "pending_approval",
                "goal": self._pending["goal"],
                "plan": self._pending["plan"],
                "steps": [],
            }

        return {
            "type": "execution_status",
            "status": "idle",
            "goal": None,
            "plan": None,
            "steps": [],
        }

    # --------------------------------------------------
    # PHASE 9.1 ROUTER
    # --------------------------------------------------

    def handle(self, message):

        if not isinstance(message, str) or not message.strip():
            return {
                "type": "error",
                "error": "No input provided.",
            }

        message = message.strip()

        decision = self._parse_approval(message)

        if decision is not None and self._pending is not None:

            if decision == "approve":
                return self.approve()

            return self.reject()

        # Execution is a distinct, explicit user command. It
        # only runs when a plan has already been approved and
        # never before approval.
        if self._parse_execution(message) == "execute":
            return self.execute_approved_plan()

        # Cancellation and re-run are explicit lifecycle
        # commands and never run on their own.
        if self._parse_cancel_execution(message) == (
            "cancel_execution"
        ):
            return self.cancel_execution()

        if self._parse_rerun(message) == "rerun":
            return self.rerun_execution()

        if self._parse_resume(message) == "resume":
            return self.resume_execution()

        retry_number = self._parse_retry(message)

        if retry_number is not None:
            return self.retry_step(retry_number)

        if self._parse_status(message) == "status":
            return self.execution_status()

        # Phase 9.8: explicit discard and read-only plan
        # listing are lifecycle commands, never auto-triggered.
        if self._parse_discard(message) == "discard":
            return self.discard_run()

        if self._parse_list_plans(message) == "list_plans":
            return self.plan_list()

        intent = self.detect_intent(message)

        if intent.get("type") == "goal":
            return self.create_plan(intent["goal"])

        return intent

    # --------------------------------------------------
    # PHASE 9.2 NATURAL INTENT DETECTION
    # --------------------------------------------------

    def detect_intent(self, message):

        if not isinstance(message, str) or not message.strip():
            return {
                "type": "error",
                "error": "No input provided.",
            }

        message = message.strip()

        goal = self._extract_goal(message)

        if goal is not None:

            if not goal:
                return {
                    "type": "error",
                    "error": "What goal should I plan for?",
                }

            return {
                "type": "goal",
                "goal": goal,
                "confidence": 1.0,
                "source": "command",
            }

        classification = self.classifier.classify(message)

        intent = classification.get(
            "intent",
            "conversation"
        )

        threshold = getattr(
            self.classifier,
            "threshold",
            0.7
        )

        if (
            intent == "goal"
            and classification.get("goal")
            and classification.get(
                "confidence",
                0.0
            ) >= threshold
        ):
            return {
                "type": "goal",
                "goal": classification["goal"],
                "confidence": classification[
                    "confidence"
                ],
                "source": "classifier",
            }

        return {
            "type": "conversation",
            "message": message,
            "intent": intent,
            "confidence": classification.get(
                "confidence",
                0.0
            ),
        }

    def _extract_goal(self, message):

        lower = message.lower()

        if lower in GOAL_COMMAND_EXACT:
            return ""

        for prefix in GOAL_COMMAND_PREFIXES:

            if lower.startswith(prefix):
                return message[len(prefix):].strip()

        return None
