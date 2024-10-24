/*
1. Provide login pattern 3x warning followed by a failure login event
2. Create Users Table
3. Enrich failed login attempts with user details
4. Register OpenAI model
5. Invoke OpenAI model with enriched context from the failed login attempts
*/

-- MATCH RECOGNIZE SAMPLE: 3x warning followed by a failure login event
SELECT *
FROM SECURITY_LOGS_JSON
MATCH_RECOGNIZE (
    PARTITION BY username
    ORDER BY $rowtime
    MEASURES
      COUNT(W.status) AS warning_count,
      F.`timestamp` AS failure_time,
      F.source_ip AS failure_source_ip,
      F.details AS failed_details
    ONE ROW PER MATCH
    AFTER MATCH SKIP PAST LAST ROW
    PATTERN (W{3,} F) 
    DEFINE
        W AS W.status = 'warning' AND W.event_type = 'login', 
        F AS F.status = 'failure' AND W.event_type = 'login'
) AS suspicious_logins;

-- Create table for failed login attempts
CREATE TABLE FAILED_LOGIN_ATTEMPTS (
    `username` STRING,
    `warning_count` BIGINT,
    `failure_time` STRING,
    `failure_source_ip` STRING,
    `failed_details` STRING,
    PRIMARY KEY (username) NOT ENFORCED) AS
        SELECT username,
              warning_count,
              failure_time,
              failure_source_ip,
              failed_details
        FROM SECURITY_LOGS_JSON
        MATCH_RECOGNIZE (
            PARTITION BY username
            ORDER BY $rowtime
            MEASURES
                COUNT(W.status) AS warning_count,
                F.`timestamp` AS failure_time,
                F.source_ip AS failure_source_ip,
                F.details AS failed_details
            ONE ROW PER MATCH
            AFTER MATCH SKIP PAST LAST ROW
            PATTERN (W{3,} F)
            DEFINE
                W AS W.status = 'warning' AND W.event_type = 'login',
                F AS F.status = 'failure' AND F.event_type = 'login'
        ) AS suspicious_logins;

/* If you have no matches but want to produce more data and retry:
INSERT INTO FAILED_LOGIN_ATTEMPTS
SELECT 
    username,
    warning_count,
    failure_time,
    failure_source_ip,
    failed_details
FROM SECURITY_LOGS_JSON
MATCH_RECOGNIZE (
    PARTITION BY username
    ORDER BY $rowtime
    MEASURES
        COUNT(W.status) AS warning_count,
        F.`timestamp` AS failure_time,
        F.source_ip AS failure_source_ip,
        F.details AS failed_details
    ONE ROW PER MATCH
    AFTER MATCH SKIP PAST LAST ROW
    PATTERN (W{3,} F)
    DEFINE
        W AS W.status = 'warning' AND W.event_type = 'login',
        F AS F.status = 'failure' AND F.event_type = 'login'
) AS suspicious_logins;
*/

-- Create table for users
CREATE TABLE USER_DETAILS (
    `username` STRING PRIMARY KEY NOT ENFORCED,	
    `first_name` STRING,
    `last_name` STRING,
    `language` STRING,
    `mail` STRING
)

-- Create sample data
INSERT INTO USER_DETAILS VALUES 
    ('user1', 'John', 'Smith', 'English', 'john.smith@email.com'),
    ('user2', 'Maria', 'Garcia', 'Spanish', 'maria.garcia@email.com'),
    ('admin', 'Hans', 'Mueller', 'German', 'hans.mueller@email.com'),
    ('system', 'Sophie', 'Dubois', 'French', 'sophie.dubois@email.com'),
    ('root', 'Anna', 'Kowalski', 'Polish', 'anna.kowalski@email.com'),
    ('guest', 'Marco', 'Rossi', 'Italian', 'marco.rossi@email.com'),
    ('user3', 'Lars', 'Anderson', 'Swedish', 'lars.anderson@email.com');
  

-- Enrich failed login attempts with user details
CREATE TABLE ENRICHED_FAILED_LOGINS (
  PRIMARY KEY (username) NOT ENFORCED
  ) DISTRIBUTED BY HASH(username) INTO 1 BUCKETS 
  AS SELECT u.username, CONCAT (
    `language`, ', ', 
    first_name, ', ', 
    last_name, ', ', 
    mail, ', ', 
    CAST(warning_count AS STRING), ', ', 
    f.failure_time, ', ', 
    f.failure_source_ip, ', ', 
    f.failed_details) AS big_string
  FROM `FAILED_LOGIN_ATTEMPTS` f
  INNER JOIN `USER_DETAILS` u
  ON  f.username = u.username;

/* Register OpenAI model - https://docs.confluent.io/cloud/current/flink/reference/functions/model-inference-functions.html
-- Create connection first via Flink Shell, make sure you have Confluent CLI > v4.7.0
confluent flink connection create openaiazure \
  --cloud azure \
  --region westeurope \
  --type azureopenai \
  --endpoint https://xxx.openai.azure.com/openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-08-01-preview \
  --api-key <api-key>
*/

CREATE MODEL `security_messages`
INPUT (`failed_login` VARCHAR(2147483647))
OUTPUT (`user_mail` VARCHAR(2147483647))
COMMENT 'create warning mail to user with failed login attemps'
WITH (
  'azureopenai.connection' = 'openaiazure',
  'azureopenai.model_version' = 'gpt-35-turbo',
  'azureopenai.system_prompt' = 'User has failed to login in our company system multiple times. Provided is security log in form of CSV message with values: language, first_name, last_name, mail, warning_count, failure_time, source_ip, log_id. Create response to the user in prefered language that summarises what happened. Write in JSON format: {"mail":"mail address", "mail":"generated mail message text"}',
  'provider' = 'azureopenai',
  'task' = 'text_generation'
);

-- Invoke OpenAI model with enriched context from the failed login attempts
SELECT username, user_mail FROM ENRICHED_FAILED_LOGINS, LATERAL TABLE(ML_PREDICT('security_messages', big_string));
