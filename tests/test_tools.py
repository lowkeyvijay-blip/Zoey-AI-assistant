from core.tool_manager import execute_tool, available_tools


print("Available tools:")
print(available_tools())

print("\nCreating task:")

result = execute_tool(
    "create_task",
    {
        "title": "Build Zoey",
        "due_at": "2026-08-12 20:00"
    }
)

print(result)

print("\nOpening calculator:")

result = execute_tool(
    "open_app",
    {
        "app_name": "calculator"
    }
)

print(result)