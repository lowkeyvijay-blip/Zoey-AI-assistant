
from core.planner import Planner


planner = Planner()


goals = [
    "I want to finish Zoey today.",
    "I want to build a website for a client.",
]


for goal in goals:

    print("=" * 60)
    print("GOAL:")
    print(goal)

    result = planner.create_plan(goal)

    print("\nRESULT:")

    print(
        planner.format_plan(result)
    )

    print()

