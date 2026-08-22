# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ZoeyBackend.exe

Build with:
    cd C:\\Zoey-ai
    pyinstaller packaging\\zoey_backend.spec

Output: dist\\ZoeyBackend\\  (onedir; consumed by electron-builder's
extraResources mapping ../dist/ZoeyBackend -> backend/ZoeyBackend)
"""

import os
import sys
from pathlib import Path

block_cipher = None

REPO_ROOT = Path(SPECPATH).parent
FRONTEND_DIST = REPO_ROOT / "jarvis-ai"

a = Analysis(
    [str(REPO_ROOT / "backend.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), "frontend_dist"),
    ],
    hiddenimports=[
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "pydantic",
        "starlette",
        "starlette.middleware.cors",
        "starlette.responses",
        "starlette.routing",
        "config",
        "config.settings",
        "core",
        "core.zoey",
        "core.orchestrator",
        "core.planner",
        "core.intent",
        "core.agent_loop",
        "core.tool_manager",
        "core.step_validation",
        "core.run_store",
        "database",
        "database.db",
        "memory",
        "memory.memory",
        "tools",
        "tools.tasks",
        "tools.system",
        "tools.calendar",
        "tools.files",
        "tools.browser",
        "tools.notifications",
        "tools.memory_tools",
        "api",
        "api.server",
        "api.state",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
        "pytest",
        "_pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ZoeyBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ZoeyBackend",
)
