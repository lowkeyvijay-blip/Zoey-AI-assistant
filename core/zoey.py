import json
import urllib.request

from database.db import initialize_database
from core.orchestrator import Orchestrator
from memory.memory import (
    remember,
    recall,
    get_by_type,
    search_memories,
)


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"
KEEP_ALIVE = "30m"
MAX_RESPONSE_TOKENS = 512


class Zoey:

    def __init__(self, orchestrator=None):
        initialize_database()
        self.orchestrator = (
            orchestrator if orchestrator is not None else Orchestrator()
        )

    # --------------------------------------------------
    # BASIC AI
    # --------------------------------------------------

    def _generate(self, prompt: str):

        payload = json.dumps({
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "num_predict": MAX_RESPONSE_TOKENS,
        }).encode("utf-8")

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
    # MEMORY CLASSIFICATION
    # --------------------------------------------------

    def analyze_memory(self, message: str):

        prompt = f"""
You are the memory classifier for Zoey,
a personal AI assistant.

Analyze the user's message.

Decide whether it contains information worth
remembering for future conversations.

Allowed memory types:

fact
preference
goal
note
none

Definitions:

fact:
A stable factual detail about the user,
their devices, projects, environment, etc.

preference:
Something the user likes, dislikes,
or prefers.

goal:
Something the user wants to achieve,
build, finish, or obtain.

note:
Useful contextual information that may
matter later.

none:
Normal conversation, questions,
calculations, greetings, or temporary
information.

Rules:

- "I want to..." is usually a goal.
- "I prefer..." is usually a preference.
- Hardware specifications are facts.
- Questions are normally none.
- Do not invent information.
- Rewrite the memory as a clean statement.
- Return ONLY valid JSON.

Example:

User:
"I have 16GB RAM in my laptop."

Return:

{{
    "remember": true,
    "type": "fact",
    "content": "The user's laptop has 16GB RAM",
    "importance": 3
}}

User:
"I want to build my own Jarvis."

Return:

{{
    "remember": true,
    "type": "goal",
    "content": "The user wants to build their own Jarvis AI assistant",
    "importance": 5
}}

User:
"What's 2 + 2?"

Return:

{{
    "remember": false,
    "type": "none",
    "content": "",
    "importance": 1
}}

USER MESSAGE:
{message}
""".strip()

        try:

            response = self._generate(prompt).strip()

            if response.startswith("```"):
                response = response.replace(
                    "```json",
                    ""
                )
                response = response.replace(
                    "```",
                    ""
                )
                response = response.strip()

            result = json.loads(response)

            if not result.get("remember"):
                return None

            memory_type = result.get(
                "type",
                "note"
            )

            content = result.get(
                "content",
                ""
            ).strip()

            if not content:
                return None

            importance = result.get(
                "importance",
                1
            )

            try:
                importance = int(importance)
            except (TypeError, ValueError):
                importance = 1

            importance = max(
                1,
                min(5, importance)
            )

            return {
                "type": memory_type,
                "content": content,
                "importance": importance
            }

        except Exception:
            return None

    # --------------------------------------------------
    # SEMANTIC MEMORY DECISION
    # --------------------------------------------------

    def compare_memory(
        self,
        new_memory: dict
    ):
        """
        Ask the local LLM whether the new memory
        duplicates or updates an existing memory.
        """

        existing_memories = get_by_type(
            new_memory["type"],
            limit=20
        )

        if not existing_memories:
            return {
                "action": "save",
                "memory_id": None
            }

        memories_text = "\n".join(
            f"ID {memory['id']}: {memory['content']}"
            for memory in existing_memories
        )

        prompt = f"""
You are Zoey's memory manager.

Determine how a NEW memory relates to
EXISTING memories.

NEW MEMORY:

Type:
{new_memory["type"]}

Content:
{new_memory["content"]}

EXISTING MEMORIES:

{memories_text}

Choose exactly one action:

save
duplicate
update

Definitions:

save:
The new memory contains genuinely new information.

duplicate:
The new memory means essentially the same thing
as an existing memory.

update:
The new memory changes or replaces an existing
fact, preference, goal, or note.

Examples:

Existing:
"The user's laptop has 16GB RAM"

New:
"The user's laptop has 32GB RAM"

Result:

{{
    "action": "update",
    "memory_id": 12
}}

Existing:
"The user prefers working late at night"

New:
"The user likes working at night"

Result:

{{
    "action": "duplicate",
    "memory_id": 13
}}

Existing:
"The user owns a Hyundai Creta"

New:
"The user wants to build a Jarvis AI"

Result:

{{
    "action": "save",
    "memory_id": null
}}

Return ONLY valid JSON.

NEW MEMORY:
{new_memory["content"]}
""".strip()

        try:

            response = self._generate(prompt).strip()

            if response.startswith("```"):
                response = response.replace(
                    "```json",
                    ""
                )
                response = response.replace(
                    "```",
                    ""
                )
                response = response.strip()

            result = json.loads(response)

            action = result.get(
                "action",
                "save"
            )

            if action not in {
                "save",
                "duplicate",
                "update"
            }:
                action = "save"

            memory_id = result.get(
                "memory_id"
            )

            return {
                "action": action,
                "memory_id": memory_id
            }

        except Exception:

            # If the semantic comparison fails,
            # safely save rather than losing information.

            return {
                "action": "save",
                "memory_id": None
            }

    # --------------------------------------------------
    # MEMORY UPDATE
    # --------------------------------------------------

    def update_memory(
        self,
        memory_id: int,
        content: str,
        memory_type: str,
        importance: int
    ):

        from database.db import get_connection

        connection = get_connection()

        try:

            connection.execute(
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

            return True

        finally:
            connection.close()

    # --------------------------------------------------
    # REMEMBER
    # --------------------------------------------------

    def remember(
        self,
        information: str,
        memory_type: str = "note",
        importance: int = 1
    ):

        memory = {
            "type": memory_type,
            "content": information,
            "importance": importance
        }

        decision = self.compare_memory(
            memory
        )

        # ------------------------------------------
        # NEW MEMORY
        # ------------------------------------------

        if decision["action"] == "save":

            saved = remember(
                information,
                memory_type,
                importance
            )

            if saved:
                return "I'll remember that."

            return "I already remember that."

        # ------------------------------------------
        # DUPLICATE
        # ------------------------------------------

        if decision["action"] == "duplicate":

            return "I already remember that."

        # ------------------------------------------
        # UPDATE
        # ------------------------------------------

        if decision["action"] == "update":

            memory_id = decision.get(
                "memory_id"
            )

            if memory_id is not None:

                self.update_memory(
                    memory_id,
                    information,
                    memory_type,
                    importance
                )

                return "I'll update what I remember."

            # Safety fallback
            saved = remember(
                information,
                memory_type,
                importance
            )

            if saved:
                return "I'll remember that."

            return "I already remember that."

        return "I'll remember that."

    # --------------------------------------------------
    # RECALL
    # --------------------------------------------------

    def recall(self, limit: int = 10):

        memories = recall(limit)

        if not memories:
            return "I don't have anything stored yet."

        return "\n".join(
            f"- [{memory['memory_type']}] "
            f"{memory['content']}"
            for memory in memories
        )

    # --------------------------------------------------
# NORMAL RESPONSE
# --------------------------------------------------

    def get_relevant_context(
        self,
        message: str,
        limit: int = 5
    ):
        memories = search_memories(
            message,
            limit
        )

        if not memories:
            return ""

        return "\n".join(
            f"- [{memory['memory_type']}] "
            f"{memory['content']}"
            for memory in memories
        )

    def ask_ai(self, message: str):

        context = self.get_relevant_context(
            message
        )

        if context:

            memory_context = f"""
RELEVANT MEMORIES:

{context}
""".strip()

        else:

            memory_context = """
RELEVANT MEMORIES:

None.
""".strip()

        prompt = f"""
You are Zoey, the user's personal AI assistant.

IDENTITY:

- Your name is Zoey.
- You were created by the user.
- You are being developed as a personal JARVIS-style assistant.
- You run locally on the user's computer.
- Your purpose is to help the user plan, remember,
  research, build, automate, and manage tasks.

BEHAVIOR:

- Helpful
- Direct
- Calm
- Practical
- Concise
- Honest

IMPORTANT:

- Use relevant memories when they help answer the user.
- Do not mention the memory system unless asked.
- Never invent personal facts.
- Never assume a memory is relevant when it isn't.
- If the memories don't contain the answer,
  simply say what you know or don't know.
- Never claim to have performed an action unless
  a real tool performed it.

{memory_context}

USER:
{message}

ZOEY:
""".strip()

        try:

            return self._generate(prompt)

        except Exception as error:

            return (
                f"I couldn't reach my local AI brain: "
                f"{error}"
            )

    # --------------------------------------------------
    # GOAL RESPONSE
    # --------------------------------------------------

    def _format_goal_response(self, result):

        plan_text = self.orchestrator.planner.format_plan(
            result["plan"]
        )

        lines = [
            plan_text,
            "",
            "I've saved these as tasks:",
        ]

        for task in result.get("tasks", []):
            lines.append(f"- {task['title']}")

        return "\n".join(lines)

    # --------------------------------------------------
    # PENDING PLAN RESPONSE
    # --------------------------------------------------

    def _format_plan_pending_response(self, result):

        plan_text = self.orchestrator.planner.format_plan(
            result["plan"]
        )

        lines = [
            plan_text,
            "",
            "Should I add these as tasks?",
            "Reply yes to save them, or no to cancel.",
        ]

        return "\n".join(lines)

    # --------------------------------------------------
    # PLAN EXECUTION RESPONSE
    # --------------------------------------------------

    def _format_warnings(self, result):

        warnings = result.get("warnings") or []

        if not warnings:
            return ""

        lines = ["", "Note:"]

        for warning in warnings:

            step_number = warning.get("step_number")
            task_id = warning.get("task_id")
            error = warning.get("error", "Unknown error")

            lines.append(
                f"- Step {step_number} ran, but I couldn't "
                f"mark task {task_id} done: {error}"
            )

        return "\n".join(lines)

    def _format_plan_execution_response(self, result):

        lines = []

        for step in result.get("steps", []):

            title = step.get("title")
            status = step.get("status")

            if status == "completed":
                lines.append(f"- {title}: done")
            elif status == "not_auto":
                lines.append(
                    f"- {title}: no automated action"
                )
            elif status == "blocked":
                lines.append(f"- {title}: blocked")
            elif status == "cancelled":
                lines.append(f"- {title}: cancelled")
            elif status == "failed":
                error_result = step.get(
                    "result",
                    {}
                ) or {}
                lines.append(
                    f"- {title}: FAILED - "
                    + error_result.get(
                        "error",
                        "Unknown error"
                    )
                )
            else:
                lines.append(
                    f"- {title}: not run"
                )

        overall = result.get("status")

        if result.get("nothing_left"):

            base = (
                "There were no un-run steps left to run:\n"
                + "\n".join(lines)
            )

        elif result.get("restored") and overall == "failed":

            base = (
                "I continued the interrupted plan, but a "
                "step is still failed:\n"
                + "\n".join(lines)
            )

        elif result.get("restored"):

            base = (
                "I continued the interrupted plan:\n"
                + "\n".join(lines)
            )

        elif result.get("resumed") and overall == "failed":

            base = (
                "I resumed the plan, but a step is still "
                "failed:\n"
                + "\n".join(lines)
            )

        elif result.get("resumed"):

            base = (
                "I resumed the plan:\n"
                + "\n".join(lines)
            )

        elif overall == "failed":

            base = (
                "I stopped the plan because a step failed:\n"
                + "\n".join(lines)
            )

        elif overall == "blocked":

            base = (
                "I couldn't run some steps because they "
                "depend on steps that can't complete:\n"
                + "\n".join(lines)
            )

        elif overall == "cancelled":

            base = (
                "I stopped the plan. Completed work is kept:\n"
                + "\n".join(lines)
            )

        elif overall == "no_executable_steps":

            base = (
                "I saved the plan as tasks, but none of "
                "the steps map to actions I can run "
                "automatically.\n"
                + "\n".join(lines)
            )

        else:

            base = (
                "I executed the approved plan:\n"
                + "\n".join(lines)
            )

        warning_text = self._format_warnings(result)

        if warning_text:
            return base + "\n" + warning_text

        return base

    def _format_step_retried_response(self, result):

        number = result.get("retried_number")

        step = {}

        for candidate in result.get("steps", []):

            if candidate.get("number") == number:
                step = candidate
                break

        title = step.get("title")
        status = step.get("status")

        if status == "completed":
            base = (
                f"I retried step {number} ({title}): done."
            )
        elif status == "blocked":
            base = (
                f"I couldn't retry step {number} "
                f"({title}): its dependencies aren't met."
            )
        else:
            error_result = step.get("result") or {}
            base = (
                f"I retried step {number} ({title}) but it "
                f"failed again: "
                + error_result.get(
                    "error",
                    "Unknown error"
                )
            )

        warning_text = self._format_warnings(result)

        if warning_text:
            return base + "\n" + warning_text

        return base

    def _format_execution_cancelled_response(self, result):

        if result.get("status") == "cancelling":
            return (
                "I'll stop the plan between steps. "
                "Nothing further will run."
            )

        lines = []

        for step in result.get("steps", []):

            title = step.get("title")
            status = step.get("status")

            if status == "completed":
                lines.append(f"- {title}: done")
            elif status == "not_auto":
                lines.append(
                    f"- {title}: no automated action"
                )
            elif status == "cancelled":
                lines.append(f"- {title}: cancelled")
            else:
                lines.append(f"- {title}: not run")

        base = (
            "I stopped the plan. Completed work is kept:\n"
            + "\n".join(lines)
        )

        warning_text = self._format_warnings(result)

        if warning_text:
            return base + "\n" + warning_text

        return base

    def _format_execution_reset_response(self, result):
        return (
            "OK, the plan is reset and approved. "
            "Say 'execute the plan' to run it again."
        )

    def _format_execution_status_response(self, result):

        status = result.get("status")

        if status == "idle":
            return "There's no plan in progress right now."

        lines = [f"Plan status: {status}"]

        goal = result.get("goal")

        if goal:
            lines.append(f"Goal: {goal}")

        steps = result.get("steps") or []

        if steps:
            lines.append("Steps:")
            for step in steps:
                lines.append(
                    f"- Step {step.get('number')}: "
                    f"{step.get('title')} - "
                    f"{step.get('status')}"
                )
        else:
            lines.append("No steps recorded yet.")

        return "\n".join(lines)

    def _format_plan_list_response(self, result):

        runs = result.get("runs") or []

        if not runs:
            return "There are no saved plans."

        lines = ["Saved plans:"]

        for run in runs:
            lines.append(
                f"- Run {run.get('run_id')}: "
                f"{run.get('goal')} "
                f"[{run.get('status')}] "
                f"(created {run.get('created_at')})"
            )

        return "\n".join(lines)

    def _format_plan_discarded_response(self, result):

        goal = result.get("goal")

        if result.get("saved_run"):

            return (
                "OK, I discarded the plan and its saved "
                f"run: {goal}"
            )

        if goal:
            return "OK, I cleared the pending plan."

        return "OK, there's nothing to discard now."

    # --------------------------------------------------
    # MAIN RESPONSE LOOP
    # --------------------------------------------------

    def respond_structured(self, message: str):
        """Route a message and return a structured result dict.

        This mirrors respond() exactly but returns the raw dict the
        orchestrator produced (plus a simple "text" result for plain
        conversation) so the API layer can render rich cards. respond()
        delegates here and formats the result as plain text.
        """

        message = message.strip()

        if not message:
            return {
                "type": "text",
                "content": "I'm listening.",
            }

        lower_message = message.lower()

        # Explicit memory command
        if lower_message.startswith(
            "remember "
        ):

            information = message[9:].strip()

            if not information:
                return {
                    "type": "text",
                    "content": "What should I remember?",
                }

            return {
                "type": "text",
                "content": self.remember(
                    information,
                    "note",
                    5
                ),
            }

        # Recall command
        if lower_message in {
            "memory",
            "what do you remember?",
            "what do you remember",
            "show my memories"
        }:

            return {
                "type": "text",
                "content": self.recall(),
            }

        # Orchestrated routing
        result = self.orchestrator.handle(message)

        if result.get("type") in {
            "goal",
            "plan_pending",
            "plan_executed",
            "step_retried",
            "execution_cancelled",
            "execution_reset",
            "execution_status",
            "plan_list",
            "plan_discarded",
            "goal_rejected",
            "error",
        }:
            return result

        # Automatic memory detection: only for clearly memory-
        # like messages. Skip for conversation/tool intents so
        # those responses stay a single Ollama call.
        intent = result.get("intent")

        if intent == "memory":
            memory = self.analyze_memory(
                message
            )

            if memory:

                self.remember(
                    memory["content"],
                    memory["type"],
                    memory["importance"]
                )

        return {
            "type": "text",
            "content": self.ask_ai(message),
        }

    def format_result(self, result):
        """Format a structured result as plain text.

        This is the single dispatch used by respond(). Keeping it
        separate lets the API layer attach the same text to rich cards.
        """

        result_type = result.get("type")

        if result_type == "text":
            return result.get("content", "")

        if result_type == "goal":
            return self._format_goal_response(result)

        if result_type == "plan_pending":
            return self._format_plan_pending_response(result)

        if result_type == "plan_executed":
            return self._format_plan_execution_response(result)

        if result_type == "step_retried":
            return self._format_step_retried_response(result)

        if result_type == "execution_cancelled":
            return self._format_execution_cancelled_response(result)

        if result_type == "execution_reset":
            return self._format_execution_reset_response(result)

        if result_type == "execution_status":
            return self._format_execution_status_response(result)

        if result_type == "plan_list":
            return self._format_plan_list_response(result)

        if result_type == "plan_discarded":
            return self._format_plan_discarded_response(result)

        if result_type == "goal_rejected":
            return "OK, I won't add those tasks."

        if result_type == "error":
            return result.get(
                "error",
                "I couldn't process that."
            )

        return result.get(
            "content",
            "I couldn't process that."
        )

    def respond(self, message: str):

        result = self.respond_structured(message)

        return self.format_result(result)