"""Local FastAPI server connecting the zoey-shell frontend to Zoey.

Phase 10.9 integration. Design notes:

- The server binds to 127.0.0.1 only and is a personal, single-user,
  loopback service. There is no authentication token.
- Exactly one shared Zoey instance (see api/state.py) is the single
  source of truth for plan/approval/execution state. A lock serializes
  state-mutating operations; /api/status intentionally does NOT take it
  (reads are GIL-atomic and must never block on a running plan).
- Approval and execution stay separate operations, matching the backend
  state machine exactly. approve/reject never start execution.
- All resource endpoints (/api/tasks, /api/events, ...) are read-only
  wrappers over the existing Phase 10 tools. Mutating/external tools are
  deliberately NOT exposed over HTTP; they remain reachable only through
  the orchestrator's plan-approval flow.

Run with:  python -m api.server
"""

import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import settings
from core.orchestrator import RUN_TERMINAL_STATES
from tools import calendar, files, memory_tools, notifications, system, tasks

from api.state import get_zoey, lock as zoey_lock


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


# ----------------------------------------------------------
# Response helpers
# ----------------------------------------------------------

def _ok(data):
    return {"ok": True, "data": data}


def _orchestrator_result(result):
    """Convert an orchestrator result into a response, mapping the
    orchestrator's own 'error' results to HTTP 400 so the frontend can
    display them as actionable errors (e.g. 'There's no approved plan
    to execute.')."""
    if result.get("type") == "error":
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "error",
                "Request failed.",
            ),
        )

    return _ok(result)


# ----------------------------------------------------------
# Background execution
# ----------------------------------------------------------

_execution_lock = threading.Lock()
_execution_active = False
_execution_thread = None


def _execute_worker():
    global _execution_active

    try:
        with zoey_lock():
            get_zoey().orchestrator.execute_approved_plan()
    except Exception:
        # The state machine persists everything; if the exception
        # escaped mid-run the write-through leaves the run in a
        # recoverable state, and the terminal status is surfaced by
        # /api/status. Nothing more can be done safely here.
        pass
    finally:
        with _execution_lock:
            _execution_active = False


def _start_execution():
    """Validate that execution is possible, then run it in a background
    thread. Returns an accepted response or a 400 matching the
    orchestrator's own guards. Never fabricates approval state."""

    global _execution_active

    with zoey_lock():

        record = get_zoey().orchestrator.approved_plan

        if record is None:
            raise HTTPException(
                status_code=400,
                detail="There's no approved plan to execute.",
            )

        status = record.get("status")

        if status == "running":
            raise HTTPException(
                status_code=400,
                detail="The plan is already running.",
            )

        if status in RUN_TERMINAL_STATES:
            raise HTTPException(
                status_code=400,
                detail=(
                    "This plan has already finished. "
                    "Say 're-run the plan' to execute it again."
                ),
            )

        # approved or interrupted: valid to execute.
        with _execution_lock:

            if _execution_active:
                raise HTTPException(
                    status_code=400,
                    detail="The plan is already running.",
                )

            _execution_active = True

            global _execution_thread
            _execution_thread = threading.Thread(
                target=_execute_worker,
                daemon=True,
            )
            _execution_thread.start()

        return _ok({
            "type": "accepted",
            "status": "running",
        })


# ----------------------------------------------------------
# App factory
# ----------------------------------------------------------

def create_app(zoey=None):
    """Build the FastAPI app. Tests pass a fake Zoey instance; the real
    backend is created lazily on first request otherwise."""

    if zoey is not None:
        from api.state import set_zoey
        set_zoey(zoey)

    app = FastAPI(
        title="Zoey API",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    # --------------------------------------------------
    # Health
    # --------------------------------------------------

    @app.get("/api/health")
    def health():
        return _ok({"status": "ok"})

    # --------------------------------------------------
    # Chat
    # --------------------------------------------------

    @app.post("/api/chat")
    def chat(request: ChatRequest):
        zoey = get_zoey()

        try:
            with zoey_lock():
                result = zoey.respond_structured(request.message)
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Zoey failed: {error}",
            )

        return _ok({
            "message": {
                "id": f"a{int(time.time() * 1000)}",
                "role": "assistant",
                "type": result.get("type", "text"),
                "content": zoey.format_result(result),
                "data": result,
            },
        })

    # --------------------------------------------------
    # Plan lifecycle (approval and execution stay separate)
    # --------------------------------------------------

    @app.get("/api/status")
    def status():
        # Intentionally no lock: this must stay readable while a plan
        # runs in the background. Reads of the in-memory record are
        # GIL-atomic and safe for this single-user service.
        zoey = get_zoey()

        try:
            result = zoey.orchestrator.execution_status()
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=str(error),
            )

        return _ok(result)

    @app.post("/api/plans/approve")
    def approve_plan():
        zoey = get_zoey()

        with zoey_lock():
            result = zoey.orchestrator.approve()

        return _orchestrator_result(result)

    @app.post("/api/plans/reject")
    def reject_plan():
        zoey = get_zoey()

        with zoey_lock():
            result = zoey.orchestrator.reject()

        return _orchestrator_result(result)

    @app.post("/api/execution/execute")
    def execute_plan():
        return _start_execution()

    @app.post("/api/execution/cancel")
    def cancel_execution():
        zoey = get_zoey()

        # Peek without the lock. While a run is active the background
        # thread holds the lock for the whole run, so the cooperative
        # flag must be set without it (the running branch only writes
        # the boolean flag). Any other branch is serialized normally.
        record = zoey.orchestrator.approved_plan

        if (
            record is not None
            and record.get("status") == "running"
        ):
            result = zoey.orchestrator.cancel_execution()
        else:
            with zoey_lock():
                result = zoey.orchestrator.cancel_execution()

        return _orchestrator_result(result)

    @app.get("/api/plans/list")
    def plan_list():
        zoey = get_zoey()

        with zoey_lock():
            result = zoey.orchestrator.plan_list()

        return _orchestrator_result(result)

    # --------------------------------------------------
    # Read-only resource endpoints (Phase 10 panels)
    #
    # These wrap only the read-only Phase 10 tool set. Mutating and
    # external tools are deliberately not exposed over HTTP.
    # --------------------------------------------------

    def _call_tool(func, *args, **kwargs):
        try:
            return _ok(func(*args, **kwargs))
        except (ValueError, TypeError, FileNotFoundError) as error:
            raise HTTPException(status_code=400, detail=str(error))
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Tool error: {error}",
            )

    @app.get("/api/tasks")
    def list_tasks(status: str | None = None):
        return _call_tool(tasks.list_tasks, status=status)

    @app.get("/api/events")
    def list_events(limit: int = 20):
        return _call_tool(calendar.upcoming_events, limit=limit)

    @app.get("/api/memories")
    def list_memories(memory_type: str | None = None, limit: int = 20):
        return _call_tool(
            memory_tools.recall_memories,
            memory_type=memory_type,
            limit=limit,
        )

    @app.get("/api/files")
    def list_files(path: str = "."):
        if not path or not path.strip():
            path = "."
        return _call_tool(files.list_dir, path=path)

    @app.get("/api/files/content")
    def read_file_content(path: str):
        return _call_tool(files.read_file, path=path)

    @app.get("/api/notifications")
    def list_notifications(limit: int = 20):
        return _call_tool(notifications.notifications_log, limit=limit)

    @app.get("/api/apps")
    def list_apps():
        return _call_tool(system.list_apps)

    # --------------------------------------------------
    # Static frontend (jarvis-ai), served same-origin
    #
    # A catch-all so /api/* stays JSON: unknown API paths (and every
    # non-GET method) still return 404. Only GET serves static assets,
    # resolving inside JARVIS_APP_DIR with an index.html fallback.
    # --------------------------------------------------

    @app.api_route("/{full_path:path}", methods=["GET", "POST"], include_in_schema=False)
    def serve_frontend(full_path: str, request: Request):
        if request.method != "GET":
            raise HTTPException(status_code=404, detail="Not found")

        if full_path.split("/", 1)[0] == "api":
            raise HTTPException(status_code=404, detail="Not found")

        root = settings.JARVIS_APP_DIR.resolve()
        target = (root / full_path).resolve()
        if target.is_relative_to(root) and target.is_file():
            return FileResponse(target)

        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)

        raise HTTPException(status_code=404, detail="Not found")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
    )
