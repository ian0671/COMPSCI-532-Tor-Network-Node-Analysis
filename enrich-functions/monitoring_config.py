"""
Production monitoring and alerting configuration for Azure Functions
"""

# Application Insights configuration for host.json
HOST_JSON_MONITORING = {
    "version": "2.0",
    "logging": {
        "applicationInsights": {
            "samplingSettings": {
                "isEnabled": True,
                "maxTelemetryItemsPerSecond": 20
            }
        },
        "logLevel": {
            "default": "Information",
            "Function": "Information"
        }
    },
    "functionTimeout": "00:05:00",
    "healthMonitor": {
        "enabled": True,
        "healthCheckInterval": "00:00:30",
        "healthCheckWindow": "00:02:00",
        "healthCheckThreshold": 6,
        "counterThreshold": 0.80
    }
}

# Custom metrics to track
CUSTOM_METRICS = {
    "abuseipdb_api_calls": "Counter for AbuseIPDB API calls",
    "censys_api_calls": "Counter for Censys API calls", 
    "event_hub_messages_sent": "Counter for Event Hub messages",
    "join_operations_completed": "Counter for join operations",
    "avg_function_duration": "Average function execution time",
    "api_error_rate": "Rate of API errors"
}

# Alert thresholds for production
ALERT_THRESHOLDS = {
    "function_failure_rate": 0.05,  # 5% failure rate
    "avg_execution_time": 5000,     # 5 seconds
    "api_error_rate": 0.10,         # 10% API error rate
    "event_hub_connection_failures": 3  # 3 consecutive failures
}