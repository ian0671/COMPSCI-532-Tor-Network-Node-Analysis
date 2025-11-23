# Register this blueprint by adding the following line of code
# to your entry point file.
# app.register_functions(CollecTor_Get_Consensus)
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

CollecTor_Get_ExtraInfo_Descriptors = func.Blueprint()

# ---------------- PRODUCER ----------------
@CollecTor_Get_ExtraInfo_Descriptors.timer_trigger(
    schedule="0 8 0 * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def Get_ExtraInfo_Descriptors(myTimer: func.TimerRequest) -> None:
    logging.info("Get_ExtraInfo_Descriptors function started.")

    connection_str = os.getenv("EVENTHUB_CONNECTION")
    eventhub_name = os.getenv("Get_ExtraInfo_EH_NAME")

    if not connection_str or not eventhub_name:
        raise EnvironmentError("Missing Event Hub connection string or name.")

    producer = EventHubProducerClient.from_connection_string(
        conn_str=connection_str,
        eventhub_name=eventhub_name
    )

    try:
        descriptors = fetch_extrainfo_descriptors_since(hours_back=24, limit=None)
        logging.info("Collected %d extra info descriptors from CollecTor", len(descriptors))

        sent_count = 0
        with producer:
            batch: EventDataBatch = producer.create_batch()
            batch_event_count = 0

            for idx, desc in enumerate(descriptors):
                logging.debug("🔍 Extra Info Descriptors at index %d:\n%s",
                              idx, json.dumps(desc, indent=2, default=str))

                if not isinstance(desc, dict):
                    logging.warning("⛔ Skipping non-dict extra info descriptor at index %d: %s",
                                    idx, repr(desc))
                    continue

                tagged = {
                    "source": "Get_ExtraInfo_Descriptors",
                    "type": "extra_info_descriptor",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": desc
                }

                tagged_json = json.dumps(tagged, default=str).strip()
                if not tagged_json:
                    logging.warning("⛔ Skipping empty descriptor payload at index %d", idx)
                    continue

                logging.debug("📤 [%d] Sending extra info descriptor with fingerprint: %s\n%s",
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

        logging.info("✅ Sent %d extra info descriptors to Event Hub", sent_count)

        # 🔽 Immediately consume after producing
        consume_events(connection_str, eventhub_name, expected_count=sent_count, timeout=30)

    except Exception:
        logging.exception("❌ Scheduled CollecTor: get_extrainfo_descriptors send failed")
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
        consumer_group="get_extrainfo_descriptors_consumer_group",
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
def _normalize_extrainfo_descriptors(desc: Any) -> Dict[str, Any]:
    return {
        "nickname": getattr(desc, "nickname", None),
        "fingerprint": getattr(desc, "fingerprint", None),
        "published": getattr(desc, "published", None),
        "str": getattr(desc, "str", None),
        "signature": getattr(desc, "signature", None),
        "geoip_db_digest": getattr(desc, "geoip_db_digest", None),
        "geoip6_db_digest": getattr(desc, "geoip6_db_digest", None),
        "transport": getattr(desc, "transport", None),
        "conn_bi_direct_end": getattr(desc, "conn_bi_direct_end", None),
        "conn_bi_direct_interval": getattr(desc, "conn_bi_direct_interval", None),
        "conn_bi_direct_below": getattr(desc, "conn_bi_direct_below", None),
        "conn_bi_direct_read": getattr(desc, "conn_bi_direct_read", None),
        "conn_bi_direct_write": getattr(desc, "conn_bi_direct_write", None),
        "conn_bi_direct_both": getattr(desc, "conn_bi_direct_both", None),
        "read_history_end": getattr(desc, "read_history_end", None),
        "read_history_interval": getattr(desc, "read_history_interval", None),
        "read_history_values": getattr(desc, "read_history_values", None),
        "write_history_end": getattr(desc, "write_history_end", None),
        "write_history_interval": getattr(desc, "write_history_interval", None),
        "write_history_values": getattr(desc, "write_history_values", None),
        "cell_stats_end": getattr(desc, "cell_stats_end", None),
        "cell_stats_interval": getattr(desc, "cell_stats_interval", None),
        "cell_processed_cells": getattr(desc, "cell_processed_cells", None),
        "cell_queued_cells": getattr(desc, "cell_queued_cells", None),
        "cell_time_in_queue": getattr(desc, "cell_time_in_queue", None),
        "cell_circuits_per_decile": getattr(desc, "cell_circuits_per_decile", None),
        "dir_stats_end": getattr(desc, "dir_stats_end", None),
        "dir_stats_interval": getattr(desc, "dir_stats_interval", None),
        "dir_v2_ips": getattr(desc, "dir_v2_ips", None),
        "dir_v3_ips": getattr(desc, "dir_v3_ips", None),
        "dir_v2_share": getattr(desc, "dir_v2_share", None),
        "dir_v3_share": getattr(desc, "dir_v3_share", None),
        "dir_v2_requests": getattr(desc, "dir_v2_requests", None),
        "dir_v3_requests": getattr(desc, "dir_v3_requests", None),
        "dir_v2_responses": getattr(desc, "dir_v2_responses", None),
        "dir_v3_responses": getattr(desc, "dir_v3_responses", None),
        "dir_v2_responses_unknown": getattr(desc, "dir_v2_responses_unknown", None),
        "dir_v3_responses_unknown": getattr(desc, "dir_v3_responses_unknown", None),
        "dir_v2_direct_dl": getattr(desc, "dir_v2_direct_dl", None),
        "dir_v3_direct_dl": getattr(desc, "dir_v3_direct_dl", None),
        "dir_v2_direct_dl_unknown": getattr(desc, "dir_v2_direct_dl_unknown", None),
        "dir_v3_direct_dl_unknown": getattr(desc, "dir_v3_direct_dl_unknown", None),
        "dir_v2_tunneled_dl": getattr(desc, "dir_v2_tunneled_dl", None),
        "dir_v3_tunneled_dl": getattr(desc, "dir_v3_tunneled_dl", None),
        "dir_v2_tunneled_dl_unknown": getattr(desc, "dir_v2_tunneled_dl_unknown", None),
        "dir_v3_tunneled_dl_unknown": getattr(desc, "dir_v3_tunneled_dl_unknown", None),
        "dir_read_history_end": getattr(desc, "dir_read_history_end", None),
        "dir_read_history_interval": getattr(desc, "dir_read_history_interval", None),  
        "dir_read_history_values": getattr(desc, "dir_read_history_values", None),
        "dir_write_history_end": getattr(desc, "dir_write_history_end", None),
        "dir_write_history_interval": getattr(desc, "dir_write_history_interval", None),
        "dir_write_history_values": getattr(desc, "dir_write_history_values", None),
        "entry_stats_end": getattr(desc, "entry_stats_end", None),
        "entry_stats_interval": getattr(desc, "entry_stats_interval", None),
        "entry_ips": getattr(desc, "entry_ips", None),
        "exit_stats_end": getattr(desc, "exit_stats_end", None),
        "exit_stats_interval": getattr(desc, "exit_stats_interval", None),
        "exit_kibibytes_written": getattr(desc, "exit_kibibytes_written", None),
        "exit_kibibytes_read": getattr(desc, "exit_kibibytes_read", None),
        "exit_streams_opened": getattr(desc, "exit_streams_opened", None),
        "hs_stats_end": getattr(desc, "hs_stats_end", None),
        "hs_rend_cells": getattr(desc, "hs_rend_cells", None),
        "hs_rend_cells_attr": getattr(desc, "hs_rend_cells_attr", None),
        "hs_dir_onions_seen": getattr(desc, "hs_dir_onions_seen", None),
        "hs_dir_onions_seen_attr": getattr(desc, "hs_dir_onions_seen_attr", None),
        "padding_counts": getattr(desc, "padding_counts", None),
        "padding_counts_end": getattr(desc, "padding_counts_end", None),
        "padding_counts_interval": getattr(desc, "padding_counts_interval", None),
        "bridge_stats_end": getattr(desc, "bridge_stats_end", None),
        "bridge_stats_interval": getattr(desc, "bridge_stats_interval", None),
        "bridge_ips": getattr(desc, "bridge_ips", None),
        "geoip_start_time": getattr(desc, "geoip_start_time", None),
        "geoip_client_origins": getattr(desc, "geoip_client_origins", None),
        "ip_versions": getattr(desc, "ip_versions", None),
        "ed25519_certificate_hash": getattr(desc, "ed25519_certificate_hash", None),
        "router_digest_sha256": getattr(desc, "router_digest_sha256", None),
    }

def aware_to_naive_utc(dt: datetime) -> datetime:
    """Convert an aware UTC datetime to a naive UTC datetime for Stem calls."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def get_aware_utc_start(hours_back: int = 24) -> datetime:
    """Return an aware UTC datetime representing now minus hours_back."""
    return datetime.now(timezone.utc) - timedelta(hours=hours_back)

def fetch_extrainfo_descriptors_since(hours_back: int = 24,
                          limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch server descriptors published since (now - hours_back) and normalize them.
    Uses aware UTC in application logic, converts to naive UTC for Stem call.
    """
    from stem.descriptor.collector import get_extrainfo_descriptors

    aware_start = get_aware_utc_start(hours_back)
    naive_start = aware_to_naive_utc(aware_start)

    raw_iter = get_extrainfo_descriptors(start=naive_start)

    results = list(raw_iter)
    if limit is not None:
        results = results[:limit]

    return [_normalize_extrainfo_descriptors(r) for r in results]