# Azure Stream Analytics Setup for ADLS Gen2 Parquet Capture

## Overview
This setup captures Event Hub data from your Azure Functions pipeline and stores it in ADLS Gen2 in Parquet format for long-term analytics.

## Current Status
✅ **Stream Analytics Job Created**: `COMPSCI532-StreamAnalytics`  
✅ **Inputs Configured**: 
   - `AbuseIPDBInput` (connected to abuseipdbdata Event Hub)
   - `CensysInput` (connected to censysdata Event Hub)
⚠️ **Outputs Pending**: ADLS Gen2 Parquet outputs (complete via Azure Portal)  

---

## Complete Setup via Azure Portal

### 1. Navigate to Stream Analytics Job
- Go to: [Azure Portal](https://portal.azure.com)
- Search: "COMPSCI532-StreamAnalytics"
- Select your Stream Analytics job

### 2. Add Outputs for ADLS Gen2 Parquet
**Create 3 outputs by clicking "Outputs" → "+ Add" → "Blob storage/ADLS Gen2" for each:**

#### **Output 1: AbuseIPDB Data**
   - **Output alias**: `AbuseIPDBParquetOutput`
   - **Storage account**: `compsci532mlwo6133466000`
   - **Container**: `threat-data`
   - **Path pattern**: `abuseipdb/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/hour={datetime:HH}/{rand-guid}`
   - **Event serialization format**: **Parquet**

#### **Output 2: Censys Data**
   - **Output alias**: `CensysParquetOutput`
   - **Storage account**: `compsci532mlwo6133466000`
   - **Container**: `threat-data`
   - **Path pattern**: `censys/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/hour={datetime:HH}/{rand-guid}`
   - **Event serialization format**: **Parquet**

#### **Output 3: Combined Analytics (Optional)**
   - **Output alias**: `CombinedThreatOutput`
   - **Storage account**: `compsci532mlwo6133466000`
   - **Container**: `threat-data`
   - **Path pattern**: `combined/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/hour={datetime:HH}/{rand-guid}`
   - **Event serialization format**: **Parquet**

### 3. Set Up the Query
1. **Click "Query"** in the left menu
2. **Replace with this multi-stream query:**
```sql
-- AbuseIPDB Data Stream
SELECT 
    *,
    'AbuseIPDB' as DataSource,
    System.Timestamp AS ProcessedTime
INTO AbuseIPDBParquetOutput
FROM AbuseIPDBInput
WHERE 
    ip IS NOT NULL 
    AND isPublic IS NOT NULL;

-- Censys Data Stream  
SELECT 
    *,
    'Censys' as DataSource,
    System.Timestamp AS ProcessedTime
INTO CensysParquetOutput
FROM CensysInput
WHERE 
    ip IS NOT NULL;

-- Combined Stream for Real-time Analytics (Optional)
SELECT 
    COALESCE(a.ip, c.ip) as ip,
    a.abuseConfidencePercentage,
    a.countryCode as abuse_country,
    a.isp as abuse_isp,
    c.services,
    c.location,
    System.Timestamp AS ProcessedTime
INTO CombinedThreatOutput
FROM AbuseIPDBInput a
FULL OUTER JOIN CensysInput c ON a.ip = c.ip AND DATEDIFF(minute, a, c) BETWEEN -5 AND 5;
```

### 4. Start the Job
1. **Click "Start"** at the top
2. **Job output start time**: "Now"
3. **Click "Start"**

---

## What This Achieves

### 📊 **Automated Data Archival**
- **Real-time capture** of all AbuseIPDB data from your functions
- **Parquet format** for efficient analytics and compression
- **Partitioned storage** by date/time for easy querying

### 🔍 **Analytics Ready**
- **Date partitioning**: `/year=2025/month=11/day=09/hour=14/`
- **Columnar storage**: Optimal for analytical queries
- **Schema evolution**: Parquet handles data schema changes gracefully

### 🚀 **Integration Benefits**
- **Complements your pipeline**: No changes to existing Azure Functions
- **Cost effective**: Pay-per-use Stream Analytics + cheap ADLS storage
- **Scalable**: Handles high-throughput Event Hub streams

---

## Data Flow Architecture

```
AbuseIPDBTimer (Function) → Event Hub (abuseipdbdata) ┐
                                                      ├→ Stream Analytics Job ┐
CensysTimer (Function) → Event Hub (censysdata) ─────┘                      │
                                                                             ├→ ADLS Gen2 (Parquet)
SimpleOrchestrator (Function) → Event Hub (collector) ──────────────────────┘
                                                                             ↓
                                                                    Combined Analytics Data
```

---

## Next Steps

1. **Complete the setup** via Azure Portal (steps above)
2. **Add Censys data**: Create similar input/output for censysdata Event Hub
3. **Set up alerts**: Monitor job health and data flow
4. **Query data**: Use Azure Data Explorer or Synapse for analytics

---

## Monitoring & Troubleshooting

### Check Job Status
```bash
az stream-analytics job show --resource-group COMPSCI532 --name COMPSCI532-StreamAnalytics --query "jobState"
```

### View Job Metrics
- Navigate to your Stream Analytics job in Azure Portal
- Click "Monitoring" → "Metrics"
- Key metrics: Input Events, Output Events, Runtime Errors

---

*This setup provides automated, real-time archival of your threat intelligence data in an analytics-optimized format.*