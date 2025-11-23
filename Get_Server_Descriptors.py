# Register this blueprint by adding the following line of code
# to your entry point file.
# app.register_functions(CollecTor_Get_Server_Descriptors)
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

CollecTor_Get_Server_Descriptors = func.Blueprint()

# ---------------- PRODUCER ----------------
@CollecTor_Get_Server_Descriptors.timer_trigger(
    schedule="0 0 0 * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def Get_Server_Descriptors(myTimer: func.TimerRequest) -> None:
    logging.info("Get_Server_Descriptors function started.")

    connection_str = os.getenv("EVENTHUB_CONNECTION")
    eventhub_name = os.getenv("Get_Server_Descriptors_EH_NAME")

    if not connection_str or not eventhub_name:
        raise EnvironmentError("Missing Event Hub connection string or name.")

    producer = EventHubProducerClient.from_connection_string(
        conn_str=connection_str,
        eventhub_name=eventhub_name
    )

    try:
        descriptors = fetch_server_descriptors_since(hours_back=24, limit=None)
        logging.info("Collected %d server descriptors from CollecTor", len(descriptors))

        sent_count = 0
        with producer:
            batch: EventDataBatch = producer.create_batch()
            batch_event_count = 0

            for idx, desc in enumerate(descriptors):
                logging.debug("🔍 Descriptor at index %d:\n%s",
                              idx, json.dumps(desc, indent=2, default=str))

                if not isinstance(desc, dict):
                    logging.warning("⛔ Skipping non-dict descriptor at index %d: %s",
                                    idx, repr(desc))
                    continue

                tagged = {
                    "source": "Get_Server_Descriptors",
                    "type": "server_descriptor",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": desc
                }

                tagged_json = json.dumps(tagged, default=str).strip()
                if not tagged_json:
                    logging.warning("⛔ Skipping empty descriptor payload at index %d", idx)
                    continue

                logging.debug("📤 [%d] Sending descriptor with fingerprint: %s\n%s",
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

        logging.info("✅ Sent %d server descriptors to Event Hub", sent_count)

        # 🔽 Immediately consume after producing
        consume_events(connection_str, eventhub_name, expected_count=sent_count, timeout=30)

    except Exception:
        logging.exception("❌ Scheduled CollecTor: get_server_descriptors send failed")
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
        consumer_group="get_server_descriptors_consumer_group",  # ensure this exists
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
                max_wait_time=timeout     # stop if no events arrive within timeout
            )
    except Exception:
        logging.exception("❌ EventHubConsumerClient failed")
        raise

# ---------------- HELPERS ----------------
def _normalize_server_descriptors(desc: Any) -> Dict[str, Any]:
    return {
        "nickname": getattr(desc, "nickname", None),
        "fingerprint": getattr(desc, "fingerprint", None),
        "published": getattr(desc, "published", None),
        "address": getattr(desc, "address", None),
        "or_port": getattr(desc, "or_port", None),
        "socks_port": getattr(desc, "socks_port", None),
        "dir_port": getattr(desc, "dir_port", None),
        "platform": getattr(desc, "platform", None),
        "tor_version": getattr(desc, "tor_version", None),
        "operating_system": getattr(desc, "operating_system", None),
        "uptime": getattr(desc, "uptime", None),
        "contact": getattr(desc, "contact", None),
        "exit_policy": getattr(desc, "exit_policy", None),
        "exit_policy_v6": getattr(desc, "exit_policy_v6", None),
        "bridge_distribution": getattr(desc, "bridge_distribution", None),
        "family": getattr(desc, "family", None),
        "average_bandwidth": getattr(desc, "average_bandwidth", None),
        "burst_bandwidth": getattr(desc, "burst_bandwidth", None),
        "observed_bandwidth": getattr(desc, "observed_bandwidth", None),
        "link_protocols": getattr(desc, "link_protocols", None),
        "circuit_protocols": getattr(desc, "circuit_protocols", None),
        "is_hidden_service_dir": getattr(desc, "is_hidden_service_dir", None),
        "hibernating": getattr(desc, "hibernating", None),
        "allow_single_hop_exits": getattr(desc, "allow_single_hop_exits", None),
        "allow_tunneled_dir_requests": getattr(desc, "allow_tunneled_dir_requests", None),
        "extra_info_cache": getattr(desc, "extra_info_cache", None),
        "extra_info_digest": getattr(desc, "extra_info_digest", None),
        "extra_info_sha256_digest": getattr(desc, "extra_info_sha256_digest", None),
        "eventdns": getattr(desc, "eventdns", None),
        "ntor_onion_key": getattr(desc, "ntor_onion_key", None),
        "or_addresses_v6": getattr(desc, "or_addresses_v6", None),
        "protocols": getattr(desc, "protocols", None),
    }

def aware_to_naive_utc(dt: datetime) -> datetime:
    """Convert an aware UTC datetime to a naive UTC datetime for Stem calls."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def get_aware_utc_start(hours_back: int = 24) -> datetime:
    """Return an aware UTC datetime representing now minus hours_back."""
    return datetime.now(timezone.utc) - timedelta(hours=hours_back)

def fetch_server_descriptors_since(hours_back: int = 24,
                                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch server descriptors published since (now - hours_back) and normalize them.
    Uses aware UTC in application logic, converts to naive UTC for Stem call.
    """
    from stem.descriptor.collector import get_server_descriptors

    aware_start = get_aware_utc_start(hours_back)
    naive_start = aware_to_naive_utc(aware_start)

    raw_iter = get_server_descriptors(start=naive_start)

    results = list(raw_iter)
    if limit is not None:
        results = results[:limit]

    return [_normalize_server_descriptors(r) for r in results]