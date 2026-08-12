from core.zoey import Zoey


zoey = Zoey()


print("ADDING MEMORIES...\n")

zoey.remember(
    "The user's laptop has 32GB RAM",
    "fact",
    3
)

zoey.remember(
    "The user prefers working at night",
    "preference",
    3
)

zoey.remember(
    "The user wants to build their own Jarvis AI assistant",
    "goal",
    5
)


tests = [
    "How much RAM does my laptop have?",
    "When do I prefer working?",
    "What am I trying to build?",
    "What's the capital of France?"
]


for message in tests:

    print("\n" + "=" * 60)
    print(f"USER: {message}")

    context = zoey.get_relevant_context(
        message
    )

    print("\nRETRIEVED CONTEXT:")

    if context:
        print(context)
    else:
        print("None")

    print("\nZOEY:")

    print(
        zoey.ask_ai(message)
    )