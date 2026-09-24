import requests

from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT


class WebsiteReaderTool:
    name = "website_reader"

    def __init__(self, logger):
        self.logger = logger
        self.failure_triggered = False

    def read(
        self,
        url: str,
        simulate_failure: bool = False,
    ):
        self.logger.log(
            "TOOL",
            f"Calling website_reader(url='{url}')"
        )

        # Deliberately induced failure for assignment demonstration.
        if simulate_failure and not self.failure_triggered:
            self.failure_triggered = True

            self.logger.log(
                "ERROR",
                "Simulated website timeout triggered."
            )

            raise TimeoutError(
                "Simulated timeout for failure-recovery demonstration."
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; "
                "ClimbrBuddyResearchAgent/1.0)"
            )
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(
            ["script", "style", "noscript", "svg"]
        ):
            element.decompose()

        title = ""

        if soup.title:
            title = soup.title.get_text(
                " ",
                strip=True,
            )

        text = soup.get_text(
            " ",
            strip=True,
        )

        text = " ".join(text.split())

        # Prevent huge pages being sent to the LLM.
        text = text[:12000]

        self.logger.log(
            "TOOL",
            f"Successfully read {url}"
        )

        return {
            "url": url,
            "title": title,
            "content": text,
        }