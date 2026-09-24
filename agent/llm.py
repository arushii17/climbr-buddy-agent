import json

from backboard import BackboardClient

from config import (
    BACKBOARD_API_KEY,
    BACKBOARD_MODEL,
    BACKBOARD_PROVIDER,
)


class BackboardLLM:
    def __init__(self, logger):
        if not BACKBOARD_API_KEY:
            raise RuntimeError(
                "BACKBOARD_API_KEY is missing from .env"
            )

        self.logger = logger

        self.client = BackboardClient(
            api_key=BACKBOARD_API_KEY
        )

    async def ask(
        self,
        prompt: str,
        json_output: bool = False,
    ):
        self.logger.log(
            "LLM",
            (
                f"Calling Backboard "
                f"({BACKBOARD_PROVIDER}/{BACKBOARD_MODEL})"
            ),
        )

        response = await self.client.send_message(
            prompt,
            llm_provider=BACKBOARD_PROVIDER,
            model_name=BACKBOARD_MODEL,
            stream=False,
            memory="off",
            json_output=json_output,
        )

        content = response.content

        self.logger.log(
            "LLM",
            "Backboard response received.",
        )

        return content

    async def ask_json(self, prompt: str):
        raw = await self.ask(
            prompt,
            json_output=True,
        )

        if isinstance(raw, dict):
            return raw

        raw = raw.strip()

        if raw.startswith("```"):
            raw = (
                raw.replace("```json", "")
                .replace("```", "")
                .strip()
            )

        return json.loads(raw)