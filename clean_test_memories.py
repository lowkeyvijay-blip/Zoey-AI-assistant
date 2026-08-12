from database.db import get_connection


connection = get_connection()

test_phrases = [
    "Build my own Jarvis AI assistant",
    "build jarvis ai assistant",
    "The user wants to build his own AI assistant.",
    "I am building my own AI assistant called Zoey",
    "I am building Zoey",
    "working late at night",
    "prefer working late at night",
    "The user prefers working late at night.",
    "Laptop RAM",
    "Laptop RAM 16GB",
    "Laptop with 16GB RAM",
    "Finish the memory system today.",
    "Zoey is being built from an open-source project.",
]

deleted = 0

for phrase in test_phrases:
    cursor = connection.execute(
        "DELETE FROM memories WHERE content = ?",
        (phrase,)
    )

    deleted += cursor.rowcount


connection.commit()
connection.close()

print(f"Deleted {deleted} test memories.")