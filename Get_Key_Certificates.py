# Register this blueprint by adding the following line of code
# to your entry point file.
# app.register_functions(CollecTor_Get_Key_Certificates)
#
# Please refer to https://aka.ms/azure-functions-python-blueprints

import os
import json
import logging

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from contextlib import suppress

import azure.functions as func
from azure.eventhub import (
    EventData,
    EventDataBatch,
    EventHubProducerClient,
    EventHubConsumerClient
)

CollecTor_Get_Key_Certificates = func.Blueprint()

# ---------------- PRODUCER ----------------
@CollecTor_Get_Key_Certificates.timer_trigger(
    schedule="0 4 0 * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def Get_Key_Certificates(myTimer: func.TimerRequest) -> None:
    logging.info("Get_Key_Certificates function started.")

    connection_str = os.getenv("EVENTHUB_CONNECTION")
    eventhub_name = os.getenv("Get_Key_Certificates_EH_NAME")

    if not connection_str or not eventhub_name:
        raise EnvironmentError("Missing Event Hub connection string or name.")

    producer = EventHubProducerClient.from_connection_string(
        conn_str=connection_str,
        eventhub_name=eventhub_name
    )

    try:
        descriptors = fetch_key_certificates_since(hours_back=24, limit=None)
        logging.info("Collected %d key certificates from CollecTor", len(descriptors))

        sent_count = 0
        with producer:
            batch: EventDataBatch = producer.create_batch()
            batch_event_count = 0

            for idx, desc in enumerate(descriptors):
                logging.debug("🔍 Key certificate at index %d:\n%s",
                              idx, json.dumps(desc, indent=2, default=str))

                if not isinstance(desc, dict):
                    logging.warning("⛔ Skipping non-dict key certificate at index %d: %s",
                                    idx, repr(desc))
                    continue

                tagged = {
                    "source": "Get_Key_Certificates",
                    "type": "key_certificate",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": desc
                }

                tagged_json = json.dumps(tagged, default=str).strip()
                if not tagged_json:
                    logging.warning("⛔ Skipping empty descriptor payload at index %d", idx)
                    continue

                logging.debug("📤 [%d] Sending key certificate with fingerprint: %s\n%s",
                              idx,
                              desc.get("fingerprint", "unknown"),
                              tagged_json)

                data = EventData(tagged_json)

                try:
                    batch.add(data)
                    batch_event_count += 1
                except ValueError:
                    producer.send_batch(batch)
                    sent_count += batch_event_count
                    batch = producer.create_batch()
                    batch_event_count = 0
                    batch.add(data)
                    batch_event_count = 1

            if batch_event_count > 0:
                producer.send_batch(batch)
                sent_count += batch_event_count

        logging.info("✅ Sent %d key certificates to Event Hub", sent_count)

        # 🔽 Immediately consume after producing
        consume_events(connection_str, eventhub_name,
                                 expected_count=sent_count, timeout=30)

    except Exception:
        logging.exception("❌ Scheduled CollecTor: get_key_certificates send failed")
        raise
    finally:
        with suppress(Exception):
            producer.close()

# ---------------- CONSUMER ----------------
def consume_events(connection_str: str, eventhub_name: str,
                             expected_count: Optional[int] = None,
                             timeout: int = 30):
    """
    Consumer client that runs immediately after producer.
    Stops after expected_count events or after timeout seconds.
    """

    client = EventHubConsumerClient.from_connection_string(
        conn_str=connection_str,
        consumer_group="get_key_certificates_consumer_group",  # ensure this exists
        eventhub_name=eventhub_name
    )

    received = {"count": 0, "stop": False}

    def on_event(partition_context, event):
        logging.info("📥 Received event from partition %s, offset %s",
                     partition_context.partition_id, event.offset)
        logging.debug("Payload: %s", event.body_as_str())

        partition_context.update_checkpoint(event)
        received["count"] += 1

        if expected_count and received["count"] >= expected_count:
            logging.info("✅ Consumer reached expected count (%d), stopping.", expected_count)
            received["stop"] = True
            client.close()

    try:
        with client:
            client.receive(
                on_event=on_event,
                starting_position="-1",   # read from beginning
                max_wait_time=timeout
            )
    except Exception:
        logging.exception("❌ EventHubConsumerClient failed")
        raise

# ---------------- HELPERS ----------------
def _normalize_key_certificates(desc: Any) -> Dict[str, Any]:
    return {
        "onion_key": getattr(desc, "onion_key", None),
        "version": getattr(desc, "version", None),
        "address": getattr(desc, "address", None),
        "dir_port": getattr(desc, "dir_port", None),
        "fingerprint": getattr(desc, "fingerprint", None),
        "identity_key": getattr(desc, "identity_key", None),
        "published": getattr(desc, "published", None),
        "expires": getattr(desc, "expires", None),
        "signing_key": getattr(desc, "signing_key", None),
        "crosscert": getattr(desc, "crosscert", None),
        "certification": getattr(desc, "certification", None),
    }

def aware_to_naive_utc(dt: datetime) -> datetime:
    """Convert an aware UTC datetime to a naive UTC datetime for Stem calls."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def get_aware_utc_start(hours_back: int = 24) -> datetime:
    """Return an aware UTC datetime representing now minus hours_back."""
    return datetime.now(timezone.utc) - timedelta(hours=hours_back)

def fetch_key_certificates_since(hours_back: int = 24,
                                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch key certificates published since (now - hours_back) and normalize them.
    Uses aware UTC in application logic, converts to naive UTC for Stem call.
    """
    from stem.descriptor.collector import get_key_certificates

    aware_start = get_aware_utc_start(hours_back)
    naive_start = aware_to_naive_utc(aware_start)

    raw_iter = get_key_certificates(start=naive_start)

    results = list(raw_iter)
    if limit is not None:
        results = results[:limit]

    return [_normalize_key_certificates(r) for r in results]