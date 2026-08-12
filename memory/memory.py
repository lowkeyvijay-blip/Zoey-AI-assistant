from database.db import get_connection


MEMORY_TYPES = {
    "fact",
    "preference",
    "goal",
    "note"
}


def normalize(text: str) -> str:
    """
    Normalize memory text for basic duplicate detection.

    This handles obvious wording differences without
    requiring an AI/embedding call.
    """

    text = text.lower().strip()

    replacements = {
        "the user wants to ": "",
        "the user want to ": "",
        "i want to ": "",
        "i would like to ": "",
        "i'm building ": "building ",
        "i am building ": "building ",
        "my laptop has ": "laptop ",
        "my laptop contains ": "laptop ",
        "laptop with ": "laptop ",
    }

    for old, new in replacements.items():

        if text.startswith(old):
            text = new + text[len(old):]

    # Common equivalent expressions
    text = text.replace("16 gb", "16gb")
    text = text.replace("32 gb", "32gb")
    text = text.replace("64 gb", "64gb")

    text = text.replace("16 gigabytes", "16gb")
    text = text.replace("32 gigabytes", "32gb")
    text = text.replace("64 gigabytes", "64gb")

    # Normalize punctuation
    punctuation = ".,!?;:'\""

    for char in punctuation:
        text = text.replace(char, "")

    # Normalize whitespace
    text = " ".join(text.split())

    return text


def _exact_duplicate(
    connection,
    content: str
):
    """
    Check for an exact duplicate.
    """

    return connection.execute(
        """
        SELECT id
        FROM memories
        WHERE content = ?
        LIMIT 1
        """,
        (content,)
    ).fetchone()


def _normalized_duplicate(
    connection,
    content: str,
    memory_type: str
):
    """
    Check whether a memory becomes identical after
    normalization.
    """

    normalized_content = normalize(content)

    rows = connection.execute(
        """
        SELECT id, content
        FROM memories
        WHERE memory_type = ?
        """,
        (memory_type,)
    ).fetchall()

    for row in rows:

        existing_normalized = normalize(
            row["content"]
        )

        if existing_normalized == normalized_content:
            return row

    return None


def remember(
    content: str,
    memory_type: str = "note",
    importance: int = 1
):
    """
    Store a memory.

    Returns:
        True  -> memory was saved
        False -> memory already exists
    """

    content = content.strip()

    if not content:
        return False

    if memory_type not in MEMORY_TYPES:
        memory_type = "note"

    try:
        importance = int(importance)
    except (TypeError, ValueError):
        importance = 1

    importance = max(
        1,
        min(5, importance)
    )

    connection = get_connection()

    try:

        # -----------------------------------------
        # 1. Exact duplicate check
        # -----------------------------------------

        if _exact_duplicate(
            connection,
            content
        ):
            return False

        # -----------------------------------------
        # 2. Normalized duplicate check
        # -----------------------------------------

        if _normalized_duplicate(
            connection,
            content,
            memory_type
        ):
            return False

        # -----------------------------------------
        # 3. Save memory
        # -----------------------------------------

        connection.execute(
            """
            INSERT INTO memories (
                content,
                memory_type,
                importance
            )
            VALUES (?, ?, ?)
            """,
            (
                content,
                memory_type,
                importance
            )
        )

        connection.commit()

        return True

    finally:
        connection.close()


def recall(
    limit: int = 10,
    memory_type: str | None = None
):
    """
    Retrieve memories.

    If memory_type is provided, only memories
    of that type are returned.
    """

    connection = get_connection()

    try:

        if memory_type is not None:

            if memory_type not in MEMORY_TYPES:
                return []

            rows = connection.execute(
                """
                SELECT
                    id,
                    content,
                    memory_type,
                    importance,
                    created_at
                FROM memories
                WHERE memory_type = ?
                ORDER BY importance DESC, id DESC
                LIMIT ?
                """,
                (
                    memory_type,
                    limit
                )
            ).fetchall()

        else:

            rows = connection.execute(
                """
                SELECT
                    id,
                    content,
                    memory_type,
                    importance,
                    created_at
                FROM memories
                ORDER BY importance DESC, id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return rows

    finally:
        connection.close()


def get_by_type(
    memory_type: str,
    limit: int = 10
):
    """
    Convenience function for retrieving one
    specific memory category.
    """

    return recall(
        limit=limit,
        memory_type=memory_type
    )


def count_memories():
    """
    Return the total number of stored memories.
    """

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM memories
            """
        ).fetchone()

        return row["count"]

    finally:
        connection.close()


def delete_memory(memory_id: int):
    """
    Delete a memory by its database ID.

    Returns:
        True  -> deleted
        False -> memory didn't exist
    """

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            DELETE FROM memories
            WHERE id = ?
            """,
            (memory_id,)
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


def update_memory(
    memory_id: int,
    content: str,
    memory_type: str = "note",
    importance: int = 1
):
    """
    Update a memory by its database ID.

    Returns:
        True  -> updated
        False -> memory didn't exist
    """

    content = content.strip()

    if not content:
        return False

    if memory_type not in MEMORY_TYPES:
        memory_type = "note"

    try:
        importance = int(importance)
    except (TypeError, ValueError):
        importance = 1

    importance = max(
        1,
        min(5, importance)
    )

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            UPDATE memories
            SET
                content = ?,
                memory_type = ?,
                importance = ?
            WHERE id = ?
            """,
            (
                content,
                memory_type,
                importance,
                memory_id
            )
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


def clear_memories():
    """
    Delete ALL memories.

    Use carefully.
    """

    connection = get_connection()

    try:

        connection.execute(
            "DELETE FROM memories"
        )

        connection.commit()

    finally:
        connection.close()


def search_memories(
    query: str,
    limit: int = 5
):
    stop_words = {
        "i", "me", "my", "mine", "the", "a", "an",
        "is", "are", "am", "was", "were", "do",
        "does", "did", "have", "has", "had",
        "what", "when", "where", "who", "why",
        "how", "can", "could", "would", "should",
        "to", "of", "in", "on", "at", "for",
        "and", "or", "but", "with", "about",
        "your", "you", "user"
    }

    query_words = {
        word
        for word in normalize(query).split()
        if word not in stop_words
        and len(word) > 2
    }

    if not query_words:
        return []

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                id,
                content,
                memory_type,
                importance,
                created_at
            FROM memories
            """
        ).fetchall()

        scored = []

        for row in rows:

            memory_words = {
                word
                for word in normalize(
                    row["content"]
                ).split()
                if word not in stop_words
                and len(word) > 2
            }

            overlap = query_words.intersection(
                memory_words
            )

            if not overlap:
                continue

            score = len(overlap)

            # Small importance boost
            score += row["importance"] * 0.1

            scored.append(
                (
                    score,
                    row
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            row
            for score, row in scored[:limit]
        ]

    finally:
        connection.close()