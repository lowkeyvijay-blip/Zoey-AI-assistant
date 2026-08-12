from database.db import initialize_database
from tools.tasks import create_task, list_tasks, complete_task
from tools.system import open_app


def main():
    initialize_database()

    print("\nZOEY TOOL TEST\n")

    task = create_task(
        "Test Zoey task",
        "2026-08-12 20:00"
    )

    print("Created task:")
    print(task)

    print("\nAll tasks:")
    print(list_tasks())

    

    print("\nCompleting task...")
    print(complete_task(task["id"]))

    print("\nAll tasks after completion:")
    print(list_tasks())


if __name__ == "__main__":
    main()

    from memory.memory import remember, recall

print("\nMEMORY TEST")

remember("The user wants to build his own AI assistant.", "goal")
remember("The user prefers working late at night.", "preference")
remember("Zoey is being built from an open-source project.", "fact")
remember("Finish the memory system today.", "note")

print("\nAll memories:")
print(recall())

print("\nGoals:")
print(recall(memory_type="goal"))

print("\nPreferences:")
print(recall(memory_type="preference"))