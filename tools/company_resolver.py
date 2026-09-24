import json
from urllib.parse import urlparse

from ddgs import DDGS

from agent.llm import BackboardLLM


class CompanyResolverTool:
    name = "company_resolver"

    BLOCKED_DOMAINS = {
        "linkedin.com",
        "crunchbase.com",
        "wellows.com",
        "ahrefs.com",
        "datamation.com",
        "techcrunch.com",
        "forbes.com",
        "wikipedia.org",
        "pitchbook.com",
        "g2.com",
        "capterra.com",
        "producthunt.com",
        "angel.co",
        "startus-insights.com",
        "fundraiseinsider.com",
        "noizz.io",
        "siteindices.com",
        "zoominfo.com",
        "tracxn.com",
        "owler.com",
        "bloomberg.com",
        "businesswire.com",
        "prnewswire.com",
        "medium.com",
        "substack.com",
        "facebook.com",
        "instagram.com",
        "x.com",
        "twitter.com",
        "youtube.com",
        "github.com",
    }

    def __init__(self, logger):
        self.logger = logger
        self.llm = BackboardLLM(logger)

    async def resolve(
        self,
        company_name,
        discovery_snippet="",
    ):
        self.logger.log(
            "TOOL",
            f"Resolving official website for {company_name}",
        )

        query = f'"{company_name}" SaaS official website'

        try:
            results = DDGS().text(
                query,
                max_results=10,
            )

        except Exception as exc:
            self.logger.log(
                "ERROR",
                (
                    "Company website resolution "
                    f"search failed: {exc}"
                ),
            )

            return None

        if not results:
            self.logger.log(
                "WARNING",
                (
                    "No website search results found "
                    f"for {company_name}."
                ),
            )

            return None

        candidates = []

        for result in results:
            url = result.get("href", "")

            if not url:
                continue

            domain = self._extract_domain(url)

            if not domain:
                continue

            if self._is_blocked(domain):
                self.logger.log(
                    "TOOL",
                    (
                        "Rejected non-company domain: "
                        f"{domain}"
                    ),
                )
                continue

            candidates.append(
                {
                    "url": self._root_url(url),
                    "domain": domain,
                    "title": result.get(
                        "title",
                        "",
                    ),
                    "snippet": result.get(
                        "body",
                        "",
                    ),
                }
            )

        if not candidates:
            self.logger.log(
                "WARNING",
                (
                    "No plausible official-site "
                    f"candidates found for {company_name}."
                ),
            )

            return None

        # Keep prompt small and focused.
        candidates = candidates[:6]

        self.logger.log(
            "TOOL",
            (
                f"Verifying {len(candidates)} possible "
                f"website matches for {company_name}."
            ),
        )

        prompt = f"""
You are verifying the official website of a company.

COMPANY NAME:
{company_name}

DISCOVERY CONTEXT:
{discovery_snippet}

POSSIBLE WEBSITES:
{json.dumps(candidates, indent=2)}

Your task is identity verification, not general research.

Determine whether ONE of these websites clearly belongs
to the SAME company described by the company name and
discovery context.

STRICT RULES:

1. Do not choose a website merely because its domain
   contains similar letters.

2. Company names may be short or ambiguous.
   For names such as "Ema", "Linear", "Ramp", etc.,
   require contextual evidence that the website is
   actually the same company.

3. Compare:
   - company name
   - website/domain
   - result title
   - result snippet
   - discovery context

4. Reject unrelated organizations with similar names.

5. Reject directories, news sites, profile sites,
   aggregators and social networks.

6. If there is not enough evidence to confidently
   identify the official website, return null.

7. Do NOT guess.

Return JSON exactly in this format when confident:

{{
  "matched": true,
  "url": "https://example.com/",
  "domain": "example.com",
  "reason": "brief identity evidence"
}}

If no candidate can be confidently verified:

{{
  "matched": false,
  "url": null,
  "domain": null,
  "reason": "insufficient identity evidence"
}}
"""

        try:
            verification = await self.llm.ask_json(
                prompt
            )

        except Exception as exc:
            self.logger.log(
                "RECOVERY",
                (
                    "Website identity verification "
                    f"failed: {exc}"
                ),
            )

            return None

        if not verification.get("matched"):
            self.logger.log(
                "WARNING",
                (
                    "Could not verify an official "
                    f"website for {company_name}: "
                    f"{verification.get('reason', '')}"
                ),
            )

            return None

        verified_url = verification.get("url")
        verified_domain = verification.get("domain")

        if not verified_url or not verified_domain:
            self.logger.log(
                "WARNING",
                (
                    f"Website verification for "
                    f"{company_name} returned "
                    "incomplete information."
                ),
            )

            return None

        # Important:
        # LLM may only select one of the URLs that
        # actually came from our filtered search.
        candidate_domains = {
            candidate["domain"]
            for candidate in candidates
        }

        clean_verified_domain = (
            verified_domain
            .lower()
            .replace("www.", "")
            .strip()
        )

        if clean_verified_domain not in candidate_domains:
            self.logger.log(
                "WARNING",
                (
                    "Verifier returned a domain that "
                    "was not present in resolver "
                    "search results. Rejecting it."
                ),
            )

            return None

        if self._is_blocked(
            clean_verified_domain
        ):
            self.logger.log(
                "WARNING",
                (
                    "Verifier selected a blocked "
                    "domain. Rejecting it."
                ),
            )

            return None

        # Find the original candidate so that the
        # returned URL is deterministic rather than
        # trusting an LLM-generated URL string.
        verified_candidate = next(
            (
                candidate
                for candidate in candidates
                if candidate["domain"]
                == clean_verified_domain
            ),
            None,
        )

        if not verified_candidate:
            return None

        self.logger.log(
            "TOOL",
            (
                f"Verified official website for "
                f"{company_name}: "
                f"{verified_candidate['url']}"
            ),
        )

        self.logger.log(
            "TOOL",
            (
                "Verification reason: "
                f"{verification.get('reason', '')}"
            ),
        )

        return {
            "company": company_name,
            "url": verified_candidate["url"],
            "domain": verified_candidate["domain"],
        }

    def _is_blocked(
        self,
        domain,
    ):
        for blocked in self.BLOCKED_DOMAINS:
            if (
                domain == blocked
                or domain.endswith(
                    "." + blocked
                )
            ):
                return True

        return False

    @staticmethod
    def _extract_domain(
        url,
    ):
        try:
            domain = (
                urlparse(url)
                .netloc
                .lower()
            )

            if domain.startswith("www."):
                domain = domain[4:]

            return domain

        except Exception:
            return ""

    @staticmethod
    def _root_url(
        url,
    ):
        parsed = urlparse(url)

        scheme = parsed.scheme or "https"

        return (
            f"{scheme}://"
            f"{parsed.netloc}/"
        )