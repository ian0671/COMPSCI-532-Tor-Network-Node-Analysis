# virustotal/virustotal_timer.py
import datetime
import logging
import os
import azure.functions as func


Virus_Total_Timer = func.Blueprint()


@Virus_Total_Timer.timer_trigger(
    schedule="0 0 */24 * * *",  # daily
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def virus_total_timer(myTimer: func.TimerRequest) -> None:
    fired_at = datetime.datetime.utcnow().isoformat() + "Z"
    logging.info("VirusTotal timer triggered at %s", fired_at)
   