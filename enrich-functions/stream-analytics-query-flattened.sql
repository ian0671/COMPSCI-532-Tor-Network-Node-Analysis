-- Stream Analytics Query for Flattened Parquet Data
-- This query reads from flattened blob storage instead of Event Hub
-- Use this to query already-processed and flattened data for analytics

-- =====================================================
-- INPUTS CONFIGURATION (Configure in Azure Portal)
-- =====================================================
-- Input 1: FlattenedAbuseIPDB
--   Type: Blob storage/ADLS Gen2
--   Storage account: compsci532mlwo6133466000
--   Container: abuseipdb
--   Path pattern: flattened/{date}/{time}
--   Serialization: Parquet
--
-- Input 2: FlattenedCensys  
--   Type: Blob storage/ADLS Gen2
--   Storage account: compsci532mlwo6133466000
--   Container: censys
--   Path pattern: flattened/{date}/{time}
--   Serialization: Parquet
-- =====================================================

-- AbuseIPDB Flattened Data Stream
-- All nested structures are already flattened with dot notation
SELECT 
    source,
    count,
    timestamp,
    ips,  -- Now a JSON string instead of complex object
    EventProcessedUtcTime,
    EventEnqueuedUtcTime,
    PartitionId,
    EventSequenceNumber,
    'AbuseIPDB' as DataSource,
    System.Timestamp AS QueryProcessedTime
INTO AbuseIPDBAnalyticsOutput
FROM FlattenedAbuseIPDB
WHERE 
    ips IS NOT NULL;

-- Censys Flattened Data Stream
-- All nested structures are already flattened
SELECT 
    source,
    query as censys_query,
    count,
    timestamp,
    EventProcessedUtcTime,
    EventEnqueuedUtcTime,
    PartitionId,
    EventSequenceNumber,
    'Censys' as DataSource,
    System.Timestamp AS QueryProcessedTime
INTO CensysAnalyticsOutput
FROM FlattenedCensys
WHERE 
    timestamp IS NOT NULL;

-- Combined Threat Intelligence View
-- Join flattened data for correlation analysis
SELECT 
    a.source as abuse_source,
    a.count as abuse_count,
    a.timestamp as abuse_timestamp,
    a.ips as abuse_ips,
    c.source as censys_source,
    c.count as censys_count,
    c.timestamp as censys_timestamp,
    c.query as censys_query,
    System.Timestamp AS CorrelationTime
INTO CombinedThreatAnalytics
FROM FlattenedAbuseIPDB a TIMESTAMP BY EventProcessedUtcTime
JOIN FlattenedCensys c TIMESTAMP BY EventProcessedUtcTime
ON DATEDIFF(minute, a, c) BETWEEN -10 AND 10;

-- Real-time Aggregations on Flattened Data
-- Hourly statistics from flattened streams
SELECT 
    'AbuseIPDB' as Source,
    System.Timestamp AS WindowEnd,
    COUNT(*) as RecordCount,
    AVG(CAST(count as bigint)) as AvgCount
INTO HourlyAggregates
FROM FlattenedAbuseIPDB TIMESTAMP BY EventProcessedUtcTime
GROUP BY TumblingWindow(hour, 1)

UNION

SELECT 
    'Censys' as Source,
    System.Timestamp AS WindowEnd,
    COUNT(*) as RecordCount,
    AVG(CAST(count as bigint)) as AvgCount
FROM FlattenedCensys TIMESTAMP BY EventProcessedUtcTime
GROUP BY TumblingWindow(hour, 1);
