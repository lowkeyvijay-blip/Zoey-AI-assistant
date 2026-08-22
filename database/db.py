import os
import sqlite3
import sys
from pathlib import Path

from config import settings
from config.settings import ensure_files_root


_DB_DIR_OVERRIDE = os.environ.get("ZOEY_DB_DIR")

if _DB_DIR_OVERRIDE:
    # Explicit override (set by backend.py for frozen builds, or by
    # tests/tools).
    DB_DIR = Path(_DB_DIR_OVERRIDE)
elif getattr(sys, "frozen", False):
    # Safety net: never write into the read-only PyInstaller bundle.
    DB_DIR = settings.DATA_DIR / "db"
else:
    DB_DIR = Path(__file__).resolve().parent


DB_PATH = DB_DIR / "zoey.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    ensure_files_root()

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'note',
            importance INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            due_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Phase 9.8: persistent run state. A run is created at
    # approval and its steps are written through to disk as
    # the plan executes. Recovery marks an in-flight run as
    # interrupted after a restart.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS plan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            status TEXT DEFAULT 'approved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_at TEXT NOT NULL,
            end_at TEXT NOT NULL,
            location TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS plan_steps (
            run_id INTEGER NOT NULL,
            number INTEGER NOT NULL,
            title TEXT NOT NULL,
            tool TEXT,
            arguments_json TEXT,
            depends_on_json TEXT,
            task_id INTEGER,
            status TEXT DEFAULT 'pending',
            result_json TEXT,
            PRIMARY KEY (run_id, number)
        )
    """)

    connection.commit()
    connection.close()

    # Upgrade existing databases
    migrate_database()


def migrate_database():
    connection = get_connection()

    columns = connection.execute(
        "PRAGMA table_info(memories)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "memory_type" not in column_names:
        connection.execute("""
            ALTER TABLE memories
            ADD COLUMN memory_type TEXT DEFAULT 'note'
        """)

    if "importance" not in column_names:
        connection.execute("""
            ALTER TABLE memories
            ADD COLUMN importance INTEGER DEFAULT 1
        """)

    connection.commit()
    connection.close()
