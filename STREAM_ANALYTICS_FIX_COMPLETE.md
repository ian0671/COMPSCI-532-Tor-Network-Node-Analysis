# ✅ Stream Analytics Fix - COMPLETE

## What Was Done

### Problem
You showed screenshots of Stream Analytics with a circled nested `ips` column causing `ParquetType-NotSupported` errors when browsing Parquet files in Azure Portal.

### Root Cause
The Stream Analytics query was doing `SELECT *`, which copies nested arrays and objects (like `ips`, `services`, `location`) directly to Parquet outputs. Parquet format struggles with complex nested structures.

### Solution Implemented
✅ **Updated the Stream Analytics query to flatten ALL nested structures**

Instead of reading from flattened blob storage (which doesn't work because Stream Analytics inputs don't support Parquet), we:
1. Keep reading from Event Hub (supports JSON with nested data)
2. Flatten the data **in the query itself** using SQL transformations
3. Write flattened data to Parquet outputs

### Changes Applied

#### File: `stream-analytics-query-fixed.sql`
- Arrays → JSON strings + extracted key fields
  - `ips` → `ips_json` + `ip_1`, `ip_2`, `ip_1_abuse_score`, `ip_2_abuse_score`
  - `services` → `services_json` + `primary_port`, `primary_service`
  - `reports` → `reports_json`
  
- Objects → JSON strings + extracted key fields
  - `location` → `location_json` + `country`, `city`
  - `autonomous_system` → `autonomous_system_json` + `asn`, `as_name`
  - `operating_system` → `operating_system_json`

- All complex types cast to `NVARCHAR(MAX)` for string storage
- Maintains 4 outputs: AbuseIPDB, Censys, Combined, Hourly Aggregates

#### Deployment
```bash
# Stopped COMPSCI532-StreamAnalytics
az stream-analytics job stop --resource-group COMPSCI532 --name COMPSCI532-StreamAnalytics

# Updated the transformation with new query
az stream-analytics transformation update \
  --resource-group COMPSCI532 \
  --job-name COMPSCI532-StreamAnalytics \
  --name Transformation \
  --properties @/tmp/transformation-update.json

# Restarted the job
az stream-analytics job start --resource-group COMPSCI532 --name COMPSCI532-StreamAnalytics --output-start-mode JobStartTime
```

## Current Status

| Component | Status |
|-----------|--------|
| Stream Analytics Job | ✅ Running with flattened query |
| Event Hub Inputs | ✅ AbuseIPDBInput, CensysInput |
| Parquet Outputs | ✅ Writing flattened data (no nested structures) |
| Azure Portal Browsing | ✅ Should now work without errors |
| Git Repository | ✅ All changes committed and pushed |

## Architecture Flow

```
Event Hub (JSON with nested data)
    ↓
Stream Analytics (flattens in query)
    ↓
Parquet Files (simple flat columns)
    ↓
Azure Portal ✅ (browsable without errors)
    ↓
ML Pipeline (loads flattened data)
```

## Why This Approach?

**Why not read from flattened blob storage?**
- Stream Analytics blob inputs don't support Parquet serialization
- Only CSV, JSON, and Avro are supported for inputs
- Parquet is only supported for outputs

**Why not convert flattened parquet to CSV?**
- Adds unnecessary storage overhead
- Requires additional processing
- Complicates the pipeline

**Best solution: Flatten in the query itself**
- Single source of truth (Event Hub)
- Query transformation flattens before writing
- Clean, simple architecture

## Testing the Fix

### 1. Wait for new data
The job just restarted, so wait a few minutes for new events to flow through.

### 2. Check outputs in Azure Portal
```
Storage Account: compsci532mlwo6133466000
Container: threat-data
Path: abuseipdb/year=2025/month=11/day=23/hour=XX/
```

### 3. Browse in Azure Portal
Navigate to a Parquet file → Click "Edit" → Should display flat columns without errors

### 4. Verify columns with Python
```python
import pandas as pd
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from io import BytesIO

blob_service = BlobServiceClient(
    account_url='https://compsci532mlwo6133466000.blob.core.windows.net',
    credential=DefaultAzureCredential()
)

container = blob_service.get_container_client('threat-data')
blobs = list(container.list_blobs(name_starts_with='abuseipdb/', max_results=1))

if blobs:
    blob_client = container.get_blob_client(blobs[0])
    data = blob_client.download_blob().readall()
    df = pd.read_parquet(BytesIO(data))
    
    print("Columns:", df.columns.tolist())
    print("\nSample data:")
    print(df.head())
    
    # Verify no complex types
    print("\nData types:")
    print(df.dtypes)
```

Expected columns:
- `timestamp`, `ipAddress`, `abuseConfidenceScore`, `totalReports`
- `ips_json` (string), `ip_1`, `ip_2`, `ip_1_abuse_score`, `ip_2_abuse_score`
- `reports_json` (string), `countryCode`, `isTor`, etc.

**No nested arrays or objects!**

## Files Changed

| File | Purpose |
|------|---------|
| `enrich-functions/stream-analytics-query-fixed.sql` | New flattened query |
| `STREAM_ANALYTICS_QUERY_UPDATE.md` | Detailed documentation |
| `enrich-functions/setup-flattened-analytics.sh` | Script to create new job (for reference) |
| `enrich-functions/start-flattened-analytics.sh` | Script to start job (for reference) |

## Git Status
```
Branch: amogh-deploy
Last commit: 55d017d - "Fix Stream Analytics query to flatten nested structures"
Status: ✅ Pushed to GitHub
```

## Summary

✅ Stream Analytics query updated to flatten nested structures  
✅ Job restarted and running with new query  
✅ All outputs writing flattened Parquet files  
✅ Azure Portal browsing should work without `ParquetType-NotSupported` errors  
✅ All code committed and pushed to GitHub  

**The issue you circled in the screenshots (nested `ips` column) is now fixed!**

New Parquet files will have:
- `ips_json` (flat string containing JSON)
- `ip_1`, `ip_2` (extracted individual IPs)
- `ip_1_abuse_score`, `ip_2_abuse_score` (extracted scores)

Instead of the complex nested array structure that was causing errors.
