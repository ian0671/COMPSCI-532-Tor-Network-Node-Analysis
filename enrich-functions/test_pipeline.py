#!/usr/bin/env python3
"""
Test script to validate Azure Functions pipeline components locally
"""
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_abuseipdb_api():
    """Test AbuseIPDB API connectivity and response format"""
    print("🔍 Testing AbuseIPDB API...")
    
    api_key = os.getenv("ABUSE_API_KEY", "a1878711c868898812da5d397605759c3adfd681483a0a51ce8ab1dc3eef824242760e00d59798eb")
    ip_list = ["8.8.8.8", "1.1.1.1"]
    
    if not api_key:
        print("❌ ABUSE_API_KEY not found")
        return False
    
    headers = {"Key": api_key, "Accept": "application/json"}
    test_results = []
    
    for ip in ip_list:
        try:
            response = requests.get(
                "https://api.abuseipdb.com/api/v2/check",
                params={"ipAddress": ip},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                test_results.append({
                    "source": "abuseipdb",
                    "ip": ip,
                    "run_id": int(datetime.utcnow().timestamp()),
                    "data": data
                })
                print(f"  ✅ {ip}: Success (confidence: {data.get('data', {}).get('abuseConfidenceScore', 0)}%)")
            else:
                print(f"  ❌ {ip}: HTTP {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"  ❌ {ip}: Error - {e}")
            return False
    
    print(f"✅ AbuseIPDB API test passed! Retrieved data for {len(test_results)} IPs")
    return test_results

def test_censys_api():
    """Test Censys API connectivity and response format"""
    print("🔍 Testing Censys API...")
    
    token = os.getenv("CENSYS_API_TOKEN", "EZXzJJap")
    
    if not token:
        print("❌ CENSYS_API_TOKEN not found")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "cs532-tor-pipeline/test"
    }
    
    params = {
        "q": "services.service_name:HTTP",
        "per_page": 5,
        "page": 1
    }
    
    try:
        response = requests.get(
            "https://search.censys.io/api/v2/hosts/search",
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("result", {}).get("hits", [])
            print(f"  ✅ Censys API: Success (found {len(hits)} hosts)")
            
            # Format data like the function would
            test_results = []
            run_id = int(datetime.utcnow().timestamp())
            
            for host in hits[:3]:  # Just test first 3
                test_results.append({
                    "source": "censys",
                    "ip": host.get("ip"),
                    "asn": host.get("autonomous_system", {}).get("asn"),
                    "country": host.get("location", {}).get("country"),
                    "seen_at": host.get("last_updated_at"),
                    "run_id": run_id,
                    "services": host.get("services", [])
                })
            
            return test_results
            
        elif response.status_code == 401:
            print(f"  ❌ Censys API: Authentication failed (401) - {response.text}")
            print("  💡 This is expected if API token is invalid/expired")
            return []
        else:
            print(f"  ❌ Censys API: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Censys API: Error - {e}")
        return False

def test_join_logic(abuse_data, censys_data):
    """Test the join logic that combines data from both sources"""
    print("🔍 Testing join logic...")
    
    if not abuse_data and not censys_data:
        print("  ⚠️ No test data available for join logic")
        return []
    
    # Simulate join logic from SimpleOrchestrator
    joined_records = []
    
    # Get unique IPs from both sources
    abuse_ips = {record["ip"]: record for record in abuse_data if record.get("ip")}
    censys_ips = {record["ip"]: record for record in censys_data if record.get("ip")}
    
    all_ips = set(abuse_ips.keys()) | set(censys_ips.keys())
    
    for ip in all_ips:
        record = {
            "ip": ip,
            "joined_at": datetime.utcnow().isoformat(),
            "abuse": abuse_ips.get(ip),
            "censys": censys_ips.get(ip)
        }
        joined_records.append(record)
    
    print(f"  ✅ Join logic: Created {len(joined_records)} joined records")
    print(f"    - AbuseIPDB IPs: {len(abuse_ips)}")
    print(f"    - Censys IPs: {len(censys_ips)}")
    print(f"    - Unique IPs total: {len(all_ips)}")
    
    return joined_records

def test_validation_logic(joined_data):
    """Test the validation logic from ValidateAndStore function"""
    print("🔍 Testing validation logic...")
    
    if not joined_data:
        print("  ⚠️ No joined data to validate")
        return []
    
    validated_records = []
    
    for record in joined_data:
        ip = record.get("ip")
        if not ip:
            continue
            
        validated_record = {
            "ip": ip,
            "joined_at": record.get("joined_at"),
            "abuse_score": (record.get("abuse") or {}).get("data", {}).get("abuseConfidenceScore"),
            "services": (record.get("censys") or {}).get("services"),
            "location": (record.get("censys") or {}).get("country"),
        }
        validated_records.append(validated_record)
    
    print(f"  ✅ Validation logic: Created {len(validated_records)} validated records")
    
    # Show sample validated record
    if validated_records:
        sample = validated_records[0]
        print(f"    Sample record: IP={sample['ip']}, Abuse Score={sample['abuse_score']}")
    
    return validated_records

def main():
    """Run all pipeline tests"""
    print("🚀 Starting Azure Functions Pipeline Tests")
    print("=" * 50)
    
    # Test 1: AbuseIPDB API
    abuse_data = test_abuseipdb_api()
    print()
    
    # Test 2: Censys API (expect failure with current token)
    censys_data = test_censys_api()
    print()
    
    # Test 3: Join Logic
    if abuse_data or censys_data:
        joined_data = test_join_logic(abuse_data or [], censys_data or [])
        print()
        
        # Test 4: Validation Logic
        validated_data = test_validation_logic(joined_data)
        print()
    else:
        print("⚠️ Skipping join and validation tests due to API failures")
    
    print("=" * 50)
    print("🎯 Test Summary:")
    print(f"  • AbuseIPDB API: {'✅ Working' if abuse_data else '❌ Failed'}")
    print(f"  • Censys API: {'✅ Working' if censys_data else '❌ Failed (expected)'}")
    print(f"  • Join Logic: {'✅ Working' if 'joined_data' in locals() else '❌ Skipped'}")
    print(f"  • Validation: {'✅ Working' if 'validated_data' in locals() else '❌ Skipped'}")
    print()
    print("💡 Next steps:")
    print("  1. Fix Censys API credentials if needed")
    print("  2. Configure ADLS settings in Azure Function App")
    print("  3. Test Event Hub data flow")

if __name__ == "__main__":
    main()