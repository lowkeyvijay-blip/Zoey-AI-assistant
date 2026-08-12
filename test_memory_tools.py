import uuid

from database.db import get_connection
from core.tool_manager import (
    TOOLS,
    execute_tool,
    available_tools,
)
from core.agent_loop import ALLOWED_TOOLS
from core.step_validation import (
    TOOL_ARGUMENT_RULES,
    validate_step,
)
from tools.memory_tools import (
    remember,
    recall_memories,
    search_memories,
    forget,
    update_memory,
)

import core.agent_loop as agent_loop_module


PREFIX = "Phase 10.2"


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def unique_content(label: str) -> str:
    return f"{PREFIX} {label} {uuid.uuid4().hex[:8]}"


def count_rows(content: str) -> int:
    connection = get_connection()

    row = connection.execute(
        "SELECT COUNT(*) AS n FROM memories WHERE content = ?",
        (content,)
    ).fetchone()

    connection.close()

    return row["n"]


def delete_by_prefix():
    connection = get_connection()

    connection.execute(
        "DELETE FROM memories WHERE content LIKE ?",
        (f"{PREFIX}%",)
    )

    connection.commit()
    connection.close()


def main():
    print("\nPHASE 10.2 TEST: MEMORY MANAGEMENT TOOLS\n")
    print("=" * 60)

    created_ids = []

    try:

        print("\nTEST A: FOUR-WAY REGISTRATION SYNC")

        memory_tools = {
            "remember",
            "recall_memories",
            "search_memories",
            "forget",
            "update_memory",
        }

        verify(
            memory_tools.issubset(TOOLS),
            "all memory tools are in the tool registry"
        )
        verify(
            memory_tools.issubset(ALLOWED_TOOLS),
            "all memory tools are in ALLOWED_TOOLS"
        )
        verify(
            all(
                name in TOOL_ARGUMENT_RULES
                for name in memory_tools
            ),
            "all memory tools have argument rules"
        )
        verify(
            all(
                name in agent_loop_module.TOOLS
                for name in memory_tools
            ),
            "all memory tools are documented in the LLM prompt"
        )
        verify(
            set(available_tools()) == set(TOOLS.keys()),
            "available_tools matches the registry"
        )
        verify(
            ALLOWED_TOOLS == set(TOOLS.keys()),
            "ALLOWED_TOOLS exactly matches the registry"
        )

        print("\nTEST B: REMEMBER")

        content = unique_content("remember")
        result = remember(content)
        verify(
            result.get("saved") is True,
            "remember saves a new memory"
        )

        result = remember(content)
        verify(
            result.get("saved") is False,
            "an exact duplicate is reported and not saved twice"
        )
        verify(
            count_rows(content) == 1,
            "the exact duplicate did not create a second row"
        )

        normalized = unique_content("normalized")
        verify(
            remember(normalized).get("saved") is True,
            "the original normalized memory is saved"
        )
        result = remember(
            normalized.upper() + "!"
        )
        verify(
            result.get("saved") is False,
            "a punctuation/case variant is detected as a duplicate"
        )
        verify(
            count_rows(normalized) == 1,
            "the normalized duplicate did not create a second row"
        )

        try:
            remember("   ")
        except ValueError:
            verify(True, "remember rejects empty content")
        else:
            raise AssertionError(
                "FAIL: remember should reject empty content"
            )

        try:
            remember("x", memory_type="bogus")
        except ValueError:
            verify(True, "remember rejects an invalid memory type")
        else:
            raise AssertionError(
                "FAIL: remember should reject an invalid type"
            )

        for bad in (0, 6, "high"):
            try:
                remember("x", importance=bad)
            except ValueError:
                verify(True, f"remember rejects importance={bad!r}")
            else:
                raise AssertionError(
                    f"FAIL: remember should reject importance={bad!r}"
                )

        print("\nTEST C: RECALL_MEMORIES")

        fact_content = unique_content("recall-fact")
        remember(fact_content, memory_type="fact", importance=3)

        rows = recall_memories()
        verify(
            isinstance(rows, list),
            "recall_memories returns a list"
        )
        verify(
            any(row["content"] == fact_content for row in rows),
            "recall_memories includes the stored memory"
        )

        fact_rows = recall_memories(memory_type="fact")
        verify(
            all(
                row["memory_type"] == "fact"
                for row in fact_rows
            ),
            "recall_memories filters by type"
        )
        verify(
            any(row["content"] == fact_content for row in fact_rows),
            "the fact filter includes the stored fact"
        )

        remembered = recall_memories(limit=1)
        verify(
            len(remembered) <= 1,
            "recall_memories honors the limit"
        )

        try:
            recall_memories(memory_type="bogus")
        except ValueError:
            verify(True, "recall_memories rejects an invalid type")
        else:
            raise AssertionError(
                "FAIL: recall_memories should reject an invalid type"
            )

        try:
            recall_memories(limit=0)
        except ValueError:
            verify(True, "recall_memories rejects a zero limit")
        else:
            raise AssertionError(
                "FAIL: recall_memories should reject a zero limit"
            )

        print("\nTEST D: SEARCH_MEMORIES")

        search_token = unique_content("search")
        remember(search_token, memory_type="note", importance=2)

        hits = search_memories(search_token)
        verify(
            any(row["content"] == search_token for row in hits),
            "search_memories finds the stored memory by keyword"
        )

        hits = search_memories(search_token, limit=1)
        verify(
            len(hits) <= 1,
            "search_memories honors the limit"
        )

        try:
            search_memories("")
        except ValueError:
            verify(True, "search_memories rejects an empty query")
        else:
            raise AssertionError(
                "FAIL: search_memories should reject an empty query"
            )

        try:
            search_memories("x", limit=0)
        except ValueError:
            verify(True, "search_memories rejects a zero limit")
        else:
            raise AssertionError(
                "FAIL: search_memories should reject a zero limit"
            )

        print("\nTEST E: UPDATE_MEMORY")

        update_content = unique_content("update-original")
        remember(
            update_content,
            memory_type="note",
            importance=1,
        )
        update_id = next(
            row["id"]
            for row in search_memories(update_content)
            if row["content"] == update_content
        )

        new_content = unique_content("update-new")
        verify(
            update_memory(
                update_id,
                new_content,
                memory_type="fact",
                importance=5,
            ) is True,
            "update_memory returns True on success"
        )
        verify(
            any(
                row["content"] == new_content
                for row in search_memories(new_content)
            ),
            "search finds the updated content"
        )
        verify(
            not any(
                row["content"] == update_content
                for row in search_memories(update_content)
            ),
            "the old content no longer matches"
        )
        fact_rows = recall_memories(memory_type="fact")
        verify(
            any(row["content"] == new_content for row in fact_rows),
            "the updated memory_type is applied"
        )

        updated_row = next(
            row
            for row in search_memories(new_content)
            if row["content"] == new_content
        )
        verify(
            updated_row["importance"] == 5,
            "the updated importance is applied"
        )

        try:
            update_memory(999999, "x")
        except ValueError:
            verify(True, "update_memory on a missing id raises")
        else:
            raise AssertionError(
                "FAIL: update_memory should raise on a missing id"
            )

        try:
            update_memory(update_id, "   ")
        except ValueError:
            verify(True, "update_memory rejects empty content")
        else:
            raise AssertionError(
                "FAIL: update_memory should reject empty content"
            )

        print("\nTEST F: FORGET (ID-BASED ONLY)")

        forget_content = unique_content("forget")
        remember(forget_content)
        forget_id = next(
            row["id"]
            for row in search_memories(forget_content)
            if row["content"] == forget_content
        )

        verify(
            forget(forget_id) is True,
            "forget deletes a memory by its id"
        )
        verify(
            not any(
                row["content"] == forget_content
                for row in search_memories(forget_content)
            ),
            "the forgotten memory is no longer found"
        )
        verify(
            not any(
                row["content"] == forget_content
                for row in recall_memories()
            ),
            "the forgotten memory is no longer recalled"
        )

        try:
            forget(forget_id)
        except ValueError:
            verify(True, "forget on a missing id raises")
        else:
            raise AssertionError(
                "FAIL: forget should raise on a missing id"
            )

        result = execute_tool("forget", {"content": "anything"})
        verify(
            result.get("success") is False,
            "forget does not support content-based deletion"
        )

        print("\nTEST G: TOOL PIPELINE (execute_tool)")

        pipe_content = unique_content("pipeline")
        result = execute_tool("remember", {"content": pipe_content})
        verify(
            result.get("success") is True,
            "execute_tool(remember) reports success"
        )
        verify(
            result["result"]["saved"] is True,
            "execute_tool(remember) reports the memory was saved"
        )

        result = execute_tool(
            "remember",
            {"content": pipe_content},
        )
        verify(
            result.get("success") is True
            and result["result"]["saved"] is False,
            "execute_tool(remember) reports a duplicate"
        )

        pipe_id = next(
            row["id"]
            for row in search_memories(pipe_content)
            if row["content"] == pipe_content
        )

        result = execute_tool("recall_memories", {})
        verify(
            result.get("success") is True,
            "execute_tool(recall_memories) reports success"
        )

        result = execute_tool(
            "search_memories",
            {"query": pipe_content},
        )
        verify(
            result.get("success") is True,
            "execute_tool(search_memories) reports success"
        )

        result = execute_tool(
            "update_memory",
            {"memory_id": pipe_id, "content": "updated " + pipe_content},
        )
        verify(
            result.get("success") is True,
            "execute_tool(update_memory) reports success"
        )

        result = execute_tool(
            "forget",
            {"memory_id": pipe_id},
        )
        verify(
            result.get("success") is True,
            "execute_tool(forget) reports success"
        )

        result = execute_tool("update_memory", {"memory_id": 999999, "content": "x"})
        verify(
            result.get("success") is False,
            "execute_tool(update_memory) fails cleanly on a missing id"
        )

        result = execute_tool("forget", {"memory_id": 999999})
        verify(
            result.get("success") is False,
            "execute_tool(forget) fails cleanly on a missing id"
        )

        result = execute_tool("remember", {"content": "x", "importance": 9})
        verify(
            result.get("success") is False,
            "execute_tool(remember) rejects an out-of-range importance"
        )

        print("\nTEST H: STEP VALIDATION")

        cases_valid = [
            ("remember", {"content": "x"}),
            ("remember", {"content": "x", "memory_type": "fact", "importance": 3}),
            ("recall_memories", {}),
            ("recall_memories", {"memory_type": "goal", "limit": 5}),
            ("search_memories", {"query": "x"}),
            ("search_memories", {"query": "x", "limit": 2}),
            ("forget", {"memory_id": 5}),
            ("update_memory", {"memory_id": 5, "content": "x"}),
            ("update_memory", {"memory_id": 5, "content": "x", "importance": 4}),
        ]

        for tool, arguments in cases_valid:
            result = validate_step({
                "number": 1,
                "title": tool,
                "tool": tool,
                "arguments": arguments,
            })
            verify(
                result["valid"],
                f"'{tool}' with {arguments!r} validates"
            )

        cases_invalid = [
            ("remember", {}, "requires 'content'"),
            ("remember", {"content": 5}, "must be a string"),
            ("search_memories", {}, "requires 'query'"),
            ("forget", {}, "requires 'memory_id'"),
            ("forget", {"memory_id": "5"}, "must be an integer"),
            ("update_memory", {}, "requires 'memory_id'"),
            ("update_memory", {"memory_id": 5}, "requires 'content'"),
            ("update_memory", {"memory_id": "5", "content": "x"}, "must be an integer"),
        ]

        for tool, arguments, expected in cases_invalid:
            result = validate_step({
                "number": 1,
                "title": tool,
                "tool": tool,
                "arguments": arguments,
            })
            verify(
                not result["valid"],
                f"'{tool}' with {arguments!r} is invalid"
            )
            verify(
                expected in result["error"],
                f"the '{tool}' error mentions: {expected}"
            )

        print("\n" + "=" * 60)
        print("PHASE 10.2 TESTS PASSED")

    finally:

        for memory_id in created_ids:
            from memory.memory import delete_memory
            delete_memory(memory_id)

        delete_by_prefix()

        print("\nCLEANUP: removed all Phase 10.2 memory rows")


if __name__ == "__main__":
    main()
