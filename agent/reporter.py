import json
from datetime import datetime
from pathlib import Path

from agent.llm import BackboardLLM
from config import CLIMBR_PROFILE


class Reporter:
    def __init__(self, logger):
        self.logger = logger
        self.llm = BackboardLLM(logger)

        self.output_dir = Path("outputs")

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def generate(self, result: dict):
        self.logger.log(
            "REPORTER",
            "Generating final structured report.",
        )

        report = await self._generate_markdown(
            result
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        markdown_path = (
            self.output_dir
            / f"lead_report_{timestamp}.md"
        )

        json_path = (
            self.output_dir
            / f"lead_report_{timestamp}.json"
        )

        markdown_path.write_text(
            report,
            encoding="utf-8",
        )

        json_path.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self.logger.log(
            "REPORTER",
            f"Markdown report saved to {markdown_path}",
        )

        self.logger.log(
            "REPORTER",
            f"JSON result saved to {json_path}",
        )

        return report

    async def _generate_markdown(
        self,
        result: dict,
    ):
        prompt = f"""
Create a concise Markdown lead-research report.

BUSINESS:
{json.dumps(CLIMBR_PROFILE, indent=2)}

RESEARCH RESULT:
{json.dumps(result, indent=2)}

Use exactly these sections:

# Climbr Buddy Lead Research Report

## Goal

## Execution Summary

## Lead Findings

For each lead include:

- Company
- Lead score
- Confidence
- Why it may be relevant
- Supporting evidence
- Potential opportunity
- Source URL

## Limitations

## Conclusion

IMPORTANT:

- Do not invent information.
- Preserve uncertainty.
- Scores come from the deterministic scorer.
- Do not modify the scores.
- Base company claims only on supplied evidence.
"""

        try:
            return await self.llm.ask(prompt)

        except Exception as exc:
            self.logger.log(
                "RECOVERY",
                (
                    "AI report generation failed. "
                    "Using deterministic reporter. "
                    f"Reason: {exc}"
                ),
            )

            return self._fallback_report(
                result
            )

    @staticmethod
    def _fallback_report(result: dict):
        lines = [
            "# Climbr Buddy Lead Research Report",
            "",
            "## Goal",
            "",
            result.get("goal", ""),
            "",
            "## Execution Summary",
            "",
            (
                "Candidates were discovered through "
                "public web search, researched using "
                "public website content, and evaluated "
                "with deterministic scoring criteria."
            ),
            "",
            "## Lead Findings",
            "",
        ]

        for lead in result.get(
            "leads",
            [],
        ):
            lines.extend(
                [
                    (
                        f"### "
                        f"{lead.get('company', 'Unknown')}"
                    ),
                    "",
                    (
                        f"**Score:** "
                        f"{lead.get('score', 0)}/100"
                    ),
                    "",
                    (
                        f"**Confidence:** "
                        f"{lead.get('confidence', 'unknown')}"
                    ),
                    "",
                    (
                        f"**Summary:** "
                        f"{lead.get('summary', '')}"
                    ),
                    "",
                    "**Evidence:**",
                ]
            )

            for evidence in lead.get(
                "evidence",
                [],
            ):
                lines.append(
                    f"- {evidence}"
                )

            lines.extend(
                [
                    "",
                    (
                        "**Potential opportunity:** "
                        + lead.get(
                            "potential_opportunity",
                            "",
                        )
                    ),
                    "",
                    (
                        "**Source:** "
                        + lead.get("url", "")
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                "## Limitations",
                "",
                (
                    "The system relies on publicly "
                    "available web information. Some "
                    "websites may block automated access "
                    "or contain incomplete information."
                ),
                "",
                "## Conclusion",
                "",
                (
                    "The report provides researched "
                    "candidate leads rather than verified "
                    "sales opportunities. Human review "
                    "should precede outreach."
                ),
            ]
        )

        return "\n".join(lines)