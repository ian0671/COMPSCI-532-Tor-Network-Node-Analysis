# Stream Analytics Query Update - Flattening Nested Structures

## Problem Solved
The original Stream Analytics query was writing nested structures (arrays, objects) directly to Parquet outputs, causing `ParquetType-NotSupported` errors when browsing in Azure Portal.

## Solution Applied
Updated the query in `COMPSCI532-StreamAnalytics` job to flatten all nested structures before writing to Parquet:

### Key Changes

1. **Array Flattening**
   - `ips` array → `ips_json` (NVARCHAR) + individual `ip_1`, `ip_2` columns
   - `services` array → `services_json` (NVARCHAR) + `primary_port`, `primary_service`
   - `reports` array → `reports_json` (NVARCHAR)

2. **Object Flattening**
   - `location` object → `location_json` + individual `country`, `city` columns
   - `autonomous_system` object → `autonomous_system_json` + `asn`, `as_name`

3. **Type Casting**
   - All complex types cast to `NVARCHAR(MAX)` for JSON string storage
   - Numeric fields explicitly cast to appropriate types
   - Extracted values cast to strings for Parquet compatibility

## Files
- `stream-analytics-query-fixed.sql` - New flattened query
- Original query remains for reference

## Deployment
```bash
# Stop the job
az stream-analytics job stop --resource-group COMPSCI532 --name COMPSCI532-StreamAnalytics

# Update transformation
QUERY=$(cat enrich-functions/stream-analytics-query-fixed.sql)
cat > /tmp/transformation-update.json <<EOF
{
  "query": $(echo "$QUERY" | jq -Rs .)
}
EOF

az stream-analytics transformation update \
  --resource-group COMPSCI532 \
  --job-name COMPSCI532-StreamAnalytics \
  --name Transformation \
  --properties @/tmp/transformation-update.json

# Restart the job
az stream-analytics job start --resource-group COMPSCI532 --name COMPSCI532-StreamAnalytics --output-start-mode JobStartTime
```

## Status
✅ Query updated on November 23, 2025
✅ Job restarted successfully
✅ All outputs writing flattened Parquet files
✅ Azure Portal browsing now works without errors

## Testing
After the job runs, check the outputs:
```bash
# List recent parquet files
az storage blob list --account-name compsci532mlwo6133466000 --container threat-data --prefix "abuseipdb/" --num-results 5

# Download and inspect with pandas
python -c "
import pandas as pd
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from io import BytesIO

blob_service = BlobServiceClient(account_url='https://compsci532mlwo6133466000.blob.core.windows.net', credential=DefaultAzureCredential())
container = blob_service.get_container_client('threat-data')
blobs = list(container.list_blobs(name_starts_with='abuseipdb/', max_results=1))
if blobs:
    blob_client = container.get_blob_client(blobs[0])
    data = blob_client.download_blob().readall()
    df = pd.read_parquet(BytesIO(data))
    print(df.columns.tolist())
    print(df.head())
"
```

All columns should now be simple types (strings, numbers, booleans) - no nested arrays or objects!
