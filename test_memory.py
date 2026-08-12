from core.zoey import Zoey
from memory.memory import recall


zoey = Zoey()

tests = [
    "I want to build my own Jarvis AI assistant.",
    "I want to build my own Jarvis AI assistant.",
    "I prefer working late at night.",
    "I prefer working late at night.",
    "My laptop has 16GB of RAM.",
    "My laptop has 16GB of RAM.",
    "What's 2 + 2?",
]

for message in tests:

    print(f"\nUSER: {message}")

    memory = zoey.analyze_memory(message)

    if memory:
        result = zoey.remember(
            memory["content"],
            memory["type"],
            memory["importance"]
        )

        print(
            f"MEMORY: {memory['type']} | "
            f"{memory['content']} | "
            f"importance={memory['importance']}"
        )

        print(f"SAVE: {result}")

    else:
        print("MEMORY: none")

print("\n--- MEMORIES ---")

memories = recall(20)

for memory in memories:
    print(
        f"[{memory['memory_type']}] "
        f"{memory['content']} "
        f"(importance={memory['importance']})"
    )