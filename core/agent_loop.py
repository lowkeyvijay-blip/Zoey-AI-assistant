import json
import urllib.request

from core.tool_manager import execute_tool


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"
KEEP_ALIVE = "30m"
MAX_RESPONSE_TOKENS = 512


TOOLS = """
AVAILABLE TOOLS

1. list_apps
   Purpose: List applications Zoey is allowed to open
   or close.

Arguments:
{}

2. open_app
   Purpose: Open a Windows application.

Arguments:
{
    "app_name": "chrome" | "notepad" | "calculator"
}

3. close_app
   Purpose: Close one safely identified application
   instance that Zoey opened.

Arguments:
{
    "app_name": "chrome" | "notepad" | "calculator"
}

4. create_task
   Purpose: Create and permanently save a task.

Arguments:
{
    "title": "task title",
    "due_at": "date/time or null"
}

5. list_tasks
   Purpose: List the user's saved tasks.

Arguments:
{}

6. complete_task
   Purpose: Mark a task as completed.

Arguments:
{
    "task_id": integer
}

7. get_task
   Purpose: Get one saved task by its id.

Arguments:
{
    "task_id": integer
}

8. update_task
   Purpose: Update a task's title, due date, or status.
   Pass only the fields you want to change. A null
   due_at clears the due date.

Arguments:
{
    "task_id": integer,
    "title": "new title or omit",
    "due_at": "date/time, null to clear, or omit",
    "status": "pending" | "completed" or omit
}

9. delete_task
   Purpose: Delete a saved task permanently.

Arguments:
{
    "task_id": integer
}

10. remember
   Purpose: Save a new memory. A duplicate memory is
   reported but not saved twice.

Arguments:
{
    "content": "memory text",
    "memory_type": "fact" | "preference" | "goal" | "note",
    "importance": integer from 1 to 5
}

11. recall_memories
   Purpose: Retrieve stored memories, optionally of one
   type only.

Arguments:
{
    "memory_type": "fact" | "preference" | "goal" | "note" or omit,
    "limit": integer or omit
}

12. search_memories
    Purpose: Search stored memories by keywords.

Arguments:
{
    "query": "search text",
    "limit": integer or omit
}

13. forget
    Purpose: Delete one memory by its id. The id comes
    from recall_memories or search_memories.

Arguments:
{
    "memory_id": integer
}

14. update_memory
    Purpose: Update a stored memory's content, type, or
    importance.

Arguments:
{
    "memory_id": integer,
    "content": "new memory text",
    "memory_type": "fact" | "preference" | "goal" | "note" or omit,
    "importance": integer from 1 to 5 or omit
}

15. list_dir
    Purpose: List files and folders inside Zoey's file
    sandbox.

Arguments:
{
    "path": "relative path inside the file sandbox"
}

16. read_file
    Purpose: Read a UTF-8 text file inside Zoey's file
    sandbox.

Arguments:
{
    "path": "relative path inside the file sandbox"
}

17. write_file
    Purpose: Write a UTF-8 text file inside Zoey's file
    sandbox.

Arguments:
{
    "path": "relative path inside the file sandbox",
    "content": "file content"
}

18. append_file
    Purpose: Append text to a UTF-8 text file inside
    Zoey's file sandbox.

Arguments:
{
    "path": "relative path inside the file sandbox",
    "content": "text to append"
}

19. delete_file
    Purpose: Delete a file inside Zoey's file sandbox.

Arguments:
{
    "path": "relative path inside the file sandbox"
}

20. file_info
    Purpose: Get metadata for a file or folder inside
    Zoey's file sandbox.

Arguments:
{
    "path": "relative path inside the file sandbox"
}

21. add_event
    Purpose: Add a local calendar event.

Arguments:
{
    "title": "event title",
    "start_at": "ISO 8601 datetime",
    "end_at": "ISO 8601 datetime",
    "location": "location or null",
    "notes": "notes or null"
}

22. list_events
    Purpose: List local calendar events, optionally within a time window.

Arguments:
{
    "start_at": "ISO 8601 datetime or null",
    "end_at": "ISO 8601 datetime or null",
    "limit": integer
}

23. upcoming_events
    Purpose: List the next local calendar events.

Arguments:
{
    "limit": integer
}

24. update_event
    Purpose: Update a local calendar event. Pass only fields to change.

Arguments:
{
    "event_id": integer,
    "title": "new title or omit",
    "start_at": "ISO 8601 datetime or omit",
    "end_at": "ISO 8601 datetime or omit",
    "location": "location, null to clear, or omit",
    "notes": "notes, null to clear, or omit"
}

25. delete_event
    Purpose: Permanently delete a local calendar event.

Arguments:
{
    "event_id": integer
}

26. open_url
    Purpose: Open an HTTP(S) URL in the default browser.

Arguments:
{
    "url": "http:// or https:// URL"
}

27. fetch_url
    Purpose: Fetch bounded HTTP(S) text without JavaScript or cookies.

Arguments:
{
    "url": "http:// or https:// URL",
    "max_chars": integer or omit
}

28. notify
    Purpose: Show a local Windows notification.

Arguments:
{
    "title": "notification title",
    "message": "notification message"
}

29. notifications_log
    Purpose: Read recent notifications sent by Zoey.

Arguments:
{
    "limit": integer or omit
}
"""


ALLOWED_TOOLS = {
    "list_apps",
    "open_app",
    "close_app",
    "create_task",
    "list_tasks",
    "complete_task",
    "get_task",
    "update_task",
    "delete_task",
    "remember",
    "recall_memories",
    "search_memories",
    "forget",
    "update_memory",
    "list_dir",
    "read_file",
    "write_file",
    "append_file",
    "delete_file",
    "file_info",
    "add_event",
    "list_events",
    "upcoming_events",
    "update_event",
    "delete_event",
    "open_url",
    "fetch_url",
    "notify",
    "notifications_log",
}


class AgentLoop:

    # --------------------------------------------------
    # MODEL
    # --------------------------------------------------

    def ask_model(self, prompt: str, json_mode: bool = False):

        payload_data = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "num_predict": MAX_RESPONSE_TOKENS,
        }

        if json_mode:
            payload_data["format"] = "json"

        payload = json.dumps(payload_data).encode("utf-8")

        request = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        return data.get("response", "")

    # --------------------------------------------------
    # DECISION
    # --------------------------------------------------

    def decide(self, user_message: str):

        prompt = f"""
You are Zoey, a personal AI assistant.

{TOOLS}

Determine what actions are required for the user's request.

IMPORTANT:

A user request may require ZERO, ONE, or MULTIPLE tools.

If multiple actions are requested, return ALL required
tool calls in the correct order.

Examples:

User:
"Open Notepad and create a task called Work on Zoey"

Return:

{{
    "type": "tool_calls",
    "calls": [
        {{
            "tool": "open_app",
            "arguments": {{
                "app_name": "notepad"
            }}
        }},
        {{
            "tool": "create_task",
            "arguments": {{
                "title": "Work on Zoey",
                "due_at": null
            }}
        }}
    ]
}}

User:
"Show me my tasks and complete task 16"

Return:

{{
    "type": "tool_calls",
    "calls": [
        {{
            "tool": "list_tasks",
            "arguments": {{}}
        }},
        {{
            "tool": "complete_task",
            "arguments": {{
                "task_id": 16
            }}
        }}
    ]
}}

User:
"Open Notepad"

Return:

{{
    "type": "tool_calls",
    "calls": [
        {{
            "tool": "open_app",
            "arguments": {{
                "app_name": "notepad"
            }}
        }}
    ]
}}

If the user does NOT need a tool, return:

{{
    "type": "response",
    "content": "answer"
}}

RULES:

- Never invent tools.
- Only use tools listed above.
- Use exact tool names.
- Arguments must be valid JSON.
- Do not put explanations outside the JSON.
- Return ONLY valid JSON.

USER:
{user_message}
""".strip()

        raw = self.ask_model(
            prompt,
            json_mode=True
        )

        try:

            result = json.loads(raw)

            # --------------------------------------------------
            # NORMAL RESPONSE
            # --------------------------------------------------

            if result.get("type") == "response":
                return result

            # --------------------------------------------------
            # MULTIPLE TOOL CALLS
            # --------------------------------------------------

            if result.get("type") == "tool_calls":

                calls = result.get("calls", [])

                if not isinstance(calls, list):
                    return {
                        "type": "response",
                        "content": "I couldn't understand that request."
                    }

                return {
                    "type": "tool_calls",
                    "calls": calls
                }

            # --------------------------------------------------
            # BACKWARDS COMPATIBILITY
            # --------------------------------------------------

            if result.get("type") == "tool_call":

                return {
                    "type": "tool_calls",
                    "calls": [
                        {
                            "tool": result.get("tool"),
                            "arguments": result.get(
                                "arguments",
                                {}
                            )
                        }
                    ]
                }

            return {
                "type": "response",
                "content": "I couldn't understand that request."
            }

        except json.JSONDecodeError:

            return {
                "type": "response",
                "content": raw
            }

    # --------------------------------------------------
    # EXECUTE ONE TOOL
    # --------------------------------------------------

    def execute_one(self, tool_name: str, arguments: dict):

        if tool_name not in ALLOWED_TOOLS:

            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not allowed."
            }

        if not isinstance(arguments, dict):

            return {
                "success": False,
                "error": "Tool arguments must be an object."
            }

        try:

            return execute_tool(
                tool_name,
                arguments
            )

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }

    # --------------------------------------------------
    # EXECUTE MULTIPLE TOOLS
    # --------------------------------------------------

    def execute(self, decision):

        if decision.get("type") != "tool_calls":
            return decision

        calls = decision.get("calls", [])

        if not isinstance(calls, list):
            return {
                "success": False,
                "error": "Invalid tool call list."
            }

        results = []

        for call in calls:

            if not isinstance(call, dict):

                results.append({
                    "success": False,
                    "error": "Invalid tool call."
                })

                continue

            tool_name = call.get("tool")

            arguments = call.get(
                "arguments",
                {}
            )

            result = self.execute_one(
                tool_name,
                arguments
            )

            results.append({
                "tool": tool_name,
                "arguments": arguments,
                "result": result
            })

            # Stop if a tool fails.
            #
            # This prevents Zoey from continuing a chain
            # when an earlier action failed.
            if not result.get("success", False):
                break

        return {
            "success": all(
                item["result"].get("success", False)
                for item in results
            ),
            "results": results
        }

    # --------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------

    def respond_after_tools(
        self,
        user_message,
        tool_results
    ):

        prompt = f"""
You are Zoey, a personal AI assistant.

The user said:

{user_message}

You executed the requested actions.

RESULTS:

{json.dumps(tool_results, indent=2)}

Respond naturally to the user.

IMPORTANT:

- Only describe what the results confirm.
- Never claim an action succeeded if it failed.
- Do not mention JSON.
- Do not mention internal tools.
- Do not mention internal architecture.
- Do not invent information.
- If several actions happened, summarize them clearly.
- Keep the response concise.
""".strip()

        return {
            "type": "response",
            "content": self.ask_model(
                prompt,
                json_mode=False
            )
        }

    # --------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------

    def run(self, user_message: str):

        decision = self.decide(
            user_message
        )

        # --------------------------------------------------
        # NORMAL CONVERSATION
        # --------------------------------------------------

        if decision.get("type") == "response":

            return decision

        # --------------------------------------------------
        # TOOL EXECUTION
        # --------------------------------------------------

        execution = self.execute(
            decision
        )

        if not execution.get("success", False):

            return {
                "type": "response",
                "content": (
                    "The action failed: "
                    + self._format_errors(execution)
                )
            }

        # --------------------------------------------------
        # FINAL AI RESPONSE
        # --------------------------------------------------

        return self.respond_after_tools(
            user_message,
            execution["results"]
        )

    # --------------------------------------------------
    # ERROR FORMATTER
    # --------------------------------------------------

    def _format_errors(self, execution):

        errors = []

        for item in execution.get(
            "results",
            []
        ):

            result = item.get(
                "result",
                {}
            )

            if not result.get(
                "success",
                False
            ):

                errors.append(
                    result.get(
                        "error",
                        "Unknown error"
                    )
                )

        if errors:
            return "; ".join(errors)

        return "Unknown error"

