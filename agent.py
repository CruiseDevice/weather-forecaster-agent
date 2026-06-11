import json
import logging
import os
import sys
import time

import httpx
from openai import OpenAI

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)
CACHE_FILE = ".cache.json"

client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=os.environ.get("OPENAI_API_KEY", "EMPTY"))
MODEL = os.environ.get("AGENT_MODEL", "gpt-4o-mini")


HEADERS = {"User-Agent": "my-weather-app (you@example.com)"}  # NWS requires a User-Agent
TIMEOUT = httpx.Timeout(10, connect=5)   # (connect timeout, read timeout) in seconds


class WeatherFetchError(Exception):
     """Raised when the NWS API request fails."""


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def _save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(_cache, f)


_cache = load_cache()  # key -> (value, timestamp)


def cached_get(key: str, ttl_seconds: int, fetch_fn):
    now = time.time()
    if key in _cache:
        value, stored_at = _cache[key]
        if now - stored_at < ttl_seconds:
            logger.info("cache HIT %s (age %.0fs)", key, now - stored_at)
            return value
        logger.info("cache EXPIRED %s", key)
    else:
        logger.info("cache MISS %s", key)
    result = fetch_fn()
    _cache[key] = (result, now)
    _save_cache()
    return result


def _http_request_uncached(url: str) -> str:
    if not url.startswith("https://api.weather.gov/"):
        return "Error: only api.weather.gov URLs allowed."
    try:
        r = httpx.get(url, headers={"User-Agent": "weather-agent (you@example.com)"}, timeout=10)
        r.raise_for_status()
        return r.text[:20_000]
    except httpx.HTTPError as e:
        raise WeatherFetchError(f"NWS request failed: {e}") from e

    
def http_request(url: str) -> str:
    return cached_get(f"http:{url}", ttl_seconds=300, fetch_fn=lambda: _http_request_uncached(url))


def _geocode_uncached(city: str) -> str:
    response = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": "weather-agent/1.0"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return f"No results found for '{city}'"
    lat = float(results[0]['lat'])
    lon = float(results[0]['lon'])
    return f"{lat:.4f}, {lon:.4f}"


def geocode(city: str) -> str:
    return cached_get(f"geo: {city.strip().lower()}", ttl_seconds=86400, fetch_fn=lambda: _geocode_uncached(city))


TOOLS = {
    "http_request": http_request,
    "geocode": geocode
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": "GET a URL from the NWS API (api.weather.gov), returns the JSON body.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "GET a co-ordinates from the Nominatim API when a location is given in query, returns the JSON body.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }   
]


SYSTEM_PROMPT = """You are a weather assistant with two tools: geocode and http_request.

Workflow:
1. If the user gives a city/place name instead of coordinates, call geocode with the place name first to get (LAT, LON).
2. GET https://api.weather.gov/points/{LAT},{LON} -> response contains properties.forecast, a URL
3. GET that URL -> properties.periods has the forecast

Rules:
- If the user already provides coordinates, skip geocoding and go straight to step 2.
- If geocoding returns multiple matches, pick the most likely one and mention which you chose.
- If geocoding fails or the place is ambiguous, ask the user to clarify instead of guessing.
- The NWS API only covers the US; if the location is outside the US, say so instead of calling the API.

Once you have all the data, return it as-is. Do not format or summarize
"""


def format_answer(user_query: str, raw_data: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": """Format the following weather data into a clear,
            human-readable answer. One line per forecast period, like: Tonight: 54°F — Partly Cloudy. Be concise.
            """},
            {"role": "user", "content": f"Question: {user_query}\n\nData:\n{raw_data}"},
        ],
    )
    return response.choices[0].message.content


def fetch_weather_data(user_query: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}]

    for _ in range(10):
        message = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS
        ).choices[0].message

        if not message.tool_calls:          # no tool call = final answer
            return message.content

        messages.append({"role": "assistant", "content": message.content,
                        "tool_calls": [tc.model_dump() for tc in message.tool_calls]})

        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            fn = TOOLS.get(tc.function.name)
            try:
                result = fn(**args) if fn else f"Error: no tool named {tc.function.name}"
            except Exception as e:
                result = f"Error: {e}" 
            print(f"[TOOL] {tc.function.name}({args}) -> {result[:200]}", file=sys.stderr) 
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "Run out of iterations"


def agent_run(user_query: str) -> str:
    raw_data = fetch_weather_data(user_query)
    formatted = format_answer(user_query, raw_data)
    return formatted

def main() -> None:
    print(agent_run(" ".join(sys.argv[1:]) or "Forecast for Seattle"))

if __name__ == "__main__":
    main()