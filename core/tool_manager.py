from tools.tasks import (
    create_task,
    list_tasks,
    complete_task,
    get_task,
    update_task,
    delete_task,
)
from tools.system import (
    list_apps,
    open_app,
    close_app,
)
from tools.memory_tools import (
    remember,
    recall_memories,
    search_memories,
    forget,
    update_memory,
)
from tools.calendar import (
    add_event,
    list_events,
    upcoming_events,
    update_event,
    delete_event,
)
from tools.files import (
    list_dir,
    read_file,
    write_file,
    append_file,
    delete_file,
    file_info,
)
from tools.browser import open_url, fetch_url
from tools.notifications import notify, notifications_log


TOOLS = {
    "create_task": create_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "list_apps": list_apps,
    "open_app": open_app,
    "close_app": close_app,
    "get_task": get_task,
    "update_task": update_task,
    "delete_task": delete_task,
    "remember": remember,
    "recall_memories": recall_memories,
    "search_memories": search_memories,
    "forget": forget,
    "update_memory": update_memory,
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "delete_file": delete_file,
    "file_info": file_info,
    "add_event": add_event,
    "list_events": list_events,
    "upcoming_events": upcoming_events,
    "update_event": update_event,
    "delete_event": delete_event,
    "open_url": open_url,
    "fetch_url": fetch_url,
    "notify": notify,
    "notifications_log": notifications_log,
}


def execute_tool(tool_name: str, arguments=None):

    tool = TOOLS.get(tool_name)

    if tool is None:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }

    # Some small local models return "", null,
    # or other values for tools that need no arguments.
    if arguments is None or arguments == "":
        arguments = {}

    if not isinstance(arguments, dict):
        return {
            "success": False,
            "error": "Tool arguments must be a JSON object."
        }

    try:

        result = tool(**arguments)

        return {
            "success": True,
            "result": result
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }


def available_tools():
    return list(TOOLS.keys())
