"""Phase 10.9 API tests: frontend <-> backend integration layer.

These tests use a fake Zoey so no local LLM (Ollama) is required. The
read-only resource endpoints exercise the real Phase 10 tool functions.

Run with:  python -m pytest test_api.py -q   (or: python test_api.py)
"""

import threading
import time

from fastapi.testclient import TestClient

from api.server import create_app

TEST_PLAN = {
    "goal": "Test goal",
    "steps": [
        {
            "number": 1,
            "title": "Step one",
            "tool": "list_tasks",
            "arguments": {},
            "depends_on": [],
        }
    ],
}

TEST_STEP_SNAPSHOT = {
    "number": 1,
    "title": "Step one",
    "tool": "list_tasks",
    "task_id": None,
    "depends_on": [],
    "status": "pending",
    "result": None,
}


class FakeOrchestrator:
    """Minimal double mirroring the real Orchestrator's API surface that
    the server touches."""

    def __init__(self):
        self.pending = False
        self.approved_plan = None
        self.status = "idle"
        self.steps = []

    def approve(self):
        if not self.pending:
            return {
                "type": "error",
                "error": "There's no plan waiting for approval.",
            }

        self.pending = False
        self.approved_plan = {
            "goal": "Test goal",
            "plan": TEST_PLAN,
            "status": "approved",
            "steps": [dict(TEST_STEP_SNAPSHOT)],
            "run_id": 1,
        }
        self.status = "approved"

        return {
            "type": "goal",
            "goal": "Test goal",
            "plan": TEST_PLAN,
            "tasks": [{"id": 1, "title": "Step one"}],
        }

    def reject(self):
        if not self.pending:
            return {
                "type": "error",
                "error": "There's no plan waiting for approval.",
            }

        self.pending = False
        return {
            "type": "goal_rejected",
            "goal": "Test goal",
            "plan": TEST_PLAN,
        }

    def execute_approved_plan(self):
        if self.approved_plan is None:
            return {
                "type": "error",
                "error": "There's no approved plan to execute.",
            }

        self.approved_plan["status"] = "running"
        self.status = "running"
        self.steps = [dict(TEST_STEP_SNAPSHOT, status="running")]
        time.sleep(0.05)
        self.steps = [dict(TEST_STEP_SNAPSHOT, status="completed")]
        self.approved_plan["status"] = "completed"
        self.status = "completed"

        return {
            "type": "plan_executed",
            "status": "completed",
            "goal": "Test goal",
            "plan": TEST_PLAN,
            "steps": self.steps,
            "warnings": [],
        }

    def cancel_execution(self):
        if self.approved_plan is None:
            return {
                "type": "error",
                "error": "There's no plan to stop.",
            }

        return {
            "type": "execution_cancelled",
            "status": "cancelled",
            "goal": "Test goal",
            "steps": [],
            "warnings": [],
        }

    def execution_status(self):
        if self.approved_plan is not None:
            return {
                "type": "execution_status",
                "status": self.approved_plan["status"],
                "goal": "Test goal",
                "plan": TEST_PLAN,
                "steps": self.steps,
            }

        return {
            "type": "execution_status",
            "status": "idle",
            "goal": None,
            "plan": None,
            "steps": [],
        }

    def plan_list(self):
        return {"type": "plan_list", "runs": []}


class FakeZoey:
    def __init__(self):
        self.orchestrator = FakeOrchestrator()

    def respond_structured(self, message):
        lower = message.lower()

        if lower in {
            "make a plan to test",
            "plan: test goal",
        }:
            self.orchestrator.pending = True
            return {
                "type": "plan_pending",
                "goal": "Test goal",
                "plan": TEST_PLAN,
            }

        if lower == "yes":
            return self.orchestrator.approve()

        if lower == "no":
            return self.orchestrator.reject()

        return {
            "type": "text",
            "content": f"Fake Zoey heard: {message}",
        }

    def format_result(self, result):
        if result.get("type") == "plan_pending":
            return "PLAN: Test goal\n1. Step one"
        if result.get("type") == "goal":
            return "Approved — 1 task saved."
        if result.get("type") == "goal_rejected":
            return "OK, I won't add those tasks."
        if result.get("type") == "text":
            return result.get("content", "")
        return result.get("content", "")


def _wait_for_terminal(client, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()["data"]
        if data["status"] in (
            "completed",
            "failed",
            "cancelled",
            "blocked",
            "no_executable_steps",
        ):
            return data
        time.sleep(0.02)
    raise AssertionError("Execution did not reach a terminal state.")


def _fresh_client():
    return TestClient(create_app(FakeZoey()))


def test_health():
    client = _fresh_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_chat_conversation_fallback():
    client = _fresh_client()
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert message["role"] == "assistant"
    assert message["type"] == "text"
    assert message["content"] == "Fake Zoey heard: hello"


def test_chat_creates_pending_plan():
    client = _fresh_client()
    response = client.post(
        "/api/chat",
        json={"message": "make a plan to test"},
    )
    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert message["type"] == "plan_pending"
    assert message["data"]["goal"] == "Test goal"
    plan = message["data"]["plan"]
    assert plan["steps"][0]["tool"] == "list_tasks"
    assert message["content"].startswith("PLAN:")


def test_chat_rejects_empty_message():
    client = _fresh_client()
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_approve_requires_pending_plan():
    client = _fresh_client()
    response = client.post("/api/plans/approve")
    assert response.status_code == 400
    assert "no plan waiting" in response.json()["detail"]


def test_approve_creates_approved_plan():
    client = _fresh_client()
    client.post("/api/chat", json={"message": "make a plan to test"})

    response = client.post("/api/plans/approve")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["type"] == "goal"
    assert len(data["tasks"]) == 1

    # Approving must never start execution: the plan is approved but
    # execution has not begun.
    status = client.get("/api/status").json()["data"]
    assert status["status"] == "approved"


def test_approve_does_not_execute():
    client = _fresh_client()
    client.post("/api/chat", json={"message": "make a plan to test"})
    client.post("/api/plans/approve")

    status = client.get("/api/status").json()["data"]
    assert status["status"] == "approved"
    assert all(
        step["status"] == "pending"
        for step in status["steps"]
    )


def test_reject_discards_pending_plan():
    client = _fresh_client()
    client.post("/api/chat", json={"message": "make a plan to test"})

    response = client.post("/api/plans/reject")
    assert response.status_code == 200
    assert response.json()["data"]["type"] == "goal_rejected"

    # A rejected plan never executes.
    response = client.post("/api/execution/execute")
    assert response.status_code == 400
    assert "no approved plan" in response.json()["detail"]


def test_reject_requires_pending_plan():
    client = _fresh_client()
    response = client.post("/api/plans/reject")
    assert response.status_code == 400


def test_execute_requires_approved_plan():
    client = _fresh_client()
    response = client.post("/api/execution/execute")
    assert response.status_code == 400
    assert "no approved plan" in response.json()["detail"]


def test_execute_runs_in_background_and_terminates():
    client = _fresh_client()
    client.post("/api/chat", json={"message": "make a plan to test"})
    client.post("/api/plans/approve")

    response = client.post("/api/execution/execute")
    assert response.status_code == 200
    assert response.json()["data"]["type"] == "accepted"

    terminal = _wait_for_terminal(client)
    assert terminal["status"] == "completed"
    assert terminal["steps"][0]["status"] == "completed"


def test_cancel_running_execution():
    client = _fresh_client()
    client.post("/api/chat", json={"message": "make a plan to test"})
    client.post("/api/plans/approve")
    client.post("/api/execution/execute")

    # Let the run start, then cancel cooperatively.
    time.sleep(0.02)
    response = client.post("/api/execution/cancel")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["type"] == "execution_cancelled"


def test_status_is_idle_when_no_plan():
    client = _fresh_client()
    data = client.get("/api/status").json()["data"]
    assert data["status"] == "idle"


def test_plan_list_is_read_only():
    client = _fresh_client()
    response = client.get("/api/plans/list")
    assert response.status_code == 200
    assert response.json()["data"]["runs"] == []


def test_tasks_endpoint():
    client = _fresh_client()
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_tasks_endpoint_validates_status():
    client = _fresh_client()
    response = client.get("/api/tasks?status=bogus")
    assert response.status_code == 400


def test_events_endpoint():
    client = _fresh_client()
    response = client.get("/api/events?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_events_endpoint_validates_limit():
    client = _fresh_client()
    response = client.get("/api/events?limit=0")
    assert response.status_code == 400


def test_memories_endpoint():
    client = _fresh_client()
    response = client.get("/api/memories")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_memories_endpoint_validates_type():
    client = _fresh_client()
    response = client.get("/api/memories?memory_type=bogus")
    assert response.status_code == 400


def test_files_endpoint():
    client = _fresh_client()
    response = client.get("/api/files?path=.")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "entries" in data


def test_files_content_endpoint_validates_missing():
    client = _fresh_client()
    response = client.get("/api/files/content", params={"path": ""})
    assert response.status_code == 400


def test_notifications_endpoint():
    client = _fresh_client()
    response = client.get("/api/notifications?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_apps_endpoint():
    client = _fresh_client()
    response = client.get("/api/apps")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_no_generic_tool_passthrough():
    client = _fresh_client()
    # There must be no endpoint that lets the frontend invoke arbitrary
    # (mutating/external) tools directly.
    for path in (
        "/api/tool",
        "/api/tools",
        "/api/execution/execute_tool",
    ):
        response = client.post(path, json={"tool": "create_task"})
        assert response.status_code == 404


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
