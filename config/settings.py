from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# Phase 10.3: sandbox root for Zoey's file tools. Keep this
# separate from source code and database files by default.
FILES_ROOT = BASE_DIR / "zoey_files"


def ensure_files_root():
    Path(FILES_ROOT).resolve().mkdir(
        parents=True,
        exist_ok=True
    )
