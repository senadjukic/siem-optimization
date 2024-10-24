-- 1. Correlation between JSON and CEF logs
SELECT
    TIME_FLOOR(JSON_LOGS."__time", 'PT1H'),
    JSON_LOGS."__time" AS event_time,
    JSON_LOGS.source_ip,
    JSON_LOGS.event_type,
    JSON_LOGS.status,
    CEF_LOGS.name AS cef_event,
    CEF_LOGS.severity
FROM "SECURITY_LOGS_JSON" AS JSON_LOGS
JOIN "SECURITY_LOGS_CEF" AS CEF_LOGS
ON JSON_LOGS.source_ip = JSON_VALUE(CEF_LOGS.extension, '$.src')
AND TIME_FLOOR(JSON_LOGS."__time", 'PT1H') = TIME_FLOOR(CEF_LOGS."__time", 'PT1H')
WHERE JSON_LOGS."__time" >= CURRENT_TIMESTAMP - INTERVAL '1' DAY
AND JSON_LOGS."__time" < CURRENT_TIMESTAMP
AND (JSON_LOGS.status = 'failure' OR CAST(CEF_LOGS.severity AS INTEGER) >= 7)
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY 1 DESC, 2 DESC
LIMIT 10

-- 2. Time-based analysis of event frequency across all log types
SELECT
    TIME_FLOOR(SECURITY_LOGS_JSON."__time", 'PT30M') AS half_hour_bucket,
    'JSON' AS log_type,
    COUNT(*) AS event_count
FROM "SECURITY_LOGS_JSON"
GROUP BY TIME_FLOOR(SECURITY_LOGS_JSON."__time", 'PT30M')

UNION ALL

SELECT
    TIME_FLOOR(SECURITY_LOGS_SYSLOG."__time", 'PT30M') AS half_hour_bucket,
    'Syslog' AS log_type,
    COUNT(*) AS event_count
FROM "SECURITY_LOGS_SYSLOG"
GROUP BY TIME_FLOOR(SECURITY_LOGS_SYSLOG."__time", 'PT30M')

UNION ALL

SELECT
    TIME_FLOOR(SECURITY_LOGS_CEF."__time", 'PT30M') AS half_hour_bucket,
    'CEF' AS log_type,
    COUNT(*) AS event_count
FROM "SECURITY_LOGS_CEF"
GROUP BY TIME_FLOOR(SECURITY_LOGS_CEF."__time", 'PT30M')
LIMIT 100

-- 3. Identifying potential security incidents
SELECT
    TIME_FLOOR(JSON_LOGS."__time", 'PT1H') AS time_window,
    JSON_LOGS.source_ip,
    JSON_LOGS.event_type AS json_event,
    JSON_LOGS.status AS json_status,
    CEF_LOGS.name AS cef_event,
    CEF_LOGS.severity AS cef_severity
FROM "SECURITY_LOGS_JSON" AS JSON_LOGS
INNER JOIN "SECURITY_LOGS_CEF" AS CEF_LOGS
    ON JSON_LOGS.source_ip = JSON_VALUE(CEF_LOGS.extension, '$.src')
    AND TIME_FLOOR(JSON_LOGS."__time", 'PT1H') = TIME_FLOOR(CEF_LOGS."__time", 'PT1H')
WHERE 
    JSON_LOGS.status = 'failure' 
    OR CAST(CEF_LOGS.severity AS INTEGER) >= 7
LIMIT 50


-- 4. Analyzing event sequences for a given source IP
SELECT
    source_ip,
    COUNT(*) AS event_count,
    CONCAT(event_type, '|', status) AS event_sequence_sample
FROM "SECURITY_LOGS_JSON"
WHERE status = 'failure'
    AND "__time" BETWEEN TIMESTAMP '2000-01-01' AND TIMESTAMP '3000-01-01'
GROUP BY source_ip , CONCAT(event_type, '|', status)
LIMIT 100