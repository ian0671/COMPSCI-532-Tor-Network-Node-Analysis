# Register this blueprint by adding the following line of code
# to your entry point file.
# app.register_functions(CollecTor_Get_Exit_Lists)
# Refer to https://aka.ms/azure-functions-python-blueprints

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

CollecTor_Get_Exit_Lists = func.Blueprint()

# ---------------- PRODUCER ----------------
@CollecTor_Get_Exit_Lists.timer_trigger(
    schedule="0 10 0 * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def Get_Exit_Lists(myTimer: func.TimerRequest) -> None:
    logging.info("Get_Exit_Lists function started.")

    connection_str = os.getenv("EVENTHUB_CONNECTION")
    eventhub_name = os.getenv("Get_Exit_Lists_EH_NAME")

    if not connection_str or not eventhub_name:
        raise EnvironmentError("Missing Event Hub connection string or name.")

    producer = EventHubProducerClient.from_connection_string(
        conn_str=connection_str,
        eventhub_name=eventhub_name
    )

    try:
        descriptors = fetch_exit_lists_since(hours_back=24, limit=None)
        logging.info("Collected %d exit lists from CollecTor", len(descriptors))

        sent_count = 0
        with producer:
            batch: EventDataBatch = producer.create_batch()
            batch_event_count = 0

            for idx, desc in enumerate(descriptors):
                logging.debug("🔍 Exit list at index %d:\n%s",
                              idx, json.dumps(desc, indent=2, default=str))

                if not isinstance(desc, dict):
                    logging.warning("⛔ Skipping non-dict exit list at index %d: %s",
                                    idx, repr(desc))
                    continue

                tagged = {
                    "source": "Get_Exit_Lists",
                    "type": "exit_list",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": desc
                }


                tagged_json = json.dumps(tagged, default=str).strip()
                if not tagged_json:
                    logging.warning("⛔ Skipping empty descriptor payload at index %d", idx)
                    continue

                logging.debug("📤 [%d] Sending exit list with relay: %s\n%s",
                              idx,
                              desc.get("relay", "unknown"),
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

        logging.info("✅ Sent %d exit lists to Event Hub", sent_count)

        consume_events(connection_str, eventhub_name, expected_count=sent_count, timeout=30)

    except Exception:
        logging.exception("❌ Scheduled CollecTor: get_exit_lists send failed")
        raise
    finally:
        with suppress(Exception):
            producer.close()

# ---------------- CONSUMER ----------------
def consume_events(connection_str: str, eventhub_name: str,
                   expected_count: Optional[int] = None,
                   timeout: int = 30):
    client = EventHubConsumerClient.from_connection_string(
        conn_str=connection_str,
        consumer_group="get_exit_lists_consumer_group",
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
                starting_position="-1",
                max_wait_time=timeout
            )
    except Exception:
        logging.exception("❌ EventHubConsumerClient failed")
        raise

# ---------------- HELPERS ----------------
def _normalize_exit_list(desc: Any) -> Dict[str, Any]: 
    return { 
        "fingerprint": getattr(desc, "fingerprint", None), 
        "published": getattr(desc, "published", None), 
        "last_status": getattr(desc, "last_status", None), 
        "exit_addresses": getattr(desc, "exit_addresses", None), 
        }

def aware_to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def get_aware_utc_start(hours_back: int = 24) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours_back)

def fetch_exit_lists_since(hours_back: int = 24,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
    from stem.descriptor.collector import get_exit_lists

    aware_start = get_aware_utc_start(hours_back)
    naive_start = aware_to_naive_utc(aware_start)

    raw_iter = get_exit_lists(start=naive_start)

    results = list(raw_iter)
    if limit is not None:
        results = results[:limit]

    return [_normalize_exit_list(r) for r in results]