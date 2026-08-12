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
from tools import system
from tools.system import (
    ALLOWED_APPS,
    close_app,
    list_apps,
    open_app,
)

import core.agent_loop as agent_loop_module


class FakeProcess:

    def __init__(self, pid, live=True):
        self.pid = pid
        self.live = live
        self.terminated = False
        self.waited = False

    def poll(self):
        if self.live:
            return None

        return 0

    def terminate(self):
        self.terminated = True
        self.live = False

    def wait(self, timeout=None):
        self.waited = True
        return 0


class FakePopen:

    def __init__(self):
        self.calls = []
        self.next_pid = 1000

    def __call__(self, image):
        process = FakeProcess(self.next_pid)
        self.next_pid += 1
        self.calls.append(image)
        return process


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def main():
    print("\nPHASE 10.4 TEST: APP TOOLS\n")
    print("=" * 60)

    original_popen = system.subprocess.Popen
    original_processes = system._LAUNCHED_PROCESSES
    fake_popen = FakePopen()

    system.subprocess.Popen = fake_popen
    system._LAUNCHED_PROCESSES = {}

    try:

        print("\nTEST A: APP CATALOG")

        catalog = list_apps()
        names = {app["name"] for app in catalog}
        images = {app["image"] for app in catalog}

        verify(
            names == set(ALLOWED_APPS.keys()),
            "list_apps returns every allowlisted app"
        )
        verify(
            images == set(ALLOWED_APPS.values()),
            "list_apps returns the allowlisted image names"
        )
        verify(
            [app["name"] for app in catalog]
            == sorted(ALLOWED_APPS.keys()),
            "list_apps is deterministic and sorted"
        )

        print("\nTEST B: ALLOWED APP LAUNCH")

        result = open_app("notepad")
        verify(
            result["success"] is True,
            "open_app allows a catalog app"
        )
        verify(
            fake_popen.calls == ["notepad.exe"],
            "open_app uses the existing allowlisted image"
        )
        verify(
            len(system._LAUNCHED_PROCESSES["notepad"]) == 1,
            "open_app tracks the launched process handle"
        )

        result = open_app("  NOTEPAD  ")
        verify(
            result["success"] is True,
            "existing open_app normalization still works"
        )
        verify(
            fake_popen.calls[-1] == "notepad.exe",
            "normalized open_app still launches allowlisted image"
        )

        print("\nTEST C: UNKNOWN AND ARBITRARY APP REJECTION")

        bad_names = [
            "wordpad",
            "notepad.exe",
            "C:\\Windows\\System32\\notepad.exe",
            "..\\notepad",
            "/bin/sh",
            "1234",
        ]

        before_calls = len(fake_popen.calls)

        for app_name in bad_names:
            result = open_app(app_name)
            verify(
                result["success"] is False,
                f"open_app rejects {app_name!r}"
            )

        verify(
            len(fake_popen.calls) == before_calls,
            "rejected app names never reach Popen"
        )

        print("\nTEST D: CLOSE_APP SAFE TARGETING")

        system._LAUNCHED_PROCESSES = {}
        fake_popen.calls = []

        result = close_app("notepad")
        verify(
            result["success"] is False,
            "close_app refuses when Zoey has no verified process"
        )

        open_app("calculator")
        process = system._LAUNCHED_PROCESSES["calculator"][0]

        result = close_app("calculator")
        verify(
            result["success"] is True,
            "close_app closes a single verified launched process"
        )
        verify(
            process.terminated,
            "close_app terminates the verified process handle"
        )
        verify(
            process.waited,
            "close_app waits for the verified process"
        )

        for app_name in bad_names:
            result = close_app(app_name)
            verify(
                result["success"] is False,
                f"close_app rejects {app_name!r}"
            )

        arbitrary = FakeProcess(4242)
        system._LAUNCHED_PROCESSES = {
            "wordpad": [arbitrary],
        }
        result = close_app("wordpad")
        verify(
            result["success"] is False,
            "close_app refuses unknown executable names"
        )
        verify(
            not arbitrary.terminated,
            "unknown executable process is not terminated"
        )

        system._LAUNCHED_PROCESSES = {
            "notepad": [
                FakeProcess(2001),
                FakeProcess(2002),
            ]
        }
        result = close_app("notepad")
        verify(
            result["success"] is False,
            "close_app refuses ambiguous multiple processes"
        )
        verify(
            not any(
                process.terminated
                for process in system._LAUNCHED_PROCESSES["notepad"]
            ),
            "ambiguous processes are not terminated"
        )

        print("\nTEST E: TOOL EXECUTION PIPELINE")

        system._LAUNCHED_PROCESSES = {}
        fake_popen.calls = []

        result = execute_tool("list_apps", {})
        verify(
            result.get("success") is True,
            "execute_tool(list_apps) reports success"
        )
        verify(
            result["result"] == list_apps(),
            "execute_tool(list_apps) returns the catalog"
        )

        result = execute_tool(
            "open_app",
            {"app_name": "chrome"}
        )
        verify(
            result.get("success") is True
            and result["result"]["success"] is True,
            "execute_tool(open_app) preserves existing behavior"
        )

        result = execute_tool(
            "close_app",
            {"app_name": "chrome"}
        )
        verify(
            result.get("success") is True
            and result["result"]["success"] is True,
            "execute_tool(close_app) routes the app close tool"
        )

        result = execute_tool(
            "open_app",
            {"app_name": "C:\\bad.exe"}
        )
        verify(
            result.get("success") is True
            and result["result"]["success"] is False,
            "execute_tool(open_app) safely reports rejected paths"
        )

        loop = AgentLoop()
        result = loop.execute_one("list_apps", {})
        verify(
            result.get("success") is True,
            "AgentLoop.execute_one routes list_apps"
        )

        print("\nTEST F: STEP VALIDATION")

        valid_cases = [
            ("list_apps", {}),
            ("open_app", {"app_name": "notepad"}),
            ("close_app", {"app_name": "notepad"}),
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
            ("open_app", {}, "requires 'app_name'"),
            ("open_app", {"app_name": 5}, "must be a string"),
            ("close_app", {}, "requires 'app_name'"),
            ("close_app", {"app_name": 5}, "must be a string"),
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

        print("\nTEST G: FOUR-WAY REGISTRATION SYNC")

        app_tools = {
            "list_apps",
            "open_app",
            "close_app",
        }

        verify(
            app_tools.issubset(TOOLS),
            "all app tools are in the tool registry"
        )
        verify(
            app_tools.issubset(ALLOWED_TOOLS),
            "all app tools are in ALLOWED_TOOLS"
        )
        verify(
            all(name in TOOL_ARGUMENT_RULES for name in app_tools),
            "all app tools have argument rules"
        )
        verify(
            all(name in agent_loop_module.TOOLS for name in app_tools),
            "all app tools are documented in the LLM prompt"
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
        print("PHASE 10.4 APP TESTS PASSED")

    finally:
        system.subprocess.Popen = original_popen
        system._LAUNCHED_PROCESSES = original_processes

        print("\nCLEANUP: restored mocked process state")


if __name__ == "__main__":
    main()
