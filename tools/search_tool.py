from ddgs import DDGS


class SearchTool:
    name = "web_search"

    def __init__(self, logger):
        self.logger = logger

    def search(self, query: str, max_results: int = 8):
        self.logger.log(
            "TOOL",
            f"Calling web_search(query='{query}')"
        )

        try:
            results = DDGS().text(
                query,
                max_results=max_results,
            )

            cleaned = []

            for result in results:
                cleaned.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                    }
                )

            self.logger.log(
                "TOOL",
                f"web_search returned {len(cleaned)} results."
            )

            return cleaned

        except Exception as exc:
            self.logger.log(
                "ERROR",
                f"Search tool failed: {exc}"
            )

            return []