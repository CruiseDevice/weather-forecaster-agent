import json
import logging
import os
import sys
import time

from src.config import CACHE_FILE

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def _save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(_cache, f)

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


_cache = load_cache()  # key -> (value, timestamp)
