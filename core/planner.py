import json
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"


class Planner:

    def __init__(self):
        pass

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
    # CREATE PLAN
    # --------------------------------------------------

    def create_plan(self, goal: str):

        goal = goal.strip()

        if not goal:
            return self._fallback_plan(
                "No goal provided"
            )

        prompt = f"""
You are Zoey's planning engine.

Convert the user's goal into a practical execution plan.

Every step must be a REAL ACTION that moves the user
toward completing the goal.

NEVER include internal planning actions such as:

- reviewing the goal
- studying instructions
- determining status
- breaking the goal into steps
- prioritizing the plan
- reviewing the plan
- presenting the plan

CRITICAL FACTUALITY RULES:

- Never invent an industry.
- Never invent a client type.
- Never invent technology.
- Never invent a platform.
- Never invent a deadline.
- Never invent a budget.
- Never invent requirements.
- Only use information explicitly present in the goal.
- If information is missing, keep the step generic.
- Do not claim that anything is already completed.

PLANNING RULES:

- Generate 4-8 actionable steps.
- Steps must be concrete.
- Steps must be ordered logically.
- Each step must produce real progress.
- Do not include meta-planning steps.
- Keep steps concise.
- Return ONLY valid JSON.

Example:

Goal:
"I want to build a website for a client."

Good plan:

1. Gather the client's requirements
2. Define the website structure and required pages
3. Design the website
4. Build the website
5. Add the required content and functionality
6. Test the website
7. Fix issues found during testing
8. Deploy the website

Goal:
"I want to finish Zoey today."

Good plan:

1. Review Zoey's current functionality
2. Test the memory system
3. Test the agent and tool execution system
4. Test the planning system
5. Fix remaining errors
6. Run an end-to-end test
7. Verify the final system works correctly

IMPORTANT:

Do not assume specific unfinished features.
Only use information explicitly provided by the user.

Return exactly:

{{
    "goal": "{goal}",
    "steps": [
        {{
            "number": 1,
            "title": "Short actionable step",
            "description": "Concrete action that needs to be performed."
        }}
    ]
}}

USER GOAL:

{goal}
""".strip()

        try:

            raw = self._generate(
                prompt
            ).strip()

            # Remove markdown code fences
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

            result = json.loads(raw)

            if not isinstance(result, dict):

                return self._fallback_plan(
                    goal
                )

            steps = result.get(
                "steps",
                []
            )

            if not isinstance(steps, list):

                return self._fallback_plan(
                    goal
                )

            cleaned_steps = []

            for step in steps:

                if not isinstance(step, dict):
                    continue

                title = str(
                    step.get(
                        "title",
                        ""
                    )
                ).strip()

                description = str(
                    step.get(
                        "description",
                        ""
                    )
                ).strip()

                if not title:
                    continue

                cleaned_steps.append({
                    "number": len(cleaned_steps) + 1,
                    "title": title,
                    "description": description
                })

            # Reject weak plans
            if len(cleaned_steps) < 3:

                return self._fallback_plan(
                    goal
                )

            # Maximum of 8 steps
            cleaned_steps = cleaned_steps[:8]

            # Make sure numbering is correct
            for index, step in enumerate(
                cleaned_steps,
                start=1
            ):
                step["number"] = index

            return {
                "goal": goal,
                "steps": cleaned_steps
            }

        except Exception:

            return self._fallback_plan(
                goal
            )

    # --------------------------------------------------
    # FALLBACK PLAN
    # --------------------------------------------------

    def _fallback_plan(
        self,
        goal: str
    ):

        return {
            "goal": goal,
            "steps": [
                {
                    "number": 1,
                    "title": "Define the required outcome",
                    "description": (
                        f"Determine exactly what is required "
                        f"to complete: {goal}"
                    )
                },
                {
                    "number": 2,
                    "title": "Complete the required work",
                    "description": (
                        "Perform the main actions necessary "
                        "to achieve the goal."
                    )
                },
                {
                    "number": 3,
                    "title": "Test the result",
                    "description": (
                        "Verify that the result works as intended."
                    )
                },
                {
                    "number": 4,
                    "title": "Fix remaining issues",
                    "description": (
                        "Resolve any problems discovered "
                        "during testing."
                    )
                }
            ]
        }

    # --------------------------------------------------
    # FORMAT PLAN
    # --------------------------------------------------

    def format_plan(
        self,
        plan: dict
    ):

        lines = [
            f"PLAN: {plan['goal']}",
            ""
        ]

        for step in plan["steps"]:

            lines.append(
                f"{step['number']}. {step['title']}"
            )

            if step.get("description"):

                lines.append(
                    f"   {step['description']}"
                )

        return "\n".join(lines)

