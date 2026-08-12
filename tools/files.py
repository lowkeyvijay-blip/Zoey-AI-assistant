from pathlib import Path

from config import settings


MAX_FILE_BYTES = 1024 * 1024

PROTECTED_PARTS = {
    "core",
    "config",
    "database",
    "memory",
    "tools",
    "tests",
    "__pycache__",
}

PROTECTED_FILENAMES = {
    "zoey.db",
    "zoey_backup.db",
}


def _files_root():
    root = Path(settings.FILES_ROOT).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve(strict=True)


def _validate_path_argument(path):
    if not isinstance(path, str):
        raise ValueError("path must be a string.")

    if not path.strip():
        raise ValueError("path cannot be empty.")

    if "\x00" in path:
        raise ValueError("path cannot contain null bytes.")

    return path.strip()


def _resolve_path(path, must_exist=False):
    path = _validate_path_argument(path)
    root = _files_root()
    candidate = Path(path).expanduser()

    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve(strict=False)

    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError("Path escapes the file sandbox.")

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"File path not found: {path}")

    return resolved


def _protect_mutation(path):
    root = _files_root()
    relative = path.relative_to(root)

    if path.name in PROTECTED_FILENAMES:
        raise ValueError("Refusing to modify a protected file.")

    if any(part in PROTECTED_PARTS for part in relative.parts):
        raise ValueError("Refusing to modify protected app files.")


def _validate_content(content):
    if not isinstance(content, str):
        raise ValueError("content must be a string.")

    size = len(content.encode("utf-8"))

    if size > MAX_FILE_BYTES:
        raise ValueError(
            f"content exceeds the {MAX_FILE_BYTES} byte limit."
        )

    return content, size


def _entry_info(path):
    stat = path.stat()

    return {
        "name": path.name,
        "path": str(path.relative_to(_files_root())),
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
    }


def list_dir(path):
    target = _resolve_path(path, must_exist=True)

    if not target.is_dir():
        raise ValueError("path is not a directory.")

    entries = [
        _entry_info(entry)
        for entry in sorted(
            target.iterdir(),
            key=lambda item: item.name.lower()
        )
    ]

    return {
        "path": str(target.relative_to(_files_root())),
        "entries": entries,
    }


def read_file(path):
    target = _resolve_path(path, must_exist=True)

    if not target.is_file():
        raise ValueError("path is not a file.")

    size = target.stat().st_size

    if size > MAX_FILE_BYTES:
        raise ValueError(
            f"file exceeds the {MAX_FILE_BYTES} byte limit."
        )

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError("file is not valid UTF-8 text.")

    return {
        "path": str(target.relative_to(_files_root())),
        "content": content,
        "size": size,
    }


def write_file(path, content):
    target = _resolve_path(path, must_exist=False)
    content, size = _validate_content(content)
    _protect_mutation(target)

    if target.exists() and target.is_dir():
        raise ValueError("path is a directory.")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        content,
        encoding="utf-8",
        newline=""
    )

    return {
        "path": str(target.relative_to(_files_root())),
        "written": size,
    }


def append_file(path, content):
    target = _resolve_path(path, must_exist=False)
    content, size = _validate_content(content)
    _protect_mutation(target)

    if target.exists() and target.is_dir():
        raise ValueError("path is a directory.")

    existing_size = target.stat().st_size if target.exists() else 0

    if existing_size + size > MAX_FILE_BYTES:
        raise ValueError(
            f"append would exceed the {MAX_FILE_BYTES} byte limit."
        )

    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open(
        "a",
        encoding="utf-8",
        newline=""
    ) as handle:
        handle.write(content)

    return {
        "path": str(target.relative_to(_files_root())),
        "appended": size,
        "size": existing_size + size,
    }


def delete_file(path):
    target = _resolve_path(path, must_exist=True)
    _protect_mutation(target)

    if not target.is_file():
        raise ValueError("path is not a file.")

    target.unlink()

    return True


def file_info(path):
    target = _resolve_path(path, must_exist=True)
    return _entry_info(target)
