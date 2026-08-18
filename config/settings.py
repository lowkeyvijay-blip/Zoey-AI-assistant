from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# Phase 10.3: sandbox root for Zoey's file tools. Keep this
# separate from source code and database files by default.
FILES_ROOT = BASE_DIR / "zoey_files"


# Phase 10.9: the jarvis-ai frontend is served same-origin by the API
# server (GET catch-all), so no extra CORS origin or dev proxy is needed.
JARVIS_APP_DIR = BASE_DIR / "jarvis-ai"


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
