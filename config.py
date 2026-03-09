"""Configuration loading from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in the values."
        )
    return value


TELEGRAM_TOKEN: str = _require("TELEGRAM_TOKEN")
AMADEUS_CLIENT_ID: str = _require("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET: str = _require("AMADEUS_CLIENT_SECRET")
AMADEUS_HOSTNAME: str = os.getenv("AMADEUS_HOSTNAME", "test")

# File used to persist monitored routes and last-seen prices
PRICES_FILE: str = os.getenv("PRICES_FILE", "prices.json")
