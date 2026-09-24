import json

from agent.llm import BackboardLLM
from config import CLIMBR_PROFILE


class Planner:
    def __init__(self, logger):
        self.logger = logger
        self.llm = BackboardLLM(logger)

    async def create_plan(self, goal: str):
        self.logger.log(
            "PLANNER",
            f"Creating plan for goal: {goal}",
        )

        prompt = f"""
You are the planning component of Climbr Buddy,
an autonomous market-research and lead-generation agent.

BUSINESS PROFILE:
{json.dumps(CLIMBR_PROFILE, indent=2)}

USER GOAL:
{goal}

AVAILABLE TOOLS:

1. web_search
   Searches public web information and discovers
   candidate companies.

2. website_reader
   Reads public website content from a URL.

3. lead_scorer
   Deterministically evaluates a researched lead.

Create a concise execution plan BEFORE any tools are used.

Return a JSON object in exactly this structure:

{{
  "goal": "...",
  "reasoning_summary": "...",
  "steps": [
    {{
      "step": 1,
      "action": "...",
      "tool": "web_search",
      "purpose": "..."
    }}
  ]
}}

The plan should normally:
1. discover candidates,
2. research their websites,
3. evaluate evidence,
4. score leads,
5. produce a report.

Do not expose private chain-of-thought.
reasoning_summary should contain only a short
high-level explanation of the strategy.
"""

        try:
            plan = await self.llm.ask_json(prompt)

            self.logger.log(
                "PLANNER",
                "Plan successfully generated.",
            )

            return plan

        except Exception as exc:
            self.logger.log(
                "RECOVERY",
                f"Dynamic planner failed: {exc}",
            )

            self.logger.log(
                "RECOVERY",
                "Using deterministic fallback plan.",
            )

            return self._fallback_plan(goal)

    @staticmethod
    def _fallback_plan(goal: str):
        return {
            "goal": goal,
            "reasoning_summary": (
                "Discover candidate companies, research "
                "public evidence, evaluate lead fit, score "
                "the candidates, and produce a grounded report."
            ),
            "steps": [
                {
                    "step": 1,
                    "action": "Discover candidate companies",
                    "tool": "web_search",
                    "purpose": (
                        "Find companies relevant to the "
                        "user's lead-generation goal."
                    ),
                },
                {
                    "step": 2,
                    "action": "Research candidate websites",
                    "tool": "website_reader",
                    "purpose": (
                        "Collect public evidence about "
                        "each candidate."
                    ),
                },
                {
                    "step": 3,
                    "action": "Evaluate candidate evidence",
                    "tool": "internal_analysis",
                    "purpose": (
                        "Determine relevance using only "
                        "retrieved public information."
                    ),
                },
                {
                    "step": 4,
                    "action": "Score candidate leads",
                    "tool": "lead_scorer",
                    "purpose": (
                        "Apply deterministic lead criteria."
                    ),
                },
                {
                    "step": 5,
                    "action": "Generate final report",
                    "tool": "reporter",
                    "purpose": (
                        "Present findings, evidence, scores, "
                        "sources, and limitations."
                    ),
                },
            ],
        }