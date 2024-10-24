
/*
1. JSON Log Analysis: Provides a time-based summary of events from the JSON logs.
2. Syslog Analysis: Summarizes syslog events by application and priority.
3. CEF Log Analysis: Gives an overview of CEF events by vendor, product, and severity.
4. Top Source IPs: Identifies the most active source IPs from JSON logs, focusing on failure events.
5. High Severity CEF Events: Lists the most severe events from the CEF logs.
6. Syslog-JSON Correlation: Attempts to correlate syslog and JSON events based on hostname/source_ip and timestamp.
7. Detect potential security incidents

Background:
1. Performs a time-based analysis of log events:
   * Groups events into 1-minute windows
   * Counts events per log type and application
   * Calculates average severity
   * Counts unique sources
   * Filters for windows with more than 10 events
4. Identifies top sources of high failure events:
   * Counts events per source IP
   * Filters for sources with failure
   * Ranks source IPs by number of events
7. Detects potential security incidents:
   * Looks for high-severity events (severity >= 7)
   * Searches for keywords in the details field
   * Orders results by time and limits to the most recent 100 incidents
*/

-- 1. Analysis of JSON logs
SELECT
    SUBSTR(`timestamp`, 1, 16) AS time_window,
    event_type,
    status,
    COUNT(*) AS event_count,
    COUNT(DISTINCT username) AS unique_users,
    COUNT(DISTINCT source_ip) AS unique_sources,
    COUNT(DISTINCT destination_ip) AS unique_destinations
FROM `SECURITY_LOGS_JSON`
GROUP BY 
    SUBSTR(`timestamp`, 1, 16),
    event_type,
    status
HAVING COUNT(*) > 10
ORDER BY 
    time_window DESC,
    event_count DESC
LIMIT 100;

-- 2. Analysis of Syslog data
SELECT
    SUBSTR(`timestamp`, 1, 16) AS time_window,
    application,
    priority,
    COUNT(*) AS event_count,
    COUNT(DISTINCT hostname) AS unique_hosts
FROM `SECURITY_LOGS_SYSLOG`
GROUP BY 
    SUBSTR(`timestamp`, 1, 16),
    application,
    priority
HAVING COUNT(*) > 5
ORDER BY 
    time_window DESC,
    event_count DESC
LIMIT 100;

-- 3. Analysis of CEF logs
SELECT
    device_vendor,
    device_product,
    name,
    severity,
    COUNT(*) AS event_count,
    COUNT(DISTINCT extension['src']) AS unique_sources,
    COUNT(DISTINCT extension['dst']) AS unique_destinations
FROM `SECURITY_LOGS_CEF`
GROUP BY 
    device_vendor,
    device_product,
    name,
    severity
HAVING COUNT(*) > 5
ORDER BY 
    event_count DESC
LIMIT 100;

-- 4. Top source IPs from JSON logs
SELECT
    source_ip,
    COUNT(*) AS event_count,
    COUNT(DISTINCT event_type) AS unique_event_types,
    COUNT(DISTINCT username) AS unique_users
FROM `SECURITY_LOGS_JSON`
WHERE status = 'failure'
GROUP BY source_ip
HAVING COUNT(*) > 5
ORDER BY event_count DESC
LIMIT 20;

-- 5. High severity events from CEF logs
SELECT
    name AS event_name,
    severity,
    extension['src'] AS source_ip,
    extension['dst'] AS destination_ip,
    extension['msg'] AS message
FROM `SECURITY_LOGS_CEF`
WHERE CAST(severity AS INT) >= 7
ORDER BY CAST(severity AS INT) DESC
LIMIT 100;

-- 6. Correlation between SYSLOG and JSON logs (based on hostname/source_ip)
SELECT
    s.hostname,
    s.application AS syslog_application,
    s.priority AS syslog_priority,
    j.event_type AS json_event_type,
    j.status AS json_status,
    COUNT(*) AS correlated_events
FROM `SECURITY_LOGS_SYSLOG` s
JOIN `SECURITY_LOGS_JSON` j
    ON SUBSTR(s.`timestamp`, 1, 16) = SUBSTR(j.`timestamp`, 1, 16)
GROUP BY
    s.hostname,
    s.application,
    s.priority,
    j.event_type,
    j.status
HAVING COUNT(*) > 1
ORDER BY correlated_events DESC
LIMIT 50;

-- 7. Detect potential security incidents
SELECT
    `timestamp`,
    log_id,
    event_type,
    status,
    username,
    source_ip,
    destination_ip,
    details
FROM `SECURITY_LOGS_JSON`
WHERE
    status = 'failure'
    OR details LIKE '%unauthorized%'
    OR details LIKE '%malware%'
    OR details LIKE '%breach%'
    OR details LIKE '%attack%'
ORDER BY `timestamp` DESC
LIMIT 100;