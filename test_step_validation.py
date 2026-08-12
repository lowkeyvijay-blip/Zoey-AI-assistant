from core.step_validation import (
    validate_step,
    validate_plan,
    normalize_step_arguments,
)


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def main():
    print(
        "\nPHASE 9.6 TEST: STEP VALIDATION "
        "(deterministic)\n"
    )
    print("=" * 60)

    print("\nTEST 1: TOOL PRESENCE AND NAME TYPE")

    result = validate_step({
        "number": 1,
        "title": "Open Notepad",
        "tool": "open_app",
        "arguments": {"app_name": "notepad"},
    })
    verify(
        result["valid"],
        "a well-formed tool step is valid"
    )
    verify(
        result["tool"] == "open_app",
        "the validated tool name is preserved"
    )

    result = validate_step({
        "number": 1,
        "title": "Review only",
    })
    verify(
        result["valid"],
        "a tool-less step is valid"
    )
    verify(
        result["not_auto"],
        "a tool-less step is not_auto"
    )

    result = validate_step({
        "number": 1,
        "title": "Review only",
        "tool": None,
    })
    verify(
        result["valid"] and result["not_auto"],
        "an explicit null tool is not_auto"
    )

    result = validate_step({
        "number": 1,
        "title": "Open",
        "tool": "",
    })
    verify(
        result["valid"] and result["not_auto"],
        "an empty tool is not_auto"
    )

    result = validate_step({
        "number": 1,
        "title": "Open",
        "tool": 42,
        "arguments": {},
    })
    verify(
        not result["valid"],
        "a non-string tool name is invalid"
    )
    verify(
        "must be a string" in result["error"],
        "the non-string tool error is clear"
    )

    print("\nTEST 2: TOOL EXISTENCE IN ALLOWED_TOOLS + REGISTRY")

    result = validate_step({
        "number": 1,
        "title": "Use Forbidden Tool",
        "tool": "bogus_tool",
        "arguments": {},
    })
    verify(
        not result["valid"],
        "a tool outside ALLOWED_TOOLS is invalid"
    )
    verify(
        "Tool 'bogus_tool' is not allowed." in result["error"],
        "the unknown-tool error matches the runtime wording"
    )

    allowed_examples = {
        "open_app": {"app_name": "notepad"},
        "create_task": {"title": "Work on Zoey"},
        "list_tasks": {},
        "complete_task": {"task_id": 16},
    }

    for tool, arguments in allowed_examples.items():
        result = validate_step({
            "number": 1,
            "title": tool,
            "tool": tool,
            "arguments": arguments,
        })
        verify(
            result["valid"],
            f"'{tool}' is recognized as an allowed tool"
        )

    from core import step_validation
    original_tools = step_validation.TOOLS
    try:
        step_validation.TOOLS = {
            "open_app": original_tools["open_app"],
        }
        result = validate_step({
            "number": 1,
            "title": "Create Task",
            "tool": "create_task",
            "arguments": {},
        })
        verify(
            not result["valid"],
            "a tool missing from the registry is invalid"
        )
        verify(
            "Unknown tool: create_task" in result["error"],
            "the registry-miss error is clear"
        )
    finally:
        step_validation.TOOLS = original_tools

    print("\nTEST 3: ARGUMENT NORMALIZATION")

    verify(
        normalize_step_arguments(None) == {},
        "None arguments normalize to an empty object"
    )
    verify(
        normalize_step_arguments({"a": 1}) == {"a": 1},
        "dict arguments pass through unchanged"
    )

    result = validate_step({
        "number": 1,
        "title": "List Tasks",
        "tool": "list_tasks",
    })
    verify(
        result["valid"],
        "a step omitting arguments is still valid"
    )
    verify(
        result["arguments"] == {},
        "omitted arguments normalize to an empty object"
    )

    result = validate_step({
        "number": 1,
        "title": "Bad Args",
        "tool": "open_app",
        "arguments": ["notepad"],
    })
    verify(
        not result["valid"],
        "non-object arguments are invalid"
    )
    verify(
        "must be an object" in result["error"],
        "the non-object argument error is clear"
    )

    print("\nTEST 4: PER-TOOL ARGUMENT SHAPES")

    result = validate_step({
        "number": 1,
        "title": "Open",
        "tool": "open_app",
        "arguments": {},
    })
    verify(
        not result["valid"],
        "open_app without app_name is invalid"
    )
    verify(
        "requires 'app_name'" in result["error"],
        "the missing-required-argument error is clear"
    )

    result = validate_step({
        "number": 1,
        "title": "Open",
        "tool": "open_app",
        "arguments": {"app_name": 7},
    })
    verify(
        not result["valid"],
        "open_app with a non-string app_name is invalid"
    )
    verify(
        "must be a string" in result["error"],
        "the wrong-type error names the expected type"
    )

    result = validate_step({
        "number": 1,
        "title": "Create",
        "tool": "create_task",
        "arguments": {},
    })
    verify(
        not result["valid"],
        "create_task without a title is invalid"
    )

    result = validate_step({
        "number": 1,
        "title": "Create",
        "tool": "create_task",
        "arguments": {"title": "Work on Zoey"},
    })
    verify(
        result["valid"],
        "create_task with only a title is valid"
    )

    result = validate_step({
        "number": 1,
        "title": "Create",
        "tool": "create_task",
        "arguments": {
            "title": "Work on Zoey",
            "due_at": "2026-08-12 20:00",
        },
    })
    verify(
        result["valid"],
        "create_task with a string due_at is valid"
    )

    result = validate_step({
        "number": 1,
        "title": "Create",
        "tool": "create_task",
        "arguments": {
            "title": "Work on Zoey",
            "due_at": None,
        },
    })
    verify(
        result["valid"],
        "create_task with a null due_at is valid"
    )

    result = validate_step({
        "number": 1,
        "title": "Create",
        "tool": "create_task",
        "arguments": {"title": 5},
    })
    verify(
        not result["valid"],
        "create_task with a non-string title is invalid"
    )

    result = validate_step({
        "number": 1,
        "title": "List",
        "tool": "list_tasks",
        "arguments": {},
    })
    verify(
        result["valid"],
        "list_tasks with no arguments is valid"
    )

    result = validate_step({
        "number": 1,
        "title": "Complete",
        "tool": "complete_task",
        "arguments": {},
    })
    verify(
        not result["valid"],
        "complete_task without a task_id is invalid"
    )

    result = validate_step({
        "number": 1,
        "title": "Complete",
        "tool": "complete_task",
        "arguments": {"task_id": "16"},
    })
    verify(
        not result["valid"],
        "complete_task with a string task_id is invalid"
    )
    verify(
        "must be an integer" in result["error"],
        "the task_id type error is clear"
    )

    result = validate_step({
        "number": 1,
        "title": "Complete",
        "tool": "complete_task",
        "arguments": {"task_id": 16},
    })
    verify(
        result["valid"],
        "complete_task with an integer task_id is valid"
    )

    print("\nTEST 5: SEMANTIC VALUES ARE NOT VALIDATED")

    result = validate_step({
        "number": 1,
        "title": "Open Banned App",
        "tool": "open_app",
        "arguments": {"app_name": "banned"},
    })
    verify(
        result["valid"],
        "a banned app name is structurally valid "
        "(semantic checks happen at runtime)"
    )

    print("\nTEST 6: VALIDATE_PLAN")

    plan = {
        "goal": "Finish Zeta",
        "steps": [
            {
                "number": 1,
                "title": "Open Notepad",
                "tool": "open_app",
                "arguments": {"app_name": "notepad"},
            },
            {
                "number": 2,
                "title": "Review",
            },
        ],
    }
    result = validate_plan(plan)
    verify(
        result["valid"],
        "a fully valid plan validates"
    )
    verify(
        result["errors"] == [],
        "a valid plan reports no errors"
    )

    plan = {
        "goal": "Finish Zeta",
        "steps": [
            {
                "number": 1,
                "title": "Open Notepad",
                "tool": "open_app",
                "arguments": {"app_name": "notepad"},
            },
            {
                "number": 2,
                "title": "Use Forbidden Tool",
                "tool": "bogus_tool",
                "arguments": {},
            },
        ],
    }
    result = validate_plan(plan)
    verify(
        not result["valid"],
        "a plan with an invalid step fails validation"
    )
    verify(
        len(result["errors"]) == 1,
        "exactly one error is reported"
    )
    verify(
        result["errors"][0]["number"] == 2,
        "the error is attributed to the right step"
    )
    verify(
        result["errors"][0]["title"] == "Use Forbidden Tool",
        "the error carries the step title"
    )

    result = validate_plan(None)
    verify(
        not result["valid"],
        "a non-dict plan fails validation"
    )

    result = validate_plan({"goal": "x", "steps": "bad"})
    verify(
        not result["valid"],
        "a plan with a non-list steps fails validation"
    )

    print("\n" + "=" * 60)
    print("PHASE 9.6 STEP VALIDATION TESTS PASSED")


if __name__ == "__main__":
    main()
