# Azure ML Integration with Flattened Data

## Overview
The ML pipeline has been updated to read from flattened parquet files in Azure Blob Storage instead of raw nested data.

## What Changed

### 1. Data Loading Updates
All ML scripts now load from the `flattened/` folders:

**AbuseIPDB Data:**
- **Old:** Read from raw nested structure in `abuseipdb/` container
- **New:** Read from `abuseipdb/flattened/*.parquet` files
- **Files:** 675 flattened parquet files, ~9.31 KiB each

**Censys Data:**
- **Old:** Not implemented
- **New:** Read from `censys/flattened/*.parquet` files  
- **Files:** 675 flattened parquet files

### 2. Updated Files

#### `src/ml_threat_detection.py`
- ✅ `load_abuseipdb_data()` - Now reads from `abuseipdb/flattened/`
- ✅ `load_censys_data()` - New method for censys flattened data
- ✅ `_simulate_censys_data()` - Fallback simulation method
- ✅ `run_full_pipeline()` - Loads all three data sources

#### `src/azure_ml_train.py`
- ✅ Updated to load censys data
- ✅ Logs censys record count to Azure ML metrics

### 3. Benefits of Flattened Data

**For Azure ML:**
- ✅ No ParquetType errors when browsing in Azure Portal
- ✅ Faster loading (no nested structure parsing)
- ✅ Direct pandas.read_parquet() compatibility
- ✅ Consistent schema across all files

**For Analytics:**
- ✅ Stream Analytics can query with simple column names
- ✅ SQL-like queries work without complex JSON parsing
- ✅ Better compression and storage efficiency

## How to Use

### Local Testing
```python
from src.ml_threat_detection import ThreatIntelligenceML

# Initialize pipeline
ml = ThreatIntelligenceML()

# Load from flattened storage
abuseipdb = ml.load_abuseipdb_data()
censys = ml.load_censys_data()

# Run full pipeline
ml.run_full_pipeline()
```

### Azure ML Deployment
```bash
cd deploy
python azure_ml_deploy.py
```

The deployment will automatically use flattened data from:
- `abuseipdb/flattened/` - 675 files
- `censys/flattened/` - 675 files

## Data Location

**Azure Storage Account:** `compsci532mlwo6133466000`

**Containers:**
- `abuseipdb/flattened/` - AbuseIPDB threat intelligence
- `censys/flattened/` - Censys network scan data

**File Pattern:** `{eventhub_partition_id}_{guid}_1.parquet`

## Viewing Data

### Azure Portal
1. Navigate to Storage Account → Containers
2. Select `abuseipdb` or `censys`
3. Click on `flattened` folder
4. Click any `.parquet` file
5. Click **Browse** tab to view contents

### Azure Storage Explorer
Download: https://azure.microsoft.com/features/storage-explorer/

## Next Steps

1. **Test the updated ML pipeline locally** with real flattened data
2. **Deploy to Azure ML** using the updated scripts
3. **Monitor training metrics** in Azure ML workspace
4. **Verify model accuracy** with production data

## Troubleshooting

**Issue:** No flattened files found
- **Solution:** Run the batch flatten scripts:
  ```bash
  python azure_function_flatten/batch_flatten_abuseipdb.py
  python azure_function_flatten/batch_flatten_censys.py
  ```

**Issue:** Authentication errors
- **Solution:** Ensure `DefaultAzureCredential` is configured or use connection string

**Issue:** Out of memory
- **Solution:** Reduce the number of files loaded (currently set to 10 most recent)
