import json
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

INTENTS = {
    "goal",
    "conversation",
    "memory",
    "tool",
}


class IntentClassifier:

    def __init__(
        self,
        threshold: float = 0.7
    ):
        self.threshold = threshold

    # --------------------------------------------------
    # LOCAL AI
    # --------------------------------------------------

    def _generate(self, prompt: str):

        payload = json.dumps({
            "model": MODEL,
            "prompt": prompt,
            "stream": False
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
    # PROMPT
    # --------------------------------------------------

    def _prompt(self, message: str):

        return f"""
You are Zoey's intent classifier.

Decide whether the user's message is a GOAL
or not, using this decision procedure:

1. If the user states or asks for help with
   something they want to achieve over time -
   finish, build, complete, prepare, study,
   learn, improve, start, create - classify
   as goal.

2. If the user asks a question or makes small
   talk - classify as conversation.

3. If the user states a fact or preference
   about themselves - classify as memory.

4. If the user orders an immediate action
   (open an app, run something now) -
   classify as tool.

5. If you cannot decide, choose conversation.

Strong goal signals - phrases that indicate a goal:

- "I want to..."
- "I need to..."
- "Help me..."
- "I'm planning to..."
- "I'm trying to..."
- "I'd like to..."

Examples:

"I want to finish Zoey today." -> goal
"I need to build a website for a client." -> goal
"Help me prepare for tomorrow's exam." -> goal
"I'm planning to learn Python." -> goal
"I'd like to start a garden." -> goal

"What's the capital of France?" -> conversation
"Tell me a joke." -> conversation
"Who are you?" -> conversation

"Remember that I prefer working at night." -> memory
"I prefer working at night." -> memory
"My laptop has 16GB RAM." -> memory

"Open Notepad." -> tool
"Open Chrome." -> tool

When the intent is goal, rewrite the goal as a
short clean statement, for example:

"I want to finish Zoey today." becomes
"Finish Zoey today"

"Help me prepare for tomorrow's exam." becomes
"Prepare for tomorrow's exam"

Confidence: a number from 0 to 1. Ambiguous
messages MUST have confidence below 0.7.

Return ONLY valid JSON, exactly:

{{
    "intent": "goal | conversation | memory | tool",
    "goal": "cleaned goal or null",
    "confidence": 0.0
}}

USER MESSAGE:
{message}
""".strip()

    # --------------------------------------------------
    # CLASSIFY
    # --------------------------------------------------

    def classify(self, message: str):

        result = {
            "intent": "conversation",
            "goal": None,
            "confidence": 0.0,
        }

        if not isinstance(message, str):
            return result

        if not message.strip():
            return result

        try:

            raw = self._generate(
                self._prompt(message)
            ).strip()

            if raw.startswith("```"):

                raw = raw.replace(
                    "```json",
                    ""
                )

                raw = raw.replace(
                    "```",
                    ""
                )

                raw = raw.strip()

            data = json.loads(raw)

            if not isinstance(data, dict):
                return result

            intent = str(
                data.get(
                    "intent",
                    "conversation"
                )
            ).strip().lower()

            if intent not in INTENTS:
                intent = "conversation"

            goal = data.get(
                "goal",
                None
            )

            if isinstance(goal, str):
                goal = goal.strip()
                if goal.lower() == "null":
                    goal = None
                elif not goal:
                    goal = None
            else:
                goal = None

            try:
                confidence = float(
                    data.get(
                        "confidence",
                        0.0
                    )
                )
            except (TypeError, ValueError):
                confidence = 0.0

            confidence = max(
                0.0,
                min(1.0, confidence)
            )

            result = {
                "intent": intent,
                "goal": goal,
                "confidence": confidence,
            }

            # Confidence is the safety mechanism.
            # Anything below threshold stays conversation.

            if intent == "goal":

                if confidence < self.threshold:
                    result["intent"] = "conversation"
                    result["goal"] = None

                elif not goal:
                    result["intent"] = "conversation"

            return result

        except Exception:

            # Any failure safely falls back to
            # normal conversation.

            return result
