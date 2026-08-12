from core.agent_loop import AgentLoop


agent = AgentLoop()


tests = [
    "Open Notepad",
    "Create a task called Work on Zoey tomorrow at 8 PM",
    "Show me my tasks",
    "What's the capital of France?"
]


for message in tests:

    print("\n" + "=" * 60)
    print("USER:", message)

    result = agent.run(message)

    print("ZOEY:")
    print(result.get("content", result))