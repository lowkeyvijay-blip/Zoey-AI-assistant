import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# In a frozen (PyInstaller) exe the source tree lives inside a
# temporary _internal/ directory which is not writable.  User-mutable
# data (database, file sandbox, logs) is redirected to an
# OS-appropriate per-user location; read-only bundled resources
# (frontend dist) are resolved relative to the exe.

_IS_FROZEN = getattr(sys, "frozen", False)

if _IS_FROZEN:
    _EXE_DIR = Path(sys.executable).resolve().parent
    _USER_DATA = Path(
        os.environ.get(
            "ZOEY_DATA_DIR",
            os.path.join(os.environ.get("APPDATA", ""), "Zoey"),
        )
    )
else:
    _EXE_DIR = None
    _USER_DATA = None


# Phase 10.3: sandbox root for Zoey's file tools.
FILES_ROOT = (
    Path(os.environ["ZOEY_FILES_ROOT"])
    if "ZOEY_FILES_ROOT" in os.environ
    else (_USER_DATA / "files" if _IS_FROZEN else BASE_DIR / "zoey_files")
)


# Phase 10.9: the jarvis-ai frontend is served same-origin by the API
# server (GET catch-all), so no extra CORS origin or dev proxy is needed.
# The ZOEY_FRONTEND_DIR env var allows overriding the frontend directory
# at runtime (used only for debugging).
_JARVIS_APP_DIR = BASE_DIR / "jarvis-ai"
_FRONTEND_DIR_OVERRIDE = os.environ.get("ZOEY_FRONTEND_DIR")
if _FRONTEND_DIR_OVERRIDE:
    JARVIS_APP_DIR = Path(_FRONTEND_DIR_OVERRIDE)
elif _IS_FROZEN:
    JARVIS_APP_DIR = _EXE_DIR / "_internal" / "frontend_dist"
else:
    JARVIS_APP_DIR = _JARVIS_APP_DIR


# Phase 10.9: local API server for the frontend. Loopback-only by
# default; the Vite dev server is the only CORS origin allowed.
API_HOST = "127.0.0.1"
API_PORT = 8000
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def ensure_files_root():
    Path(FILES_ROOT).resolve().mkdir(
        parents=True,
        exist_ok=True
    )
