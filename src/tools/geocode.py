import httpx

from src.cache import cached_get
from src.config import TIMEOUT


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