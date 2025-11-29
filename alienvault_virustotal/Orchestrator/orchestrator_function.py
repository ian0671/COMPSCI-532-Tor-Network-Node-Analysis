# orchestrator/orchestrator_function.py
# import azure.durable_functions as df
# import logging

# def orchestrator_function(context: df.DurableOrchestrationContext):
#     # read AlienVault messages (activity)
#     alienvault_msgs = yield context.call_activity("read_eventhub_activity", "OTX_EH_NAME")
#     # VirusTotal
#     # virustotal_msgs = yield context.call_activity("read_eventhub_activity", "VIRUSTOTAL_EH_NAME")

#     merged = {
#         "AlienVault": alienvault_msgs,
#         # "VirusTotal": virustotal_msgs,
#         "merged_at": df.DurableOrchestrationContext.current_utc_datetime().isoformat() + "Z"
#     }

#     # sink to ADLS
#     result = yield context.call_activity("adls_sink_activity", merged)
#     logging.info("Orchestrator finished, ADLS result: %s", result)
#     return {"result": result, "count": len(alienvault_msgs or [])}

# main = df.Orchestrator.create(orchestrator_function)


import azure.durable_functions as df
import logging

def orchestrator_function(context: df.DurableOrchestrationContext):

    alienvault_msgs = yield context.call_activity(
        "read_eventhub_activity",
        "OTX_EH_NAME"
    )

    merged = {
        "AlienVault": alienvault_msgs,
        "merged_at": df.DurableOrchestrationContext.current_utc_datetime().isoformat() + "Z"
    }

    logging.info("Orchestrator finished (no ADLS write)")
    return {"count": len(alienvault_msgs or [])}

main = df.Orchestrator.create(orchestrator_function)
