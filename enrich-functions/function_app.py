import datetime
import json
import logging
import os
from typing import Dict, Any, List, Optional

import requests
import azure.functions as func
from azure.eventhub import EventHubProducerClient, EventData, EventHubConsumerClient
import azure.durable_functions as df
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient


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
        logging.warning(f" Invalid int for {name}='{raw}', using default {default}")
        return default


# Read settings once at import time
EVENTHUB_CONNECTION = _get_env("EVENTHUB_CONNECTION")  # namespace conn string (no EntityPath)
ABUSE_EH_NAME = _get_env("ABUSE_EH_NAME")              # e.g., 'abuseipdbdata'
CENSYS_EH_NAME = _get_env("CENSYS_EH_NAME")            # e.g., 'censysdata'

# Consumer groups (for orchestrator + validator)
ABUSE_CONSUMER_GROUP = os.environ.get("ABUSE_CONSUMER_GROUP", "$Default")
CENSYS_CONSUMER_GROUP = os.environ.get("CENSYS_CONSUMER_GROUP", "$Default")
VALIDATOR_CONSUMER_GROUP = os.environ.get("VALIDATOR_CONSUMER_GROUP", "$Default")

# Joined output target
JOINED_OUTPUT_TARGET = os.environ.get("JOINED_OUTPUT_TARGET", "eventhub").lower()  # 'eventhub' | 'adls'
JOINED_EH_NAME = os.environ.get("JOINED_EH_NAME", "joinedrecords")

# ADLS Gen2 settings (for either sink or validator)
ADLS_ACCOUNT_URL = os.environ.get("ADLS_ACCOUNT_URL")  # e.g. https://<account>.dfs.core.windows.net
ADLS_FILESYSTEM = os.environ.get("ADLS_FILESYSTEM", "cs532")
ADLS_DIR_BASE = os.environ.get("ADLS_DIR_BASE", "tor-pipeline")

ABUSE_API_KEY = _get_env("ABUSE_API_KEY")
ABUSE_IP_LIST: List[str] = [x.strip() for x in os.environ.get("ABUSE_IP_LIST", "8.8.8.8,1.1.1.1").split(",") if x.strip()]

CENSYS_API_TOKEN = _get_env("CENSYS_API_TOKEN")
CENSYS_QUERY = os.environ.get("CENSYS_QUERY", "services.service_name:HTTP")
CENSYS_PER_PAGE = _get_env_int("CENSYS_PER_PAGE", 50)
CENSYS_MAX_PAGES = _get_env_int("CENSYS_MAX_PAGES", 1)

# Light config echo (redacted)
logging.info(
    " Config: ABUSE_EH_NAME=%s, CENSYS_EH_NAME=%s, ABUSE_IP_COUNT=%d, CENSYS_PER_PAGE=%d, CENSYS_MAX_PAGES=%d",
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
# Helper: Write JSON to ADLS (append-create)
# -------------------------------------------------------
def _adls_client() -> Optional[DataLakeServiceClient]:
    if not ADLS_ACCOUNT_URL:
        logging.error("ADLS_ACCOUNT_URL missing; cannot write to ADLS.")
        return None
    try:
        cred = DefaultAzureCredential()
        return DataLakeServiceClient(account_url=ADLS_ACCOUNT_URL, credential=cred)
    except Exception:
        logging.exception("Failed to create ADLS client")
        return None


def write_json_to_adls(records: List[Dict[str, Any]], subdir: str, filename: Optional[str] = None) -> Optional[str]:
    if not records:
        logging.info("No records to write to ADLS for %s", subdir)
        return None
    if not (svc := _adls_client()):
        return None

    ts = datetime.datetime.utcnow()
    parts = [
        ADLS_DIR_BASE.rstrip("/"),
        subdir.strip("/"),
        f"dt={ts.strftime('%Y-%m-%d')}",
        f"hour={ts.strftime('%H')}",
    ]
    dir_path = "/".join([p for p in parts if p])
    file_name = filename or f"part-{ts.strftime('%M%S')}.json"
    try:
        fs = svc.get_file_system_client(file_system=ADLS_FILESYSTEM)
        dir_client = fs.get_directory_client(dir_path)
        dir_client.create_directory()  # idempotent
        file_client = dir_client.get_file_client(file_name)
        data = ("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in records)).encode("utf-8")
        file_client.create_file()
        file_client.append_data(data=data, offset=0, length=len(data))
        file_client.flush_data(len(data))
        path = f"abfss://{ADLS_FILESYSTEM}@{ADLS_ACCOUNT_URL.split('://')[1]}/{dir_path}/{file_name}"
        logging.info("Wrote %d records to ADLS at %s", len(records), path)
        return path
    except Exception:
        logging.exception("Failed writing to ADLS %s/%s", dir_path, file_name)
        return None


# -------------------------------------------------------
# Timer Function: Censys (every 30 minutes)
# -------------------------------------------------------
@app.schedule(
    schedule="0 */30 * * * *",       # every 30 minutes at minute 0,30 (free tier friendly)
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

        # reduce/normalize: only keep minimal host info for joining (IP + optional location/service names)
        minimal_hosts: List[Dict[str, Any]] = []
        for h in all_hits:
            host_ip = h.get("ip") or h.get("ip_address")
            if not host_ip:
                continue
            minimal_hosts.append({
                "ip": host_ip,
                "location": h.get("location", {}),
                "services": [s.get("service_name") for s in (h.get("services") or []) if isinstance(s, dict) and s.get("service_name")]
            })

        payload = {
            "source": "censys",
            "query": CENSYS_QUERY,
            "count": len(minimal_hosts),
            "timestamp": fired_at
        }
        # include small host sample to support joins
        if minimal_hosts:
            payload["hosts"] = minimal_hosts[:500]  # cap size
        send_to_eventhub(CENSYS_EH_NAME, payload)
        logging.info("CensysTimer sent %d hosts to %s", len(minimal_hosts), CENSYS_EH_NAME)

    except Exception as e:
        logging.exception("CensysTimer failed: %s", e)


# -------------------------------------------------------
# Timer Function: AbuseIPDB (every minute)
# -------------------------------------------------------
@app.schedule(
    schedule="0 */30 * * * *",       # every 30 minutes at minute 0,30 (free tier friendly)
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


# ---------------------------
# ----------------------------
# Durable Functions Orchestrator and Activities (Simplified)
# -------------------------------------------------------

# Simple timer that manually orchestrates the join process
@app.schedule(
    schedule="0 */5 * * * *",        # every 5 minutes
    arg_name="timer", 
    run_on_startup=False,
    use_monitor=False
)
def SimpleOrchestrator(timer: func.TimerRequest) -> None:
    """Simple orchestrator that reads from Event Hubs, joins data, and sinks to configured target."""
    logging.info("SimpleOrchestrator triggered at %s", datetime.datetime.utcnow().isoformat())
    
    try:
        # Fetch abuse data
        abuse_records = fetch_abuse_batch_simple()
        logging.info("Fetched %d abuse records", len(abuse_records))
        
        # Fetch censys data  
        censys_records = fetch_censys_batch_simple()
        logging.info("Fetched %d censys records", len(censys_records))
        
        # Join the data
        joined_records = join_and_enrich_simple({"abuse": abuse_records, "censys": censys_records})
        logging.info("Created %d joined records", len(joined_records))
        
        # Sink the results
        if joined_records:
            sink_result = sink_joined_simple(joined_records)
            logging.info("Orchestrator completed: %s", sink_result)
        else:
            logging.info("No joined records to sink")
            
    except Exception as e:
        logging.exception("SimpleOrchestrator failed: %s", e)


def fetch_abuse_batch_simple() -> List[Dict[str, Any]]:
    """Simplified version without Durable Functions decorators."""
    if not (EVENTHUB_CONNECTION and ABUSE_EH_NAME):
        logging.error("Missing Event Hub settings for AbuseIPDB")
        return []

    records: List[Dict[str, Any]] = []
    def on_event(partition_context, event):
        try:
            if event is None:
                logging.warning("Received None event from AbuseIPDB Event Hub")
                return
            body = event.body_as_str()
            j = json.loads(body)
            if j.get("source") == "abuseipdb":
                for ipr in j.get("ips", []) or []:
                    rec = {"ip": ipr.get("ip") or ipr.get("ipAddress"), **{k:v for k,v in ipr.items() if k != "ip"}}
                    if rec.get("ip"):
                        records.append(rec)
        except Exception:
            logging.exception("Error parsing AbuseIPDB event")

    try:
        client = EventHubConsumerClient.from_connection_string(
            conn_str=EVENTHUB_CONNECTION,
            consumer_group=ABUSE_CONSUMER_GROUP,
            eventhub_name=ABUSE_EH_NAME,
        )
        with client:
            client.receive(on_event=on_event, max_wait_time=5, starting_position="@latest")
    except Exception:
        logging.exception("Abuse consumer failed")
    return records


def fetch_censys_batch_simple() -> List[Dict[str, Any]]:
    """Simplified version without Durable Functions decorators."""
    if not (EVENTHUB_CONNECTION and CENSYS_EH_NAME):
        logging.error("Missing Event Hub settings for Censys")
        return []
    hosts: List[Dict[str, Any]] = []

    def on_event(partition_context, event):
        try:
            if event is None:
                logging.warning("Received None event from Censys Event Hub")
                return
            j = json.loads(event.body_as_str())
            if j.get("source") == "censys":
                for h in j.get("hosts", []) or []:
                    ip = h.get("ip") or h.get("ip_address")
                    if ip:
                        hosts.append({"ip": ip, "services": h.get("services", []), "location": h.get("location", {})})
        except Exception:
            logging.exception("Error parsing Censys event")

    try:
        client = EventHubConsumerClient.from_connection_string(
            conn_str=EVENTHUB_CONNECTION,
            consumer_group=CENSYS_CONSUMER_GROUP,
            eventhub_name=CENSYS_EH_NAME,
        )
        with client:
            client.receive(on_event=on_event, max_wait_time=5, starting_position="@latest")
    except Exception:
        logging.exception("Censys consumer failed")
    return hosts


def join_and_enrich_simple(payload: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Simplified join logic without Durable Functions."""
    abuse = payload.get("abuse", [])
    censys = payload.get("censys", [])
    abuse_map: Dict[str, Dict[str, Any]] = {a["ip"]: a for a in abuse if a.get("ip")}
    out: List[Dict[str, Any]] = []
    for h in censys:
        ip = h.get("ip")
        if not ip:
            continue
        rec = {
            "ip": ip,
            "joined_at": datetime.datetime.utcnow().isoformat() + "Z",
            "abuse": abuse_map.get(ip),
            "censys": {
                "services": h.get("services"),
                "location": h.get("location"),
            },
        }
        out.append(rec)
    # include any abuse-only IPs (no Censys match)
    censys_ips = {h.get("ip") for h in censys if h.get("ip")}
    for ip, a in abuse_map.items():
        if ip not in censys_ips:
            out.append({
                "ip": ip,
                "joined_at": datetime.datetime.utcnow().isoformat() + "Z",
                "abuse": a,
                "censys": None,
            })
    return out


def sink_joined_simple(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Simplified sink without Durable Functions."""
    if not records:
        return {"count": 0, "sink": JOINED_OUTPUT_TARGET}
    if JOINED_OUTPUT_TARGET == "eventhub":
        if not (EVENTHUB_CONNECTION and JOINED_EH_NAME):
            logging.error("JOINED_EH_NAME/EVENTHUB_CONNECTION missing")
            return {"count": 0, "sink": "eventhub", "error": "config"}
        # send in chunks to respect size limits
        max_batch = 100
        sent = 0
        for i in range(0, len(records), max_batch):
            chunk = records[i:i+max_batch]
            payload = {
                "source": "join",
                "count": len(chunk),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "records": chunk,
            }
            send_to_eventhub(JOINED_EH_NAME, payload)
            sent += len(chunk)
        return {"count": sent, "sink": "eventhub"}
    else:
        # ADLS
        path = write_json_to_adls(records, subdir="processed/joined")
        return {"count": len(records), "sink": "adls", "path": path}


# -------------------------------------------------------
# Validation: consume joined Event Hub and store validated data to ADLS
# -------------------------------------------------------

# Validation: Simple timer to test function registration 
@app.schedule(
    schedule="0 */10 * * * *",      # every 10 minutes
    arg_name="timer",
    run_on_startup=False,
    use_monitor=False
)
def ValidateAndStore(timer: func.TimerRequest) -> None:
    """Simple validation timer for testing function registration."""
    logging.info("ValidateAndStore timer executed at %s", datetime.datetime.utcnow().isoformat())
    
    # For now, just log that we're running
    if timer.past_due:
        logging.info('ValidateAndStore timer is past due')
    
    # TODO: Replace with actual Event Hub consumption logic when EventHub trigger works
    logging.info(" ValidateAndStore function is running successfully")
    
    # Placeholder for validation logic - we'll convert back to EventHub trigger later
    try:
        # For now, just write a test file to ADLS to verify connection
        test_data = [{"test": True, "timestamp": datetime.datetime.utcnow().isoformat()}]
        path = write_json_to_adls(test_data, subdir="test/validator")
        logging.info("Test data written to ADLS: %s", path)
    except Exception:
        logging.exception("Failed to write test data to ADLS")
