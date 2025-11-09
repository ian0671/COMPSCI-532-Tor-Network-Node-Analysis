-- Stream Analytics Query for Threat Intelligence Data Archival to ADLS Gen2
-- This query processes both AbuseIPDB and Censys Event Hub data and outputs to Parquet format

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