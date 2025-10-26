import datetime
import json
import logging
import os
from typing import Dict, Any, List, Optional

import requests
import azure.functions as func
from azure.eventhub import EventHubProducerClient, EventData


# -------------------------------------------------------
# Function App Initialization
# -------------------------------------------------------
app = func.FunctionApp()
logging.warning("FunctionApp loaded — waiting for timer triggers…")


# -------------------------------------------------------
# Environment & Config Helpers
# -------------------------------------------------------
def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.environ.get(name, default)
    if val is None:
        logging.error(f"Missing required app setting: {name}")
    return val


def _get_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logging.warning(f"⚠️ Invalid int for {name}='{raw}', using default {default}")
        return default


# Read settings once at import time
EVENTHUB_CONNECTION = _get_env("EVENTHUB_CONNECTION")  # namespace conn string (no EntityPath)
ABUSE_EH_NAME = _get_env("ABUSE_EH_NAME")              # e.g., 'abuseipdbdata'
CENSYS_EH_NAME = _get_env("CENSYS_EH_NAME")            # e.g., 'censysdata'

ABUSE_API_KEY = _get_env("ABUSE_API_KEY")
ABUSE_IP_LIST: List[str] = [x.strip() for x in os.environ.get("ABUSE_IP_LIST", "8.8.8.8,1.1.1.1").split(",") if x.strip()]

CENSYS_API_TOKEN = _get_env("CENSYS_API_TOKEN")
CENSYS_QUERY = os.environ.get("CENSYS_QUERY", "services.service_name:HTTP")
CENSYS_PER_PAGE = _get_env_int("CENSYS_PER_PAGE", 50)
CENSYS_MAX_PAGES = _get_env_int("CENSYS_MAX_PAGES", 1)

# Light config echo (redacted)
logging.info(
    "🔧 Config: ABUSE_EH_NAME=%s, CENSYS_EH_NAME=%s, ABUSE_IP_COUNT=%d, CENSYS_PER_PAGE=%d, CENSYS_MAX_PAGES=%d",
    ABUSE_EH_NAME, CENSYS_EH_NAME, len(ABUSE_IP_LIST), CENSYS_PER_PAGE, CENSYS_MAX_PAGES
)


# -------------------------------------------------------
# Helper: Send to Event Hub
# -------------------------------------------------------
def send_to_eventhub(eventhub_name: str, payload: Dict[str, Any]) -> None:
    """Send a JSON payload to an Event Hub."""
    if not EVENTHUB_CONNECTION:
        logging.error("EVENTHUB_CONNECTION missing; cannot send.")
        return
    if not eventhub_name:
        logging.error("eventhub_name missing; cannot send.")
        return

    try:
        producer = EventHubProducerClient.from_connection_string(
            conn_str=EVENTHUB_CONNECTION,
            eventhub_name=eventhub_name
        )
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        event = EventData(body)
        with producer:
            producer.send_batch([event])
        logging.info("Sent %d bytes to Event Hub '%s'", len(body.encode("utf-8")), eventhub_name)
    except Exception as e:
        logging.exception("Failed sending to Event Hub '%s': %s", eventhub_name, e)


# -------------------------------------------------------
# Timer Function: Censys (every minute)
# -------------------------------------------------------
@app.schedule(
    schedule="0 * * * * *",          # every minute at second 0 (more reliable on Consumption)
    arg_name="mytimer",
    run_on_startup=True,             # fire once as the host starts
    use_monitor=False                # ignore history; always run on schedule
)
def CensysTimer(mytimer: func.TimerRequest) -> None:
    fired_at = datetime.datetime.utcnow().isoformat() + "Z"
    logging.info("CensysTimer fired at %s", fired_at)

    if not CENSYS_API_TOKEN:
        logging.error("CENSYS_API_TOKEN missing; skipping.")
        return
    if not CENSYS_EH_NAME:
        logging.error("CENSYS_EH_NAME missing; skipping.")
        return

    url = "https://search.censys.io/api/v2/hosts/search"
    headers = {
        "Authorization": f"Bearer {CENSYS_API_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "cs532-azure-functions/1.0"
    }

    params = {
        "q": CENSYS_QUERY,
        "per_page": CENSYS_PER_PAGE,
        "virtual_hosts": "EXCLUDE"
    }

    all_hits: List[Dict[str, Any]] = []
    try:
        for page in range(1, CENSYS_MAX_PAGES + 1):
            params["page"] = page
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                logging.warning("Censys API %s: %s", resp.status_code, resp.text[:500])
                break

            j = resp.json()
            hits = j.get("result", {}).get("hits", []) or []
            all_hits.extend(hits)
            logging.info("• Censys page %d: %d hits", page, len(hits))
            if not hits:
                break

        payload = {
            "source": "censys",
            "query": CENSYS_QUERY,
            "count": len(all_hits),
            "timestamp": fired_at
        }
        send_to_eventhub(CENSYS_EH_NAME, payload)
        logging.info("CensysTimer sent %d records to %s", len(all_hits), CENSYS_EH_NAME)

    except Exception as e:
        logging.exception("CensysTimer failed: %s", e)


# -------------------------------------------------------
# Timer Function: AbuseIPDB (every minute)
# -------------------------------------------------------
@app.schedule(
    schedule="0 * * * * *",          # every minute at second 0
    arg_name="mytimer",
    run_on_startup=True,
    use_monitor=False
)
def AbuseIPDBTimer(mytimer: func.TimerRequest) -> None:
    fired_at = datetime.datetime.utcnow().isoformat() + "Z"
    logging.info("AbuseIPDBTimer fired at %s", fired_at)

    if not ABUSE_API_KEY:
        logging.error("ABUSE_API_KEY missing; skipping.")
        return
    if not ABUSE_EH_NAME:
        logging.error("ABUSE_EH_NAME missing; skipping.")
        return

    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {
        "Key": ABUSE_API_KEY,
        "Accept": "application/json",
        "User-Agent": "cs532-azure-functions/1.0"
    }

    results: List[Dict[str, Any]] = []
    try:
        for ip in ABUSE_IP_LIST:
            try:
                resp = requests.get(url, headers=headers, params={"ipAddress": ip}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    results.append({"ip": ip, **data})
                    logging.info("• AbuseIPDB ok for %s", ip)
                else:
                    logging.warning("AbuseIPDB %s for %s: %s", resp.status_code, ip, resp.text[:500])
            except requests.RequestException as re:
                logging.warning("Network error querying AbuseIPDB for %s: %s", ip, re)

        payload = {
            "source": "abuseipdb",
            "count": len(results),
            "timestamp": fired_at,
            "ips": results
        }
        send_to_eventhub(ABUSE_EH_NAME, payload)
        logging.info("AbuseIPDBTimer sent %d records to %s", len(results), ABUSE_EH_NAME)

    except Exception as e:
        logging.exception("AbuseIPDBTimer failed: %s", e)
