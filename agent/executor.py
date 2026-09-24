import json
import re

from agent.llm import BackboardLLM
from config import CLIMBR_PROFILE, DEFAULT_MAX_LEADS

from tools.company_resolver import CompanyResolverTool
from tools.lead_scorer import LeadScorerTool
from tools.search_tool import SearchTool
from tools.website_reader import WebsiteReaderTool


class AgentExecutor:
    def __init__(self, logger):
        self.logger = logger

        self.llm = BackboardLLM(logger)

        self.search_tool = SearchTool(logger)
        self.reader_tool = WebsiteReaderTool(logger)
        self.scorer_tool = LeadScorerTool(logger)
        self.resolver_tool = CompanyResolverTool(logger)

    async def execute(
        self,
        goal: str,
        plan: dict,
        simulate_failure: bool = True,
        max_leads: int = DEFAULT_MAX_LEADS,
    ):
        self.logger.log(
            "EXECUTOR",
            "Beginning autonomous plan execution.",
        )

        # =================================================
        # STEP 1 — GENERATE SEARCH QUERY
        # =================================================

        query = await self._build_search_query(goal)

        search_results = self.search_tool.search(
            query=query,
            max_results=max(max_leads * 4, 12),
        )

        # =================================================
        # RECOVERY — SEARCH FAILURE
        # =================================================

        if not search_results:
            self.logger.log(
                "RECOVERY",
                "Initial search returned no results.",
            )

            recovery_query = (
                "early stage SaaS startups "
                "seed funding growth launch 2026"
            )

            self.logger.log(
                "RECOVERY",
                (
                    "Retrying with broader search: "
                    f"{recovery_query}"
                ),
            )

            search_results = self.search_tool.search(
                query=recovery_query,
                max_results=max(max_leads * 5, 15),
            )

        if not search_results:
            self.logger.log(
                "ERROR",
                "Search failed after recovery attempt.",
            )

            return {
                "status": "failed",
                "goal": goal,
                "plan": plan,
                "leads": [],
                "message": (
                    "No public search results were "
                    "available."
                ),
            }

        # =================================================
        # STEP 2 — READ DISCOVERY SOURCES + EXTRACT COMPANIES
        # =================================================

        candidates = await self._discover_candidates(
            goal=goal,
            search_results=search_results,
            max_leads=max_leads,
        )

        # =================================================
        # RECOVERY — NO COMPANIES EXTRACTED
        # =================================================

        if not candidates:
            self.logger.log(
                "RECOVERY",
                (
                    "No companies were extracted from "
                    "the initial discovery sources."
                ),
            )

            self.logger.log(
                "RECOVERY",
                (
                    "Running broader candidate "
                    "discovery search."
                ),
            )

            candidates = await self._recover_candidates(
                goal=goal,
                max_leads=max_leads,
            )

        if not candidates:
            self.logger.log(
                "ERROR",
                (
                    "No candidate companies could be "
                    "identified after recovery."
                ),
            )

            return {
                "status": "failed",
                "goal": goal,
                "plan": plan,
                "leads": [],
                "message": (
                    "Candidate discovery failed after "
                    "recovery attempts."
                ),
            }

        researched_leads = []

        # =================================================
        # STEP 3 — RESEARCH ACTUAL COMPANIES
        # =================================================

        for index, candidate in enumerate(candidates):
            company_name = candidate.get(
                "title",
                "Unknown",
            )

            self.logger.log(
                "EXECUTOR",
                (
                    f"Researching candidate "
                    f"{index + 1}/{len(candidates)}: "
                    f"{company_name}"
                ),
            )

            # =============================================
            # RESOLVE + VERIFY OFFICIAL WEBSITE
            # =============================================

            resolved = await self.resolver_tool.resolve(
                company_name=company_name,
                discovery_snippet=candidate.get(
                    "snippet",
                    "",
                ),
            )

            if resolved:
                candidate["discovery_url"] = (
                    candidate.get("url", "")
                )

                candidate["url"] = resolved["url"]

                candidate["website_verified"] = True

                self.logger.log(
                    "EXECUTOR",
                    (
                        "Using verified company website: "
                        f"{candidate['url']}"
                    ),
                )

            else:
                candidate["website_verified"] = False

                self.logger.log(
                    "RECOVERY",
                    (
                        "Official website could not be "
                        "confidently verified. "
                        "Using discovery source."
                    ),
                )

            # =============================================
            # READ COMPANY WEBSITE / DISCOVERY SOURCE
            #
            # Deliberately induce one timeout on first
            # lead for assignment failure demonstration.
            # =============================================

            page = self._read_with_recovery(
                candidate=candidate,
                induce_failure=(
                    simulate_failure and index == 0
                ),
            )

            if page is None:
                self.logger.log(
                    "WARNING",
                    (
                        f"No usable evidence recovered "
                        f"for {company_name}. "
                        "Skipping candidate."
                    ),
                )

                continue

            # =============================================
            # ANALYSE EVIDENCE
            # =============================================

            analysis = await self._analyse_candidate(
                goal=goal,
                candidate=candidate,
                page=page,
            )

            if not analysis:
                self.logger.log(
                    "WARNING",
                    (
                        f"Analysis failed for "
                        f"{company_name}. "
                        "Skipping candidate."
                    ),
                )

                continue

            # =============================================
            # DETERMINISTIC LEAD SCORING
            # =============================================

            score_data = self.scorer_tool.score(
                analysis
            )

            analysis.update(score_data)

            analysis["website_verified"] = (
                candidate.get(
                    "website_verified",
                    False,
                )
            )

            if candidate.get("discovery_url"):
                analysis["discovery_url"] = (
                    candidate["discovery_url"]
                )

            researched_leads.append(analysis)

        # =================================================
        # STEP 4 — RANK LEADS
        # =================================================

        researched_leads.sort(
            key=lambda item: item.get("score", 0),
            reverse=True,
        )

        self.logger.log(
            "EXECUTOR",
            (
                f"Execution completed with "
                f"{len(researched_leads)} "
                "researched leads."
            ),
        )

        return {
            "status": "success",
            "goal": goal,
            "plan": plan,
            "leads": researched_leads,
        }

    # =====================================================
    # SEARCH QUERY
    # =====================================================

    async def _build_search_query(
        self,
        goal: str,
    ):
        self.logger.log(
            "EXECUTOR",
            "Generating search strategy.",
        )

        prompt = f"""
Create ONE concise public web search query for
discovering early-stage SaaS companies relevant
to this goal:

{goal}

RULES:

- Search broadly across the public web.
- Do NOT use site: operators.
- Do NOT restrict the search to one website.
- Prefer terms involving SaaS startups,
  funding, launches, traction and growth.
- Search results may include startup lists,
  funding articles, company websites or news.

Return ONLY the search query.
"""

        try:
            query = await self.llm.ask(prompt)

            query = (
                query
                .strip()
                .strip('"')
            )

            query = self._sanitize_search_query(
                query
            )

            if not query:
                raise ValueError(
                    "Generated query was empty."
                )

            self.logger.log(
                "EXECUTOR",
                (
                    "Generated search query: "
                    f"{query}"
                ),
            )

            return query

        except Exception as exc:
            self.logger.log(
                "RECOVERY",
                (
                    "Search-query generation failed: "
                    f"{exc}"
                ),
            )

            fallback_query = (
                "early stage SaaS startups "
                "funding growth launch 2026"
            )

            self.logger.log(
                "RECOVERY",
                (
                    "Using fallback search query: "
                    f"{fallback_query}"
                ),
            )

            return fallback_query

    # =====================================================
    # QUERY SANITIZER
    # =====================================================

    def _sanitize_search_query(
        self,
        query: str,
    ):
        original_query = query

        # Remove site:example.com
        query = re.sub(
            r"\bsite:\S+",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # Remove dangling Boolean operators.
        query = re.sub(
            r"\b(?:OR|AND)\b(?=\s*(?:OR|AND|\Z))",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"(?:\s+\b(?:OR|AND)\b\s*)+$",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"^(?:OR|AND)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"\s+",
            " ",
            query,
        ).strip()

        if query != original_query:
            self.logger.log(
                "EXECUTOR",
                (
                    "Removed restrictive site "
                    "operators from generated "
                    "search query."
                ),
            )

        return query

    # =====================================================
    # DISCOVERY
    #
    # IMPORTANT CHANGE:
    # We now READ search results before asking the LLM
    # to identify actual companies.
    # =====================================================

    async def _discover_candidates(
        self,
        goal: str,
        search_results: list,
        max_leads: int,
    ):
        self.logger.log(
            "DISCOVERY",
            (
                "Reading discovery sources before "
                "extracting company candidates."
            ),
        )

        discovery_sources = []

        # We do not need to read every search result.
        # A few strong sources are enough and keep
        # execution reasonably fast.
        max_sources = min(
            len(search_results),
            6,
        )

        for index, result in enumerate(
            search_results[:max_sources]
        ):
            url = result.get("url", "")

            if not url:
                continue

            self.logger.log(
                "DISCOVERY",
                (
                    f"Reading discovery source "
                    f"{index + 1}/{max_sources}: "
                    f"{url}"
                ),
            )

            try:
                page = self.reader_tool.read(
                    url,
                    simulate_failure=False,
                )

                content = page.get(
                    "content",
                    "",
                )

                if content:
                    discovery_sources.append(
                        {
                            "url": url,
                            "search_title": (
                                result.get(
                                    "title",
                                    "",
                                )
                            ),
                            "search_snippet": (
                                result.get(
                                    "snippet",
                                    "",
                                )
                            ),
                            "page_title": page.get(
                                "title",
                                "",
                            ),
                            # Keep prompt size controlled.
                            "content": content[:7000],
                        }
                    )

            except Exception as exc:
                self.logger.log(
                    "RECOVERY",
                    (
                        "Could not read discovery "
                        f"source: {exc}. "
                        "Using search snippet instead."
                    ),
                )

                snippet = result.get(
                    "snippet",
                    "",
                )

                if snippet:
                    discovery_sources.append(
                        {
                            "url": url,
                            "search_title": (
                                result.get(
                                    "title",
                                    "",
                                )
                            ),
                            "search_snippet": snippet,
                            "page_title": "",
                            "content": snippet,
                        }
                    )

        if not discovery_sources:
            self.logger.log(
                "WARNING",
                (
                    "No discovery-source content "
                    "could be collected."
                ),
            )

            return []

        self.logger.log(
            "DISCOVERY",
            (
                f"Collected "
                f"{len(discovery_sources)} "
                "discovery sources."
            ),
        )

        # =============================================
        # Extract REAL company names from page content
        # =============================================

        prompt = f"""
You are the company-discovery component of
Climbr Buddy.

USER GOAL:
{goal}

PUBLIC DISCOVERY SOURCES:
{json.dumps(discovery_sources, indent=2)}

Extract up to {max_leads} REAL COMPANY NAMES
from the supplied source content.

CRITICAL RULES:

1. A discovery source may be an article such as:
   "Top 30 SaaS Startups to Watch".

   That article title is NOT a company.

2. Extract actual companies MENTIONED INSIDE
   the supplied article/page content.

3. Do NOT return:
   - article titles
   - publishers
   - directories
   - news websites
   - list names
   - blog names

4. For example, if an article published by
   ExampleNews mentions a SaaS startup called
   DataPilot, return DataPilot — NOT ExampleNews.

5. The company must be explicitly supported
   by the supplied content.

6. Do NOT invent companies.

7. Prefer companies with explicit evidence of:
   - SaaS/software products
   - startup or early-stage status
   - recent funding
   - launch activity
   - customer traction
   - revenue growth
   - expansion
   - adoption growth

8. Each candidate MUST contain the source URL
   where that company was actually found.

9. The snippet must describe evidence about
   THAT COMPANY, not the publisher.

Return JSON exactly in this format:

{{
  "candidates": [
    {{
      "title": "Actual company name",
      "url": "discovery source URL",
      "snippet": "Evidence about this company from the source",
      "selection_reason": "Why this company fits the goal"
    }}
  ]
}}
"""

        try:
            data = await self.llm.ask_json(
                prompt
            )

            candidates = data.get(
                "candidates",
                [],
            )

            if not isinstance(
                candidates,
                list,
            ):
                candidates = []

            cleaned = []

            seen_names = set()

            for candidate in candidates:
                name = candidate.get(
                    "title",
                    "",
                ).strip()

                url = candidate.get(
                    "url",
                    "",
                ).strip()

                snippet = candidate.get(
                    "snippet",
                    "",
                ).strip()

                if not name or not url:
                    continue

                # -------------------------------------
                # Reject obvious article/list titles
                # deterministically.
                # -------------------------------------

                if self._looks_like_article_title(
                    name
                ):
                    self.logger.log(
                        "DISCOVERY",
                        (
                            "Rejected article/list "
                            f"title as candidate: {name}"
                        ),
                    )

                    continue

                normalized = (
                    name
                    .lower()
                    .strip()
                )

                if normalized in seen_names:
                    continue

                seen_names.add(
                    normalized
                )

                cleaned.append(
                    {
                        "title": name,
                        "url": url,
                        "snippet": snippet,
                        "selection_reason": (
                            candidate.get(
                                "selection_reason",
                                "",
                            )
                        ),
                    }
                )

            self.logger.log(
                "DISCOVERY",
                (
                    f"Extracted {len(cleaned)} "
                    "actual company candidates."
                ),
            )

            return cleaned[:max_leads]

        except Exception as exc:
            self.logger.log(
                "RECOVERY",
                (
                    "Company extraction from "
                    f"discovery sources failed: {exc}"
                ),
            )

            return []

    # =====================================================
    # ARTICLE-TITLE GUARD
    # =====================================================

    @staticmethod
    def _looks_like_article_title(
        name: str,
    ):
        text = name.lower()

        suspicious_phrases = [
            "top ",
            "best ",
            "list of",
            "companies to watch",
            "startups to watch",
            "saas startups",
            "saas companies",
            "startup companies",
            "recently funded",
            "funded startups",
            "funded companies",
            "companies in ",
            "startups in ",
            "guide to",
            "ultimate guide",
        ]

        return any(
            phrase in text
            for phrase in suspicious_phrases
        )

    # =====================================================
    # RECOVERY CANDIDATE DISCOVERY
    # =====================================================

    async def _recover_candidates(
        self,
        goal: str,
        max_leads: int,
    ):
        recovery_query = (
            "early stage SaaS startups "
            "seed funding growth launch "
            "customer traction 2026"
        )

        self.logger.log(
            "RECOVERY",
            (
                "Running recovery search: "
                f"{recovery_query}"
            ),
        )

        recovery_results = self.search_tool.search(
            query=recovery_query,
            max_results=max(
                max_leads * 5,
                15,
            ),
        )

        if not recovery_results:
            self.logger.log(
                "ERROR",
                (
                    "Recovery search returned "
                    "no results."
                ),
            )

            return []

        # IMPORTANT:
        # Recovery uses the SAME robust discovery
        # process instead of reverting to snippet-only
        # extraction.
        return await self._discover_candidates(
            goal=goal,
            search_results=recovery_results,
            max_leads=max_leads,
        )

    # =====================================================
    # WEBSITE READER + FAILURE RECOVERY
    # =====================================================

    def _read_with_recovery(
        self,
        candidate: dict,
        induce_failure: bool,
    ):
        url = candidate.get(
            "url",
            "",
        )

        try:
            return self.reader_tool.read(
                url,
                simulate_failure=induce_failure,
            )

        except TimeoutError as exc:
            self.logger.log(
                "RECOVERY",
                (
                    f"Detected timeout: {exc}"
                ),
            )

            self.logger.log(
                "RECOVERY",
                (
                    "Retrying website_reader "
                    "without simulated failure."
                ),
            )

            try:
                page = self.reader_tool.read(
                    url,
                    simulate_failure=False,
                )

                self.logger.log(
                    "RECOVERY",
                    (
                        "Retry succeeded. "
                        "Continuing execution."
                    ),
                )

                return page

            except Exception as retry_exc:
                self.logger.log(
                    "RECOVERY",
                    (
                        "Retry failed. Falling back "
                        "to discovery evidence. "
                        f"Reason: {retry_exc}"
                    ),
                )

                return (
                    self._search_result_fallback(
                        candidate
                    )
                )

        except Exception as exc:
            self.logger.log(
                "RECOVERY",
                (
                    f"Website reader failed: {exc}. "
                    "Using discovery evidence."
                ),
            )

            return (
                self._search_result_fallback(
                    candidate
                )
            )

    # =====================================================
    # DISCOVERY-EVIDENCE FALLBACK
    # =====================================================

    @staticmethod
    def _search_result_fallback(
        candidate: dict,
    ):
        snippet = candidate.get(
            "snippet",
            "",
        )

        if not snippet:
            return None

        fallback_url = candidate.get(
            "discovery_url",
            candidate.get(
                "url",
                "",
            ),
        )

        return {
            "url": fallback_url,
            "title": candidate.get(
                "title",
                "",
            ),
            "content": snippet,
            "fallback": True,
        }

    # =====================================================
    # EVIDENCE ANALYSIS
    # =====================================================

    async def _analyse_candidate(
        self,
        goal: str,
        candidate: dict,
        page: dict,
    ):
        company_name = candidate.get(
            "title",
            "candidate",
        )

        self.logger.log(
            "ANALYSIS",
            (
                "Analysing evidence for "
                f"{company_name}."
            ),
        )

        prompt = f"""
You are the evidence-analysis component
of Climbr Buddy.

CLIMBR:
{json.dumps(CLIMBR_PROFILE, indent=2)}

USER GOAL:
{goal}

COMPANY:
{company_name}

DISCOVERY EVIDENCE:
{candidate.get("snippet", "")}

WEBSITE VERIFIED:
{candidate.get("website_verified", False)}

CURRENT EVIDENCE SOURCE:
{page.get("url")}

SOURCE TITLE:
{page.get("title")}

PUBLIC EVIDENCE:
{page.get("content")}

Determine whether this company is a
plausible potential lead for Climbr Agency.

STRICT RULES:

1. Analyse ONLY the company named:
   {company_name}

2. Do not switch to analysing the publisher,
   article, directory or another company.

3. Use ONLY supplied evidence.

4. Do not invent company facts.

5. is_relevant_business=true only when
   evidence supports that this company fits
   Climbr's target market.

6. has_digital_presence=true only when
   evidence supports a public digital
   product, platform, website or online
   business presence.

7. growth_signal=true ONLY when evidence
   explicitly indicates:
   - funding
   - expansion
   - hiring
   - launch activity
   - customer traction
   - increasing adoption
   - revenue growth
   - another observable growth indicator

8. service_need=true ONLY when evidence
   identifies a concrete problem, weakness,
   gap or opportunity involving:
   - branding
   - acquisition
   - positioning
   - content
   - conversion
   - website
   - digital presence
   - marketing

9. Funding alone does NOT prove a need
   for agency services.

10. Growth alone does NOT prove a need
    for agency services.

11. Do NOT assume that startups generally
    need marketing.

12. potential_opportunity must be supported
    by evidence.

    If no concrete opportunity is supported,
    use exactly:

    "No clear agency opportunity identified
    from available evidence."

13. confidence must be exactly:
    "high", "medium", or "low".

14. Evidence entries must be concise
    paraphrases of supplied information.

15. The company field MUST remain:
    {company_name}

Return JSON exactly in this format:

{{
  "company": "{company_name}",
  "url": "...",
  "summary": "...",
  "is_relevant_business": true,
  "has_digital_presence": true,
  "growth_signal": false,
  "service_need": false,
  "evidence": [
    "...",
    "..."
  ],
  "potential_opportunity": "...",
  "confidence": "high"
}}
"""

        try:
            analysis = await self.llm.ask_json(
                prompt
            )

            # -----------------------------------------
            # Deterministic identity protection.
            #
            # Do not allow the LLM to silently rename
            # the lead after reading an article.
            # -----------------------------------------

            analysis["company"] = company_name

            # Preserve the actual evidence URL.
            analysis["url"] = page.get(
                "url",
                candidate.get(
                    "url",
                    "",
                ),
            )

            return analysis

        except Exception as exc:
            self.logger.log(
                "ERROR",
                (
                    "Candidate analysis failed: "
                    f"{exc}"
                ),
            )

            return None