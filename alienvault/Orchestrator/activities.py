import logging
from eventhub_utils import receive_eventhub_batch

def read_eventhub_activity(source_name: str) -> list:
    logging.info("Reading EventHub: %s", source_name)
    msgs = receive_eventhub_batch(
        eventhub_name=source_name,
        consumer_group="$Default",
        max_messages=500,
        max_wait_time=60
    )
    return msgs

def adls_sink_activity(payload):
    logging.info("Stream Analytics writes parquet")
    return "disabled"


    # VT commented out
    # if isinstance(merged_payload.get("VirusTotal"), list):
    #     records.extend(merged_payload["VirusTotal"])
