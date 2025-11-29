import datetime
import logging
import os
import azure.functions as func

from .api_client import query_recent_pulses
from .validators import validate_pulse_minimal
from eventhub_utils import send_to_eventhub

AlienVault_OTX_Timer = func.Blueprint()

OTX_EH_NAME = os.environ.get("OTX_EH_NAME")

@AlienVault_OTX_Timer.timer_trigger(
    schedule="*/25 * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def alienvault_timer(myTimer: func.TimerRequest) -> None:

    if myTimer.past_due:
        logging.info("AlienVault timer past due")

    fired_at = datetime.datetime.utcnow().isoformat() + "Z"
    logging.info("AlienVault timer fired at %s", fired_at)

    try:
        pulses = query_recent_pulses()
    except Exception as e:
        logging.exception("Failed to query OTX: %s", e)
        return

    normalized = []
    for p in pulses:
        if not validate_pulse_minimal(p):
            continue

        indicators = p.get("indicators", [])
        norm = {
            "pulse_id": p.get("id"),
            "name": p.get("name"),
            "description": p.get("description"),
            "modified": p.get("modified"),
            "indicator_count": len(indicators),
            "indicators": [
                {
                    "indicator": i.get("indicator"),
                    "type": i.get("type"),
                    "created": i.get("created")
                }
                for i in indicators
            ],
            "normalized_at": datetime.datetime.utcnow().isoformat() + "Z",
            "source": "alienvault_otx",
            "timestamp": fired_at
        }

        normalized.append(norm)

    if not normalized:
        logging.info("No pulses to send")
        return

    if OTX_EH_NAME:
        send_to_eventhub(OTX_EH_NAME, normalized)
        logging.info("Sent %d messages → EH %s", len(normalized), OTX_EH_NAME)
    else:
        logging.error("OTX_EH_NAME not set; cannot send")
