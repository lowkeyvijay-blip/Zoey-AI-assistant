"""Zoey backend entry point for PyInstaller.

This script runs BEFORE any project imports so it can set environment
variables that config/settings.py and database/db.py will read at
import-time.  In development the existing ``python -m api.server``
flow is unchanged.
"""

import os
import sys
from pathlib import Path


def _setup_frozen_paths():
    """Configure user-writable and bundled-resource paths for the
    frozen (PyInstaller) executable."""

    exe_dir = Path(sys.executable).resolve().parent

    # User-writable data: %APPDATA%/Zoey/  (or ZOEY_DATA_DIR override)
    user_data = Path(
        os.environ.get(
            "ZOEY_DATA_DIR",
            os.path.join(os.environ.get("APPDATA", ""), "Zoey"),
        )
    )
    user_data.mkdir(parents=True, exist_ok=True)

    # Redirect mutable paths into the user-data directory.
    os.environ.setdefault("ZOEY_DB_DIR", str(user_data / "db"))
    os.environ.setdefault("ZOEY_FILES_ROOT", str(user_data / "files"))

    # Ensure the DB directory exists.
    Path(os.environ["ZOEY_DB_DIR"]).mkdir(parents=True, exist_ok=True)

    # Frontend dist is bundled inside _internal/frontend_dist/
    # (set by the spec file's datas collection).
    frontend_dist = exe_dir / "_internal" / "frontend_dist"
    if frontend_dist.is_dir():
        os.environ.setdefault("ZOEY_FRONTEND_DIR", str(frontend_dist))


if getattr(sys, "frozen", False):
    _setup_frozen_paths()

# Now it is safe to import the server – config.settings and
# database.db will pick up the environment variables above.
from api.server import app, settings  # noqa: E402
from database.db import initialize_database  # noqa: E402
import uvicorn  # noqa: E402


def main():
    initialize_database()
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
    )


if __name__ == "__main__":
    main()
