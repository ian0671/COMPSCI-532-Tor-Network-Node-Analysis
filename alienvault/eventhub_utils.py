import json
import logging
from typing import List, Dict
import os
from azure.eventhub import EventHubProducerClient, EventData, EventHubConsumerClient

EVENTHUB_CONNECTION = os.environ.get("EVENTHUB_CONNECTION")

def send_to_eventhub(eventhub_name: str, records: List[Dict], max_batch_size=100):

    if not EVENTHUB_CONNECTION:
        logging.error("Missing EVENTHUB_CONNECTION")
        return

    producer = EventHubProducerClient.from_connection_string(
        conn_str=EVENTHUB_CONNECTION,
        eventhub_name=eventhub_name
    )

    with producer:
        batch = producer.create_batch()
        for rec in records:
            body = json.dumps(rec, separators=(",", ":"), ensure_ascii=False)
            ev = EventData(body)

            if not batch.try_add(ev):
                producer.send_batch(batch)
                batch = producer.create_batch()
                batch.try_add(ev)

        if len(batch) > 0:
            producer.send_batch(batch)

    logging.info("EventHub send complete → %s", eventhub_name)
