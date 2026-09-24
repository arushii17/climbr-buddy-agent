import argparse
import asyncio
import json

from agent.executor import AgentExecutor
from agent.planner import Planner
from agent.reporter import Reporter
from config import BACKBOARD_API_KEY
from utils.logger import AgentLogger


def print_plan(plan: dict):
    print("\n" + "=" * 70)
    print("CLIMBR BUDDY — EXECUTION PLAN")
    print("=" * 70)

    print(
        f"\nGoal:\n{plan.get('goal', '')}"
    )

    print(
        "\nStrategy:\n"
        f"{plan.get('reasoning_summary', '')}"
    )

    print("\nSteps:")

    for step in plan.get(
        "steps",
        [],
    ):
        print(
            f"\n{step.get('step')}. "
            f"{step.get('action')}"
        )

        print(
            f"   Tool: {step.get('tool')}"
        )

        print(
            f"   Why: {step.get('purpose')}"
        )

    print("\n" + "=" * 70 + "\n")


async def main():
    parser = argparse.ArgumentParser(
        description=(
            "Climbr Buddy — autonomous "
            "lead research agent"
        )
    )

    parser.add_argument(
        "--goal",
        type=str,
        help=(
            "High-level lead-generation goal."
        ),
    )

    parser.add_argument(
        "--max-leads",
        type=int,
        default=5,
        help=(
            "Maximum number of leads "
            "to research."
        ),
    )

    parser.add_argument(
        "--no-simulated-failure",
        action="store_true",
        help=(
            "Disable deliberate timeout "
            "used to demonstrate recovery."
        ),
    )

    args = parser.parse_args()

    if not BACKBOARD_API_KEY:
        raise RuntimeError(
            "BACKBOARD_API_KEY is missing. "
            "Add it to your .env file."
        )

    goal = args.goal

    if not goal:
        print(
            "\nClimbr Buddy — Autonomous "
            "Lead Research Agent\n"
        )

        goal = input(
            "Enter your high-level goal:\n> "
        ).strip()

    if not goal:
        raise ValueError(
            "A goal is required."
        )

    logger = AgentLogger()

    logger.log(
        "SYSTEM",
        "Climbr Buddy started.",
    )

    #
    # 1. PLAN
    #
    planner = Planner(logger)

    plan = await planner.create_plan(
        goal
    )

    #
    # IMPORTANT:
    # Show plan BEFORE tools execute.
    #
    print_plan(plan)

    #
    # 2. EXECUTE
    #
    executor = AgentExecutor(logger)

    result = await executor.execute(
        goal=goal,
        plan=plan,
        simulate_failure=(
            not args.no_simulated_failure
        ),
        max_leads=args.max_leads,
    )

    #
    # 3. REPORT
    #
    reporter = Reporter(logger)

    report = await reporter.generate(
        result
    )

    print("\n")
    print("=" * 70)
    print("FINAL REPORT")
    print("=" * 70)

    print(report)

    print("\n")
    print("=" * 70)
    print("EXECUTION LOG")
    print("=" * 70)

    print(
        json.dumps(
            logger.get_entries(),
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())