import os, json, time, logging, datetime, requests
import azure.functions as func
from azure.eventhub import EventHubProducerClient, EventData

app = func.FunctionApp()

# --------------------------
# Helpers
# --------------------------

def _http_get(url, *, params=None, headers=None, timeout=30, retries=3, backoff=2):
    """GET with basic retry on 5xx/429."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"Retryable status {r.status_code}: {r.text}")
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            if attempt < retries:
                sleep_s = backoff ** (attempt - 1)
                logging.warning("GET %s failed (attempt %d/%d): %s; retrying in %ss",
                                url, attempt, retries, e, sleep_s)
                time.sleep(sleep_s)
            else:
                logging.error("GET %s failed after %d attempts: %s", url, retries, e)
    raise last_exc

def _send_records_to_eventhub(records, *, conn_str, hub_name):
    producer = EventHubProducerClient.from_connection_string(conn_str, eventhub_name=hub_name)
    sent = 0
    try:
        batch = producer.create_batch()
        for rec in records:
            payload = json.dumps(rec)
            try:
                batch.add(EventData(payload))
                sent += 1
            except ValueError:
                producer.send_batch(batch)
                batch = producer.create_batch()
                batch.add(EventData(payload))
                sent += 1
        if len(batch) > 0:
            producer.send_batch(batch)
    finally:
        producer.close()
    return sent


# ---------------------------------
# CENSYS (token-based, paginated)
# ---------------------------------
@app.function_name(name="CensysTimer")
@app.schedule(schedule="0 5 * * * *", arg_name="mytimer", run_on_startup=False, use_monitor=True)  # hourly at :05 UTC
def censys_timer(mytimer: func.TimerRequest) -> None:
    logging.info("CensysTimer fired at %s", datetime.datetime.utcnow().isoformat())

    # Required env
    token   = os.getenv("CENSYS_API_TOKEN")
    eh_conn = os.getenv("EVENTHUB_CONNECTION")
    eh_name = os.getenv("CENSYS_EH_NAME")

    if not all([token, eh_conn, eh_name]):
        logging.error("Missing env vars (CENSYS_API_TOKEN, EVENTHUB_CONNECTION, CENSYS_EH_NAME)")
        return

    # Optional tuning
    query     = os.getenv("CENSYS_QUERY", "services.service_name:HTTP")
    per_page  = int(os.getenv("CENSYS_PER_PAGE", "50"))
    max_pages = int(os.getenv("CENSYS_MAX_PAGES", "1"))  # raise for more data; mind rate limits

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "cs532-tor-pipeline/1.0"
    }

    all_recs = []
    for page in range(1, max_pages + 1):
        params = {"q": query, "per_page": per_page, "page": page}
        try:
            r = _http_get("https://search.censys.io/api/v2/hosts/search",
                          params=params, headers=headers, timeout=30, retries=3, backoff=2)
            body = r.json() or {}
            hits = (body.get("result") or {}).get("hits", []) or []
        except Exception as e:
            logging.exception("Censys page %d failed: %s", page, e)
            break

        if not hits:
            logging.info("Censys page %d returned 0 hits; stopping pagination.", page)
            break

        run_id = int(datetime.datetime.utcnow().timestamp())
        for h in hits:
            all_recs.append({
                "source": "censys",
                "ip": h.get("ip"),
                "asn": (h.get("autonomous_system") or {}).get("asn"),
                "country": (h.get("location") or {}).get("country"),
                "seen_at": h.get("last_updated_at"),
                "run_id": run_id,
                "q": query,
                "page": page,
            })

    if not all_recs:
        logging.warning("Censys returned no records for query='%s'", query)
        return

    sent = _send_records_to_eventhub(all_recs, conn_str=eh_conn, hub_name=eh_name)
    logging.info("✅ CensysTimer sent %d/%d records to %s (query='%s', pages=%d)",
                 sent, len(all_recs), eh_name, query, min(max_pages, (len(all_recs) + per_page - 1) // per_page))


# -------------------------
# AbuseIPDB (batched)
# -------------------------
@app.function_name(name="AbuseIPDBTimer")
@app.schedule(schedule="0 10 * * * *", arg_name="mytimer", run_on_startup=False, use_monitor=True)  # hourly at :10 UTC
def abuseipdb_timer(mytimer: func.TimerRequest) -> None:
    logging.info("AbuseIPDBTimer fired at %s", datetime.datetime.utcnow().isoformat())

    api_key = os.getenv("ABUSE_API_KEY")
    ip_list = [x.strip() for x in os.getenv("ABUSE_IP_LIST", "8.8.8.8,1.1.1.1").split(",") if x.strip()]
    eh_conn = os.getenv("EVENTHUB_CONNECTION")
    eh_name = os.getenv("ABUSE_EH_NAME")

    if not all([api_key, eh_conn, eh_name]):
        logging.error("Missing env vars (ABUSE_API_KEY, EVENTHUB_CONNECTION, ABUSE_EH_NAME)")
        return

    headers = {"Key": api_key, "Accept": "application/json", "User-Agent": "cs532-tor-pipeline/1.0"}
    results = []
    run_id = int(datetime.datetime.utcnow().timestamp())

    for ip in ip_list:
        try:
            r = _http_get("https://api.abuseipdb.com/api/v2/check",
                          params={"ipAddress": ip}, headers=headers, timeout=20, retries=3, backoff=2)
            payload = r.json() or {}
            results.append({
                "source": "abuseipdb",
                "ip": ip,
                "run_id": run_id,
                "data": payload
            })
        except Exception as e:
            logging.exception("AbuseIPDB request failed for %s: %s", ip, e)

    if not results:
        logging.warning("AbuseIPDB produced no records (ip_list=%s)", ",".join(ip_list))
        return

    sent = _send_records_to_eventhub(results, conn_str=eh_conn, hub_name=eh_name)
    logging.info("✅ AbuseIPDBTimer sent %d/%d records to %s", sent, len(results), eh_name)
