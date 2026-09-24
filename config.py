import os

from dotenv import load_dotenv

load_dotenv()

BACKBOARD_API_KEY = os.getenv("BACKBOARD_API_KEY")

BACKBOARD_PROVIDER = os.getenv(
    "BACKBOARD_PROVIDER",
    "openrouter",
)

BACKBOARD_MODEL = os.getenv(
    "BACKBOARD_MODEL",
    "moonshotai/kimi-k2.6",
)

CLIMBR_PROFILE = {
    "name": "Climbr Agency",
    "website": "https://climbr.agency/",
    "description": (
        "Climbr Agency is a digital agency. Climbr Buddy "
        "acts as an AI-powered market research and "
        "lead-generation assistant for the agency."
    ),
    "ideal_leads": [
        "startups",
        "SaaS companies",
        "growing digital businesses",
        "businesses with an active online presence",
    ],
}

DEFAULT_MAX_LEADS = 5
REQUEST_TIMEOUT = 10