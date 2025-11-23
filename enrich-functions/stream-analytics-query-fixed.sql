-- Stream Analytics Query with Flattened Output
-- This query reads from Event Hub and flattens nested structures before writing to Parquet
-- Eliminates ParquetType-NotSupported errors by serializing complex types to JSON strings

-- ============================================
-- 1. Flattened AbuseIPDB Data
-- ============================================
SELECT
    EventEnqueuedUtcTime AS timestamp,
    ipAddress,
    CAST(abuseConfidenceScore AS BIGINT) AS abuseConfidenceScore,
    CAST(totalReports AS BIGINT) AS totalReports,
    CAST(numDistinctUsers AS BIGINT) AS numDistinctUsers,
    CAST(lastReportedAt AS NVARCHAR(MAX)) AS lastReportedAt,
    -- Flatten array/object fields to JSON strings
    CAST(reports AS NVARCHAR(MAX)) AS reports_json,
    CAST(ipVersion AS INT) AS ipVersion,
    isWhitelisted,
    countryCode,
    CAST(usageType AS NVARCHAR(MAX)) AS usageType,
    isp,
    domain,
    CAST(hostnames AS NVARCHAR(MAX)) AS hostnames_json,
    CAST(isTor AS BIT) AS isTor,
    -- Flatten the nested ips structure to individual columns
    CAST(TRY_CAST(GetArrayElement(ips, 0).ip AS NVARCHAR(MAX)) AS NVARCHAR(MAX)) AS ip_1,
    CAST(TRY_CAST(GetArrayElement(ips, 0).abuse_confidence_score AS INT) AS NVARCHAR(MAX)) AS ip_1_abuse_score,
    CAST(TRY_CAST(GetArrayElement(ips, 1).ip AS NVARCHAR(MAX)) AS NVARCHAR(MAX)) AS ip_2,
    CAST(TRY_CAST(GetArrayElement(ips, 1).abuse_confidence_score AS INT) AS NVARCHAR(MAX)) AS ip_2_abuse_score,
    -- Keep full array as JSON string for reference
    CAST(ips AS NVARCHAR(MAX)) AS ips_json
INTO AbuseIPDBAnalyticsOutput
FROM AbuseIPDBInput
WHERE ipAddress IS NOT NULL;

-- ============================================
-- 2. Flattened Censys Data
-- ============================================
SELECT
    EventEnqueuedUtcTime AS timestamp,
    ip,
    -- Flatten services array to JSON string
    CAST(services AS NVARCHAR(MAX)) AS services_json,
    -- Extract first service for quick filtering
    CAST(TRY_CAST(GetArrayElement(services, 0).port AS INT) AS NVARCHAR(MAX)) AS primary_port,
    CAST(TRY_CAST(GetArrayElement(services, 0).service_name AS NVARCHAR(MAX)) AS NVARCHAR(MAX)) AS primary_service,
    -- Location data
    CAST(location AS NVARCHAR(MAX)) AS location_json,
    CAST(TRY_CAST(GetRecordPropertyValue(location, 'country') AS NVARCHAR(MAX)) AS NVARCHAR(MAX)) AS country,
    CAST(TRY_CAST(GetRecordPropertyValue(location, 'city') AS NVARCHAR(MAX)) AS NVARCHAR(MAX)) AS city,
    -- Autonomous system
    CAST(autonomous_system AS NVARCHAR(MAX)) AS autonomous_system_json,
    CAST(TRY_CAST(GetRecordPropertyValue(autonomous_system, 'asn') AS BIGINT) AS NVARCHAR(MAX)) AS asn,
    CAST(TRY_CAST(GetRecordPropertyValue(autonomous_system, 'name') AS NVARCHAR(MAX)) AS NVARCHAR(MAX)) AS as_name,
    -- Operating system
    CAST(operating_system AS NVARCHAR(MAX)) AS operating_system_json,
    -- Last updated
    CAST(last_updated_at AS NVARCHAR(MAX)) AS last_updated_at
INTO CensysAnalyticsOutput
FROM CensysInput
WHERE ip IS NOT NULL;

-- ============================================
-- 3. Combined Threat Intelligence
-- ============================================
SELECT
    COALESCE(a.timestamp, c.timestamp) AS timestamp,
    COALESCE(a.ipAddress, c.ip) AS ip_address,
    -- AbuseIPDB metrics
    a.abuseConfidenceScore,
    a.totalReports,
    a.numDistinctUsers,
    a.countryCode AS abuse_country,
    a.isTor,
    -- Censys metrics  
    c.primary_port,
    c.primary_service,
    c.country AS censys_country,
    c.asn,
    c.as_name,
    -- Combined risk scoring
    CASE 
        WHEN a.abuseConfidenceScore >= 75 AND c.primary_port IN ('22', '23', '3389', '445') THEN 'CRITICAL'
        WHEN a.abuseConfidenceScore >= 50 OR c.primary_port IN ('22', '23', '3389', '445') THEN 'HIGH'
        WHEN a.abuseConfidenceScore >= 25 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_level,
    -- Full context as JSON
    CAST(a.ips_json AS NVARCHAR(MAX)) AS abuseipdb_context,
    CAST(c.services_json AS NVARCHAR(MAX)) AS censys_context
INTO CombinedThreatAnalytics
FROM AbuseIPDBInput a TIMESTAMP BY EventEnqueuedUtcTime
FULL OUTER JOIN CensysInput c TIMESTAMP BY EventEnqueuedUtcTime
ON a.ipAddress = c.ip
AND DATEDIFF(minute, a, c) BETWEEN 0 AND 5
WHERE COALESCE(a.ipAddress, c.ip) IS NOT NULL;

-- ============================================
-- 4. Hourly Aggregated Statistics
-- ============================================
SELECT
    System.Timestamp() AS window_end,
    COUNT(DISTINCT ipAddress) AS unique_ips,
    AVG(CAST(abuseConfidenceScore AS FLOAT)) AS avg_abuse_score,
    MAX(CAST(abuseConfidenceScore AS FLOAT)) AS max_abuse_score,
    SUM(CAST(totalReports AS BIGINT)) AS total_reports,
    COUNT(*) AS event_count,
    -- Top countries
    CAST(COLLECT(TOPONE(countryCode, 1)) AS NVARCHAR(MAX)) AS top_country,
    -- Risk distribution
    SUM(CASE WHEN CAST(abuseConfidenceScore AS INT) >= 75 THEN 1 ELSE 0 END) AS critical_risk_count,
    SUM(CASE WHEN CAST(abuseConfidenceScore AS INT) >= 50 AND CAST(abuseConfidenceScore AS INT) < 75 THEN 1 ELSE 0 END) AS high_risk_count,
    SUM(CASE WHEN CAST(abuseConfidenceScore AS INT) < 50 THEN 1 ELSE 0 END) AS low_risk_count,
    -- Tor statistics
    SUM(CASE WHEN isTor = 1 THEN 1 ELSE 0 END) AS tor_ip_count
INTO HourlyAggregates
FROM AbuseIPDBInput TIMESTAMP BY EventEnqueuedUtcTime
GROUP BY TumblingWindow(hour, 1);
