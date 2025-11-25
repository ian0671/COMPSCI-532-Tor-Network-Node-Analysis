# Stream Analytics Setup for Flattened Data

## Overview
This guide shows how to configure Azure Stream Analytics to read from **flattened blob storage** instead of Event Hub, eliminating the ParquetType-NotSupported errors.

## Architecture Change

### Before (Current - Has Errors):
```
Event Hub → Stream Analytics → Parquet (nested/broken) 
```

### After (Recommended):
```
Event Hub → Raw Parquet → Flatten Function → Flattened Parquet → Stream Analytics 
```

## Option 1: Use Flattened Blob Storage (Recommended)

### Step 1: Create New Stream Analytics Job

```bash
# Create a new job for flattened data analytics
az stream-analytics job create \
  --resource-group COMPSCI532 \
  --name COMPSCI532-FlattenedAnalytics \
  --location eastus \
  --output-error-policy "Drop" \
  --events-outoforder-policy "Adjust" \
  --events-outoforder-max-delay 5 \
  --events-late-arrival-max-delay 5
```

### Step 2: Configure Inputs (Azure Portal)

#### Input 1: FlattenedAbuseIPDB
1. Go to Stream Analytics job → Inputs → Add blob storage input
2. **Input alias**: `FlattenedAbuseIPDB`
3. **Storage account**: `compsci532mlwo6133466000`
4. **Container**: `abuseipdb`
5. **Path pattern**: `flattened/*.parquet`
6. **Event serialization format**: **Parquet**
7. **Authentication**: Connection string or Managed Identity

#### Input 2: FlattenedCensys
1. Add blob storage input
2. **Input alias**: `FlattenedCensys`
3. **Storage account**: `compsci532mlwo6133466000`
4. **Container**: `censys`
5. **Path pattern**: `flattened/*.parquet`
6. **Event serialization format**: **Parquet**
7. **Authentication**: Connection string or Managed Identity

### Step 3: Configure Outputs

#### Output 1: AbuseIPDB Analytics
- **Output alias**: `AbuseIPDBAnalyticsOutput`
- **Sink**: Azure Data Lake Gen2 or Azure SQL Database
- **Container**: `analytics`
- **Path**: `abuseipdb/year={datetime:yyyy}/month={datetime:MM}/`

#### Output 2: Censys Analytics
- **Output alias**: `CensysAnalyticsOutput`
- **Container**: `analytics`
- **Path**: `censys/year={datetime:yyyy}/month={datetime:MM}/`

#### Output 3: Combined Analytics
- **Output alias**: `CombinedThreatAnalytics`
- **Container**: `analytics`
- **Path**: `combined/year={datetime:yyyy}/month={datetime:MM}/`

#### Output 4: Hourly Aggregates
- **Output alias**: `HourlyAggregates`
- **Container**: `analytics`
- **Path**: `aggregates/year={datetime:yyyy}/month={datetime:MM}/`

### Step 4: Set Up Query

Use the query from `stream-analytics-query-flattened.sql`:

```sql
-- AbuseIPDB Flattened Data Stream
SELECT 
    source,
    count,
    timestamp,
    ips,  -- Now a JSON string instead of complex object
    EventProcessedUtcTime,
    'AbuseIPDB' as DataSource,
    System.Timestamp AS QueryProcessedTime
INTO AbuseIPDBAnalyticsOutput
FROM FlattenedAbuseIPDB
WHERE ips IS NOT NULL;

-- See full query in stream-analytics-query-flattened.sql
```

### Step 5: Start the Job

```bash
az stream-analytics job start \
  --resource-group COMPSCI532 \
  --name COMPSCI532-FlattenedAnalytics \
  --output-start-mode JobStartTime
```

## Option 2: Update Existing Job to Read Flattened Data

### Quick Update Steps:
1. Stop your existing `COMPSCI532-StreamAnalytics` job
2. Replace Event Hub inputs with Blob Storage inputs (above)
3. Update the query to use new input aliases
4. Restart the job

```bash
# Stop job
az stream-analytics job stop \
  --resource-group COMPSCI532 \
  --name COMPSCI532-StreamAnalytics

# Update inputs in portal (manual step)

# Restart job
az stream-analytics job start \
  --resource-group COMPSCI532 \
  --name COMPSCI532-StreamAnalytics
```

## Benefits of Using Flattened Data

###  No ParquetType Errors
- All complex types converted to strings
- Compatible with Azure portal browsing
- Works with all downstream tools

###  Better Performance
- Pre-flattened data is faster to query
- No runtime JSON parsing needed
- Optimized schema for analytics

###  ML Pipeline Ready
- Same data source for Stream Analytics and ML
- Consistent data format across pipeline
- Easy to validate and debug

## Data Flow with Flattening

```
┌─────────────┐
│ Event Hub   │
│ (abuseipdb) │
└──────┬──────┘
       │
       ↓
┌─────────────────────┐
│ Storage Account     │
│ Raw Parquet Files   │
│ (nested structure)  │
└──────┬──────────────┘
       │
       ↓ Blob Trigger
┌─────────────────────┐
│ Flatten Function    │
│ (Azure Function)    │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ Storage Account     │
│ Flattened Parquet   │  ←─── Stream Analytics reads from here
│ (flat structure)    │
└──────┬──────────────┘
       │
       ├─→ Stream Analytics → Analytics DB
       │
       └─→ ML Pipeline → Trained Models
```

## Querying Flattened Data

### Example: Count Records by Source
```sql
SELECT 
    source,
    COUNT(*) as RecordCount
FROM FlattenedAbuseIPDB
GROUP BY source, TumblingWindow(hour, 1);
```

### Example: Parse JSON Strings
Since `ips` is now a JSON string, you can parse it if needed:
```sql
SELECT 
    source,
    JSON_VALUE(ips, '$.ip') as ip_address,
    timestamp
FROM FlattenedAbuseIPDB;
```

## Monitoring

### Check Input Processing
```bash
az stream-analytics job show \
  --resource-group COMPSCI532 \
  --name COMPSCI532-FlattenedAnalytics \
  --query "inputs[].name"
```

### View Metrics
- Input Events (from flattened blobs)
- Output Events (to analytics)
- Data Conversion Errors (should be 0 now!)
- Watermark Delay

## Troubleshooting

### Issue: No data flowing
**Solution:** Verify blob path patterns match your flattened files:
```
abuseipdb/flattened/*.parquet
censys/flattened/*.parquet
```

### Issue: Schema errors
**Solution:** Flattened data should have consistent schema. Check flatten function logs.

### Issue: High watermark delay
**Solution:** Increase streaming units in Stream Analytics job settings.

## Cost Optimization

- **Streaming Units**: Start with 1 SU, scale up if needed
- **Blob Storage**: Use cool tier for older flattened data
- **Output Batching**: Configure batch size for efficiency

## Next Steps

1.  Create new Stream Analytics job for flattened data
2.  Configure blob storage inputs
3.  Set up analytics outputs
4.  Deploy query from `stream-analytics-query-flattened.sql`
5.  Test with existing 1350 flattened files
6.  Monitor and optimize

---

**Result:** No more ParquetType errors, faster queries, ML-ready data! 
