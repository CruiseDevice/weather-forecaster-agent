import httpx

from src.cache import cached_get
from src.config import WeatherFetchError


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
