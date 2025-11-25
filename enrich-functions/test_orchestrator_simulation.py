#!/usr/bin/env python3
"""
Test simulation of the orchestrator function with real data structure
"""
import json
from datetime import datetime

def simulate_orchestrator_join():
    """Simulate the orchestrator function with the actual data structures we're seeing"""
    
    # Simulate AbuseIPDB data based on what we observed (803 bytes for 2 records)
    abuseipdb_data = [
        {
            "ip": "8.8.8.8",
            "isPublic": True,
            "ipVersion": 4,
            "isWhitelisted": False,
            "abuseConfidencePercentage": 0,
            "countryCode": "US",
            "usageType": "Data Center/Web Hosting/Transit",
            "isp": "Google LLC",
            "domain": "google.com",
            "totalReports": 0,
            "numDistinctUsers": 0,
            "lastReportedAt": None
        },
        {
            "ip": "1.1.1.1",
            "isPublic": True,
            "ipVersion": 4,
            "isWhitelisted": False,
            "abuseConfidencePercentage": 0,
            "countryCode": "US",
            "usageType": "Content Delivery Network",
            "isp": "Cloudflare, Inc.",
            "domain": "cloudflare.com",
            "totalReports": 0,
            "numDistinctUsers": 0,
            "lastReportedAt": None
        }
    ]
    
    # Simulate Censys data (empty due to auth error, but structure would be)
    censys_data = []  # Would contain host data if authentication worked
    
    print("🔄 **Simulating Orchestrator Join Logic**")
    print(f" AbuseIPDB records: {len(abuseipdb_data)}")
    print(f" Censys records: {len(censys_data)}")
    
    # Perform the join operation (same logic as in function_app.py)
    joined_results = []
    
    for abuse_record in abuseipdb_data:
        ip = abuse_record.get('ip')
        
        # Find matching Censys data
        censys_match = None
        for censys_record in censys_data:
            if censys_record.get('ip') == ip:
                censys_match = censys_record
                break
        
        # Create joined record
        joined_record = {
            'ip': ip,
            'timestamp': datetime.utcnow().isoformat(),
            'abuseipdb': abuse_record,
            'censys': censys_match,
            'threat_score': calculate_threat_score(abuse_record, censys_match)
        }
        joined_results.append(joined_record)
    
    print(f" **Join completed: {len(joined_results)} enriched records**")
    
    # Calculate what would be sent to Event Hub
    joined_json = json.dumps(joined_results, indent=2)
    message_size = len(joined_json.encode('utf-8'))
    
    print(f" **Message size for 'collector' Event Hub: {message_size} bytes**")
    print(f"⚡ **Estimated processing time: ~1000ms** (based on observed pattern)")
    
    # Show sample of what would be sent
    print("\n **Sample joined record:**")
    print(json.dumps(joined_results[0], indent=2)[:500] + "...")
    
    return joined_results

def calculate_threat_score(abuseipdb_data, censys_data):
    """Calculate threat score based on available data"""
    score = 0
    
    if abuseipdb_data:
        # AbuseIPDB confidence percentage
        score += abuseipdb_data.get('abuseConfidencePercentage', 0)
        
        # Add points for total reports
        reports = abuseipdb_data.get('totalReports', 0)
        score += min(reports * 2, 20)  # Cap at 20 points
    
    if censys_data:
        # Add Censys-based scoring here
        # For now, placeholder since we don't have Censys data
        pass
    
    return min(score, 100)  # Cap at 100

if __name__ == "__main__":
    simulate_orchestrator_join()