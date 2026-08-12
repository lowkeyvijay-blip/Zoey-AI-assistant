import os
import shutil
import tempfile
from pathlib import Path

from config import settings
from core.tool_manager import (
    TOOLS,
    execute_tool,
    available_tools,
)
from core.agent_loop import AgentLoop, ALLOWED_TOOLS
from core.step_validation import (
    TOOL_ARGUMENT_RULES,
    validate_step,
)
from tools.files import (
    MAX_FILE_BYTES,
    append_file,
    delete_file,
    file_info,
    list_dir,
    read_file,
    write_file,
)

import core.agent_loop as agent_loop_module


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def expect_error(func, message_fragment, label):
    try:
        func()
    except Exception as error:
        verify(
            message_fragment in str(error),
            label
        )
    else:
        raise AssertionError(f"FAIL: {label}")


def main():
    print("\nPHASE 10.3 TEST: FILE TOOLS\n")
    print("=" * 60)

    original_root = settings.FILES_ROOT
    sandbox = Path(tempfile.mkdtemp(prefix="zoey-files-test-"))
    outside = Path(tempfile.mkdtemp(prefix="zoey-files-outside-"))

    settings.FILES_ROOT = sandbox

    try:

        print("\nTEST A: WRITE/READ/LIST/INFO/APPEND/DELETE")

        write_result = write_file(
            "notes/hello.txt",
            "hello"
        )
        verify(
            write_result["path"] == "notes\\hello.txt",
            "write_file writes inside the sandbox"
        )

        read_result = read_file("notes/hello.txt")
        verify(
            read_result["content"] == "hello",
            "read_file returns file content"
        )

        append_result = append_file(
            "notes/hello.txt",
            "\nworld"
        )
        verify(
            append_result["size"] == len("hello\nworld"),
            "append_file reports the new size"
        )
        verify(
            read_file("notes/hello.txt")["content"] == "hello\nworld",
            "read/write round trip preserves content"
        )

        info = file_info("notes/hello.txt")
        verify(
            info["type"] == "file",
            "file_info identifies files"
        )
        verify(
            info["size"] == len("hello\nworld"),
            "file_info reports file size"
        )

        listing = list_dir("notes")
        verify(
            any(
                entry["name"] == "hello.txt"
                and entry["type"] == "file"
                for entry in listing["entries"]
            ),
            "list_dir lists child files"
        )

        verify(
            delete_file("notes/hello.txt") is True,
            "delete_file deletes a file"
        )
        verify(
            not (sandbox / "notes" / "hello.txt").exists(),
            "deleted file is gone"
        )

        print("\nTEST B: MISSING AND TYPE ERRORS")

        expect_error(
            lambda: read_file("missing.txt"),
            "not found",
            "read_file reports a missing file"
        )
        expect_error(
            lambda: file_info("missing.txt"),
            "not found",
            "file_info reports a missing path"
        )

        (sandbox / "folder").mkdir()
        write_file("folder/file.txt", "x")

        expect_error(
            lambda: read_file("folder"),
            "not a file",
            "read_file rejects directories"
        )
        expect_error(
            lambda: list_dir("folder/file.txt"),
            "not a directory",
            "list_dir rejects files"
        )
        expect_error(
            lambda: delete_file("folder"),
            "not a file",
            "delete_file rejects directories"
        )

        print("\nTEST C: SANDBOX ESCAPE REJECTION")

        outside_file = outside / "outside.txt"
        outside_file.write_text("outside", encoding="utf-8")

        expect_error(
            lambda: read_file("../outside.txt"),
            "sandbox",
            "../ traversal is rejected"
        )
        expect_error(
            lambda: read_file("..\\outside.txt"),
            "sandbox",
            "..\\ traversal is rejected"
        )
        expect_error(
            lambda: read_file(str(outside_file)),
            "sandbox",
            "absolute outside paths are rejected"
        )
        expect_error(
            lambda: write_file(str(outside_file), "x"),
            "sandbox",
            "Windows drive paths outside the sandbox are rejected"
        )

        unc_path = "\\\\server\\share\\file.txt"
        expect_error(
            lambda: read_file(unc_path),
            "sandbox",
            "UNC-style outside paths are rejected"
        )

        symlink_path = sandbox / "escape-link.txt"
        try:
            os.symlink(outside_file, symlink_path)
        except (OSError, NotImplementedError):
            print(
                "  PASS: symlink escape test skipped "
                "(symlinks unavailable)"
            )
        else:
            expect_error(
                lambda: read_file("escape-link.txt"),
                "sandbox",
                "symlink escape attempts are rejected"
            )

        print("\nTEST D: SIZE LIMITS")

        too_large = "x" * (MAX_FILE_BYTES + 1)
        expect_error(
            lambda: write_file("too-large.txt", too_large),
            "byte limit",
            "write_file rejects content over the size limit"
        )

        write_file("limit.txt", "x" * MAX_FILE_BYTES)
        expect_error(
            lambda: append_file("limit.txt", "x"),
            "byte limit",
            "append_file rejects writes beyond the size limit"
        )
        verify(
            read_file("limit.txt")["size"] == MAX_FILE_BYTES,
            "read_file allows a file at the size limit"
        )
        append_file("limit.txt", "")
        expect_error(
            lambda: read_file("too-big-on-disk.txt"),
            "not found",
            "missing oversized fixture is not created accidentally"
        )

        print("\nTEST E: INVALID ARGUMENTS")

        expect_error(
            lambda: list_dir(""),
            "path cannot be empty",
            "empty paths are rejected"
        )
        expect_error(
            lambda: read_file(42),
            "path must be a string",
            "non-string paths are rejected"
        )
        expect_error(
            lambda: write_file("x.txt", 42),
            "content must be a string",
            "non-string content is rejected"
        )
        expect_error(
            lambda: write_file("bad\x00path", "x"),
            "null",
            "null bytes in paths are rejected"
        )

        print("\nTEST F: TOOL EXECUTION PIPELINE")

        result = execute_tool(
            "write_file",
            {"path": "pipe.txt", "content": "pipe"}
        )
        verify(
            result.get("success") is True,
            "execute_tool(write_file) reports success"
        )
        result = execute_tool(
            "read_file",
            {"path": "pipe.txt"}
        )
        verify(
            result.get("success") is True
            and result["result"]["content"] == "pipe",
            "execute_tool(read_file) returns content"
        )

        loop = AgentLoop()
        result = loop.execute_one(
            "append_file",
            {"path": "pipe.txt", "content": "line"}
        )
        verify(
            result.get("success") is True,
            "AgentLoop.execute_one routes file tools"
        )

        print("\nTEST G: STEP VALIDATION")

        valid_cases = [
            ("list_dir", {"path": "."}),
            ("read_file", {"path": "pipe.txt"}),
            ("write_file", {"path": "new.txt", "content": "x"}),
            ("append_file", {"path": "new.txt", "content": "x"}),
            ("delete_file", {"path": "new.txt"}),
            ("file_info", {"path": "pipe.txt"}),
        ]

        for tool, arguments in valid_cases:
            result = validate_step({
                "number": 1,
                "title": tool,
                "tool": tool,
                "arguments": arguments,
            })
            verify(
                result["valid"],
                f"{tool} validates with required arguments"
            )

        invalid_cases = [
            ("list_dir", {}, "requires 'path'"),
            ("read_file", {"path": 5}, "must be a string"),
            ("write_file", {"path": "x"}, "requires 'content'"),
            ("append_file", {"path": "x", "content": 5}, "must be a string"),
            ("delete_file", {}, "requires 'path'"),
            ("file_info", {}, "requires 'path'"),
        ]

        for tool, arguments, expected in invalid_cases:
            result = validate_step({
                "number": 1,
                "title": tool,
                "tool": tool,
                "arguments": arguments,
            })
            verify(
                not result["valid"],
                f"{tool} rejects invalid arguments"
            )
            verify(
                expected in result["error"],
                f"{tool} error mentions {expected}"
            )

        print("\nTEST H: FOUR-WAY REGISTRATION SYNC")

        file_tools = {
            "list_dir",
            "read_file",
            "write_file",
            "append_file",
            "delete_file",
            "file_info",
        }

        verify(
            file_tools.issubset(TOOLS),
            "all file tools are in the tool registry"
        )
        verify(
            file_tools.issubset(ALLOWED_TOOLS),
            "all file tools are in ALLOWED_TOOLS"
        )
        verify(
            all(name in TOOL_ARGUMENT_RULES for name in file_tools),
            "all file tools have argument rules"
        )
        verify(
            all(name in agent_loop_module.TOOLS for name in file_tools),
            "all file tools are documented in the LLM prompt"
        )
        verify(
            set(available_tools()) == set(TOOLS.keys()),
            "available_tools matches the registry"
        )
        verify(
            ALLOWED_TOOLS == set(TOOLS.keys()),
            "ALLOWED_TOOLS exactly matches the registry"
        )

        print("\n" + "=" * 60)
        print("PHASE 10.3 FILE TESTS PASSED")

    finally:
        settings.FILES_ROOT = original_root
        shutil.rmtree(sandbox, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)

        print("\nCLEANUP: removed temporary file sandboxes")


if __name__ == "__main__":
    main()
