from core.agent_loop import ALLOWED_TOOLS
from core.tool_manager import TOOLS


# Per-tool argument shape rules. Each rule maps an argument
# name to its expected type(s) and whether it is required.
# This is lightweight structural validation only: it never
# judges semantic values (e.g. whether an app is allowed).
TOOL_ARGUMENT_RULES = {
    "open_app": {
        "app_name": {"types": (str,), "required": True},
    },
    "list_apps": {},
    "close_app": {
        "app_name": {"types": (str,), "required": True},
    },
    "create_task": {
        "title": {"types": (str,), "required": True},
        "due_at": {
            "types": (str, type(None)),
            "required": False,
        },
    },
    "list_tasks": {
        "status": {
            "types": (str,),
            "required": False,
        },
    },
    "complete_task": {
        "task_id": {"types": (int,), "required": True},
    },
    "get_task": {
        "task_id": {"types": (int,), "required": True},
    },
    "update_task": {
        "task_id": {"types": (int,), "required": True},
        "title": {"types": (str,), "required": False},
        "due_at": {
            "types": (str, type(None)),
            "required": False,
        },
        "status": {"types": (str,), "required": False},
    },
    "delete_task": {
        "task_id": {"types": (int,), "required": True},
    },
    "remember": {
        "content": {"types": (str,), "required": True},
        "memory_type": {"types": (str,), "required": False},
        "importance": {"types": (int,), "required": False},
    },
    "recall_memories": {
        "memory_type": {"types": (str,), "required": False},
        "limit": {"types": (int,), "required": False},
    },
    "search_memories": {
        "query": {"types": (str,), "required": True},
        "limit": {"types": (int,), "required": False},
    },
    "forget": {
        "memory_id": {"types": (int,), "required": True},
    },
    "update_memory": {
        "memory_id": {"types": (int,), "required": True},
        "content": {"types": (str,), "required": True},
        "memory_type": {"types": (str,), "required": False},
        "importance": {"types": (int,), "required": False},
    },
    "list_dir": {
        "path": {"types": (str,), "required": True},
    },
    "read_file": {
        "path": {"types": (str,), "required": True},
    },
    "write_file": {
        "path": {"types": (str,), "required": True},
        "content": {"types": (str,), "required": True},
    },
    "append_file": {
        "path": {"types": (str,), "required": True},
        "content": {"types": (str,), "required": True},
    },
    "delete_file": {
        "path": {"types": (str,), "required": True},
    },
    "file_info": {
        "path": {"types": (str,), "required": True},
    },
    "add_event": {
        "title": {"types": (str,), "required": True},
        "start_at": {"types": (str,), "required": True},
        "end_at": {"types": (str,), "required": True},
        "location": {"types": (str, type(None)), "required": False},
        "notes": {"types": (str, type(None)), "required": False},
    },
    "list_events": {
        "start_at": {"types": (str, type(None)), "required": False},
        "end_at": {"types": (str, type(None)), "required": False},
        "limit": {"types": (int,), "required": False},
    },
    "upcoming_events": {
        "limit": {"types": (int,), "required": False},
    },
    "update_event": {
        "event_id": {"types": (int,), "required": True},
        "title": {"types": (str,), "required": False},
        "start_at": {"types": (str,), "required": False},
        "end_at": {"types": (str,), "required": False},
        "location": {"types": (str, type(None)), "required": False},
        "notes": {"types": (str, type(None)), "required": False},
    },
    "delete_event": {
        "event_id": {"types": (int,), "required": True},
    },
    "open_url": {
        "url": {"types": (str,), "required": True},
    },
    "fetch_url": {
        "url": {"types": (str,), "required": True},
        "max_chars": {"types": (int,), "required": False},
    },
    "notify": {
        "title": {"types": (str,), "required": True},
        "message": {"types": (str,), "required": True},
    },
    "notifications_log": {
        "limit": {"types": (int,), "required": False},
    },
}


def normalize_step_arguments(arguments):

    # A tool step that omits its arguments must behave
    # exactly like one that passes an empty object.
    if arguments is None:
        return {}

    return arguments


def _type_names(types):

    names = []

    for tool_type in types:

        if tool_type is str:
            names.append("a string")
        elif tool_type is int:
            names.append("an integer")
        elif tool_type is type(None):
            names.append("null")
        else:
            names.append(tool_type.__name__)

    return " or ".join(names)


def _validate_arguments(tool, arguments):

    rules = TOOL_ARGUMENT_RULES.get(tool, {})

    for name, rule in rules.items():

        present = (
            name in arguments
            and arguments[name] is not None
        )

        if rule.get("required", False):

            if not present:
                return (
                    f"Tool '{tool}' requires '{name}'."
                )

        if present:

            if not isinstance(
                arguments[name],
                rule["types"]
            ):
                return (
                    f"Tool '{tool}' argument '{name}' "
                    f"must be "
                    f"{_type_names(rule['types'])}."
                )

    return None


def validate_step(step):
    """
    Validate a single plan step for execution.

    Returns a dict:
      {
        "valid": bool,
        "error": str | None,
        "tool": str | None,
        "arguments": dict,
        "not_auto": bool,
      }

    A step without a tool action is an informational
    (not_auto) step: it is valid and is never executed.
    Semantic values are not validated here.
    """

    if not isinstance(step, dict):
        return {
            "valid": False,
            "error": "Step must be a dictionary.",
            "tool": None,
            "arguments": {},
            "not_auto": False,
        }

    tool = step.get("tool")

    if tool is None or tool == "":
        return {
            "valid": True,
            "error": None,
            "tool": None,
            "arguments": {},
            "not_auto": True,
        }

    if not isinstance(tool, str):
        return {
            "valid": False,
            "error": "Tool name must be a string.",
            "tool": tool,
            "arguments": {},
            "not_auto": False,
        }

    if tool not in ALLOWED_TOOLS:
        return {
            "valid": False,
            "error": f"Tool '{tool}' is not allowed.",
            "tool": tool,
            "arguments": {},
            "not_auto": False,
        }

    if tool not in TOOLS:
        return {
            "valid": False,
            "error": f"Unknown tool: {tool}",
            "tool": tool,
            "arguments": {},
            "not_auto": False,
        }

    arguments = normalize_step_arguments(
        step.get("arguments")
    )

    if not isinstance(arguments, dict):
        return {
            "valid": False,
            "error": "Tool arguments must be an object.",
            "tool": tool,
            "arguments": {},
            "not_auto": False,
        }

    argument_error = _validate_arguments(tool, arguments)

    if argument_error is not None:
        return {
            "valid": False,
            "error": argument_error,
            "tool": tool,
            "arguments": arguments,
            "not_auto": False,
        }

    return {
        "valid": True,
        "error": None,
        "tool": tool,
        "arguments": arguments,
        "not_auto": False,
    }


def validate_plan(plan):
    """
    Validate every step in a plan without executing it.

    Returns a dict:
      {
        "valid": bool,
        "errors": [
            {"number": int | None, "title": str, "error": str}
        ]
      }
    """

    if not isinstance(plan, dict):
        return {
            "valid": False,
            "errors": [{
                "number": None,
                "title": None,
                "error": "Plan must be a dictionary.",
            }],
        }

    steps = plan.get("steps", [])

    if not isinstance(steps, list):
        return {
            "valid": False,
            "errors": [{
                "number": None,
                "title": None,
                "error": "Plan 'steps' must be a list.",
            }],
        }

    errors = []

    for step in steps:

        if isinstance(step, dict):
            number = step.get("number")
            title = step.get("title")
        else:
            number = None
            title = None

        result = validate_step(step)

        if not result["valid"]:
            errors.append({
                "number": number,
                "title": title,
                "error": result["error"],
            })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
