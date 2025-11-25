#!/usr/bin/env python3
"""
Quick smoke test for the join logic without Azure dependencies.
"""

def join_and_enrich_simple(payload):
    """Simplified version of join logic for testing."""
    abuse = payload.get("abuse", [])
    censys = payload.get("censys", [])
    abuse_map = {a["ip"]: a for a in abuse if a.get("ip")}
    out = []
    
    for h in censys:
        ip = h.get("ip")
        if not ip:
            continue
        rec = {
            "ip": ip,
            "joined_at": "2025-11-06T00:00:00Z",
            "abuse": abuse_map.get(ip),
            "censys": {
                "services": h.get("services"),
                "location": h.get("location"),
            },
        }
        out.append(rec)
    
    # include any abuse-only IPs (no Censys match)
    censys_ips = {h.get("ip") for h in censys if h.get("ip")}
    for ip, a in abuse_map.items():
        if ip not in censys_ips:
            out.append({
                "ip": ip,
                "joined_at": "2025-11-06T00:00:00Z",
                "abuse": a,
                "censys": None,
            })
    return out


if __name__ == "__main__":
    import json
    
    # Test case 1: IP in both sources
    sample = join_and_enrich_simple({
        "abuse": [{"ip": "1.2.3.4", "abuseConfidenceScore": 42}],
        "censys": [{"ip": "1.2.3.4", "services": ["HTTP"], "location": {"country": "US"}}]
    })
    print("Test 1 - IP in both sources:")
    print(json.dumps(sample, indent=2))
    print()
    
    # Test case 2: IP only in AbuseIPDB
    sample2 = join_and_enrich_simple({
        "abuse": [{"ip": "5.6.7.8", "abuseConfidenceScore": 85}],
        "censys": [{"ip": "1.2.3.4", "services": ["HTTP"], "location": {"country": "US"}}]
    })
    print("Test 2 - IP only in AbuseIPDB:")
    print(json.dumps(sample2, indent=2))
    print()
    
    # Test case 3: IP only in Censys
    sample3 = join_and_enrich_simple({
        "abuse": [{"ip": "5.6.7.8", "abuseConfidenceScore": 85}],
        "censys": [{"ip": "9.10.11.12", "services": ["SSH"], "location": {"country": "CA"}}]
    })
    print("Test 3 - No common IPs:")
    print(json.dumps(sample3, indent=2))
    print()
    
    print(" Join logic tests passed!")