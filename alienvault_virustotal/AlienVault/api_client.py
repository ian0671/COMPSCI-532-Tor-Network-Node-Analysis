import time
import requests
import logging
import os
from functools import wraps
from typing import List, Dict
import datetime

OTX_API_KEY = os.environ.get("OTX_API_KEY")

def retry(max_attempts=3, initial_delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.warning("Attempt %d/%d failed: %s", attempt, max_attempts, e)
                    if attempt == max_attempts:
                        logging.exception("All retries failed.")
                        raise
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator

@retry(max_attempts=3)
def query_recent_pulses() -> List[Dict]:
    if not OTX_API_KEY:
        raise RuntimeError("Missing OTX_API_KEY")

    api_url = "https://otx.alienvault.com/api/v1/pulses/subscribed"
    headers = {"X-OTX-API-KEY": OTX_API_KEY}
    resp = requests.get(api_url, headers=headers, timeout=30)
    resp.raise_for_status()
    pulses = resp.json().get("results", [])

    normalized_pulses = []
    for pulse in pulses:
        indicators = pulse.get("indicators", [])
        normalized_pulses.append({
            "id": pulse.get("id"),
            "name": pulse.get("name"),
            "description": pulse.get("description"),
            "author_name": pulse.get("author_name"),
            "created": pulse.get("created"),
            "modified": pulse.get("modified"),
            "tags": ",".join(pulse.get("tags", [])),
            "indicator_count": len(indicators),
            "indicators": [
                {
                    "indicator": i.get("indicator"),
                    "type": i.get("type"),
                    "description": i.get("description"),
                    "created": i.get("created"),
                }
                for i in indicators
            ],
            "normalized_at": datetime.datetime.utcnow().isoformat() + "Z",
        })

    return normalized_pulses
