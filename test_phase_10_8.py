from core.agent_loop import ALLOWED_TOOLS, TOOLS as PROMPT_TOOL_SOURCE
from core.step_validation import TOOL_ARGUMENT_RULES, validate_step
from core.tool_manager import TOOLS, execute_tool
from database.db import get_connection, initialize_database


def documented_tools():
    # AgentLoop's prompt constant is the authoritative LLM tool document.
    import core.agent_loop as agent_loop
    import re
    return re.findall(r"^\s*\d+\.\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*$", agent_loop.TOOLS, re.MULTILINE)


def cleanup():
    initialize_database()
    connection = get_connection()
    connection.execute("DELETE FROM notifications")
    connection.execute("DELETE FROM events")
    connection.execute("DELETE FROM tasks WHERE title LIKE 'phase10_8_%'")
    connection.commit()
    connection.close()


def run():
    cleanup()
    try:
        registry = set(TOOLS.keys())
        allowed = set(ALLOWED_TOOLS)
        rules = set(TOOL_ARGUMENT_RULES.keys())
        documented = set(documented_tools())

        assert registry == allowed
        assert registry == rules
        assert registry == documented
        assert len(documented_tools()) == len(set(documented_tools()))

        # Every registered tool must have a structural validation rule.
        for tool in registry:
            assert tool in TOOL_ARGUMENT_RULES

        # The current architecture deliberately has no separate production
        # classification registry. Keep the safety policy explicit here so
        # additions cannot silently omit destructive/external tools.
        read_only = {
            "list_apps", "list_tasks", "get_task", "recall_memories",
            "search_memories", "list_dir", "read_file", "file_info",
            "list_events", "upcoming_events", "fetch_url", "notifications_log",
        }
        mutating = {
            "create_task", "complete_task", "update_task", "delete_task",
            "remember", "forget", "update_memory", "write_file",
            "append_file", "delete_file", "add_event", "update_event",
            "delete_event",
        }
        external = {"open_app", "close_app", "open_url", "notify"}

        assert read_only | mutating | external == registry
        assert read_only.isdisjoint(mutating)
        assert read_only.isdisjoint(external)
        assert mutating.isdisjoint(external)

        # Hallucinated/unregistered tools are rejected before execution.
        invalid = validate_step({
            "tool": "hallucinated_tool",
            "arguments": {},
        })
        assert invalid["valid"] is False

        # No executable action is attempted for an invalid step.
        assert execute_tool("hallucinated_tool", {})["success"] is False

        # Cross-capability smoke through the single registered execution path.
        task = execute_tool("create_task", {"title": "phase10_8_task", "due_at": None})
        assert task["success"] is True

        import tools.files as files
        files.write_file("phase10_8.txt", "integration")
        read_result = files.read_file("phase10_8.txt")
        assert read_result["content"] == "integration"

        event = execute_tool("add_event", {
            "title": "phase10_8_event",
            "start_at": "2030-01-01T10:00:00",
            "end_at": "2030-01-01T11:00:00",
            "location": None,
            "notes": None,
        })
        assert event["success"] is True

        # Notification side effect is not invoked here; 10.7 has its own
        # deterministic mocked test. Validate its step contract instead.
        assert validate_step({
            "tool": "notify",
            "arguments": {"title": "Zoey", "message": "integration"},
        })["valid"] is True

        # Existing approval boundary is represented by the plan executor;
        # this test specifically proves the tool layer cannot bypass its own
        # registry/validation boundary with an unknown tool.
        assert validate_step({"tool": "notify", "arguments": None})["valid"] is False
        assert validate_step({"tool": "list_tasks", "arguments": None})["valid"] is True

        print("test_phase_10_8.py: 8 tests passed")
    finally:
        files = None
        try:
            import tools.files as file_tools
            file_tools.delete_file("phase10_8.txt")
        except Exception:
            pass
        cleanup()


if __name__ == "__main__":
    run()
