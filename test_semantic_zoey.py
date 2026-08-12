from core.zoey import Zoey


zoey = Zoey()


tests = [
    "I have 16GB RAM in my laptop.",
    "My laptop has 16GB of RAM.",
    "I upgraded my laptop to 32GB RAM.",
    "I prefer working late at night.",
    "I like working at night.",
    "I want to build my own Jarvis AI assistant.",
    "I want to create my own Jarvis AI assistant.",
]


for message in tests:

    print(f"\nUSER: {message}")

    memory = zoey.analyze_memory(
        message
    )

    if not memory:

        print("MEMORY: none")
        continue

    print(
        f"MEMORY: {memory['type']} | "
        f"{memory['content']} | "
        f"importance={memory['importance']}"
    )

    result = zoey.remember(
        memory["content"],
        memory["type"],
        memory["importance"]
    )

    print(f"SAVE: {result}")


print("\n--- FINAL MEMORIES ---")

for memory in zoey.recall(20).splitlines():

    print(memory)