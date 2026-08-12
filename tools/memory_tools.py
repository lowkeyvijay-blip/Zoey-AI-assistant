from memory.memory import (
    MEMORY_TYPES,
    remember as store_memory,
    recall,
    search_memories as search,
    delete_memory,
    update_memory as update_stored_memory,
)


def _validate_limit(limit):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError("limit must be an integer.")

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    return limit


def _validate_memory_type(memory_type):
    if memory_type is None:
        return "note"

    if memory_type not in MEMORY_TYPES:
        raise ValueError(
            f"Invalid memory type: {memory_type}"
        )

    return memory_type


def _validate_importance(importance):
    try:
        importance = int(importance)
    except (TypeError, ValueError):
        raise ValueError("importance must be an integer.")

    if not 1 <= importance <= 5:
        raise ValueError("importance must be between 1 and 5.")

    return importance


def remember(
    content: str,
    memory_type: str = "note",
    importance: int = 1
):
    content = content.strip()

    if not content:
        raise ValueError("Memory content cannot be empty.")

    memory_type = _validate_memory_type(memory_type)
    importance = _validate_importance(importance)

    saved = store_memory(
        content,
        memory_type,
        importance
    )

    return {
        "saved": saved,
    }


def recall_memories(
    memory_type=None,
    limit: int = 10
):
    limit = _validate_limit(limit)

    if memory_type is not None:
        memory_type = _validate_memory_type(memory_type)

    rows = recall(
        limit=limit,
        memory_type=memory_type
    )

    return [dict(row) for row in rows]


def search_memories(
    query: str,
    limit: int = 5
):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    limit = _validate_limit(limit)

    rows = search(
        query.strip(),
        limit
    )

    return [dict(row) for row in rows]


def forget(memory_id: int):
    deleted = delete_memory(memory_id)

    if not deleted:
        raise ValueError(
            f"Memory {memory_id} not found."
        )

    return True


def update_memory(
    memory_id: int,
    content: str,
    memory_type: str = "note",
    importance: int = 1
):
    content = content.strip()

    if not content:
        raise ValueError("Memory content cannot be empty.")

    memory_type = _validate_memory_type(memory_type)
    importance = _validate_importance(importance)

    updated = update_stored_memory(
        memory_id,
        content,
        memory_type,
        importance
    )

    if not updated:
        raise ValueError(
            f"Memory {memory_id} not found."
        )

    return True
