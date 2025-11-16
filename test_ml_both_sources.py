"""
Test Azure ML Pipeline with Both AbuseIPDB and Censys Data
"""

import sys
import os
sys.path.append('/Users/amoghsguthur/Desktop/CS532Project/tor-threat-pipeline/src')

from ml_threat_detection import ThreatIntelligenceML
import pandas as pd

def test_both_data_sources():
    """Test if both AbuseIPDB and Censys data work in ML pipeline"""
    
    print("🔍 Testing Azure ML Pipeline with Both Data Sources...")
    
    # Initialize ML pipeline
    ml_pipeline = ThreatIntelligenceML()
    
    print("\n📊 Testing AbuseIPDB Data Loading...")
    try:
        abuseipdb_data = ml_pipeline.load_abuseipdb_data()
        print(f"✅ AbuseIPDB: Loaded {len(abuseipdb_data)} records")
        print(f"   Columns: {list(abuseipdb_data.columns)}")
        print(f"   Sample data preview:")
        print(abuseipdb_data.head(2).to_string())
    except Exception as e:
        print(f"❌ AbuseIPDB Error: {e}")
        return False
    
    print("\n📊 Testing Censys Data Loading...")
    try:
        tor_data = ml_pipeline.load_tor_data()
        print(f"✅ Censys/Tor: Loaded {len(tor_data)} records")
        print(f"   Columns: {list(tor_data.columns)}")
        print(f"   Sample data preview:")
        print(tor_data.head(2).to_string())
    except Exception as e:
        print(f"❌ Censys Error: {e}")
        return False
    
    print("\n🔗 Testing Data Integration...")
    try:
        threat_data = ml_pipeline.create_threat_features(abuseipdb_data, tor_data)
        print(f"✅ Integration: Created {len(threat_data)} combined records")
        print(f"   Columns: {list(threat_data.columns)}")
        
        # Check data quality
        print(f"\n📈 Data Quality Check:")
        print(f"   - AbuseIPDB records with data: {abuseipdb_data['abuseConfidencePercentage'].notna().sum()}")
        print(f"   - Tor relays identified: {threat_data['is_tor_relay'].sum()}")
        print(f"   - High abuse score IPs: {threat_data['high_abuse_score'].sum()}")
        print(f"   - Threat levels distribution:")
        print(threat_data['threat_level'].value_counts().to_string())
        
    except Exception as e:
        print(f"❌ Integration Error: {e}")
        return False
    
    print("\n🤖 Testing ML Model Training...")
    try:
        # Train threat detection model
        threat_model = ml_pipeline.train_threat_detection_model(threat_data)
        if threat_model:
            print("✅ Threat Detection Model: Trained successfully")
        
        # Train anomaly detection model  
        anomaly_model = ml_pipeline.train_anomaly_detection_model(threat_data)
        if anomaly_model:
            print("✅ Anomaly Detection Model: Trained successfully")
            
        return True
        
    except Exception as e:
        print(f"❌ ML Training Error: {e}")
        return False

def test_real_azure_data():
    """Test with actual Azure storage data"""
    print("\n🌐 Testing with Real Azure Data...")
    
    ml_pipeline = ThreatIntelligenceML()
    
    try:
        # Try to load actual files from Azure storage
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential
        
        credential = DefaultAzureCredential()
        blob_client = BlobServiceClient(
            account_url="https://compsci532mlwo6133466000.blob.core.windows.net",
            credential=credential
        )
        
        # Check AbuseIPDB container
        abuseipdb_container = blob_client.get_container_client("abuseipdb")
        abuseipdb_blobs = list(abuseipdb_container.list_blobs(name_starts_with="compsci532eventhub"))
        print(f"📁 AbuseIPDB files found: {len(abuseipdb_blobs)}")
        
        # Check Censys container  
        censys_container = blob_client.get_container_client("censys")
        censys_blobs = list(censys_container.list_blobs(name_starts_with="compsci532eventhub"))
        print(f"📁 Censys files found: {len(censys_blobs)}")
        
        if len(abuseipdb_blobs) > 0 and len(censys_blobs) > 0:
            print("✅ Both AbuseIPDB and Censys data are available in Azure!")
            return True
        else:
            print("❌ Missing data in one or both containers")
            return False
            
    except Exception as e:
        print(f"❌ Azure connectivity error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔬 AZURE ML PIPELINE TEST - BOTH DATA SOURCES")
    print("=" * 60)
    
    # Test 1: Check Azure storage connectivity
    azure_test = test_real_azure_data()
    
    # Test 2: Test ML pipeline functionality  
    ml_test = test_both_data_sources()
    
    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"   Azure Data Access: {'✅ PASS' if azure_test else '❌ FAIL'}")
    print(f"   ML Pipeline: {'✅ PASS' if ml_test else '❌ FAIL'}")
    
    if azure_test and ml_test:
        print("🎉 SUCCESS: Both AbuseIPDB and Censys work in Azure ML!")
    else:
        print("⚠️  ISSUES DETECTED: Check the errors above")
    print("=" * 60)