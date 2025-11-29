def validate_pulse_minimal(p: dict) -> bool:
    required = ["id", "name", "modified"]
    return all(k in p for k in required)
