import os

import httpx
from openai import OpenAI

CACHE_FILE = ".cache.json"

client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=os.environ.get("OPENAI_API_KEY", "EMPTY"))
MODEL = os.environ.get("AGENT_MODEL", "gpt-4o-mini")


HEADERS = {"User-Agent": "my-weather-app (you@example.com)"}  # NWS requires a User-Agent
TIMEOUT = httpx.Timeout(10, connect=5)   # (connect timeout, read timeout) in seconds


class WeatherFetchError(Exception):
     """Raised when the NWS API request fails."""
