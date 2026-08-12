from memory.memory import remember, recall


tests = [
    (
        "I have 16GB RAM in my laptop.",
        "fact"
    ),
    (
        "My laptop has 16 GB of RAM.",
        "fact"
    ),
    (
        "Laptop RAM is 16GB.",
        "fact"
    ),
    (
        "I want to build my own Jarvis AI assistant.",
        "goal"
    ),
    (
        "I want to create my own Jarvis AI assistant.",
        "goal"
    ),
    (
        "I prefer working late at night.",
        "preference"
    ),
    (
        "I prefer working at night.",
        "preference"
    ),
]


for content, memory_type in tests:

    saved = remember(
        content,
        memory_type,
        3
    )

    print(
        f"{'SAVED' if saved else 'DUPLICATE'} | "
        f"[{memory_type}] {content}"
    )


print("\n--- FINAL MEMORIES ---")

for memory in recall(20):

    print(
        f"[{memory['memory_type']}] "
        f"{memory['content']}"
    )