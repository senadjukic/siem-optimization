curl -X POST \
     -H "Content-Type: application/json" \
     -u "druid_system:password2" \
     -d @cc_sec_log_json_ingestion.json \
     http://localhost:8888/druid/indexer/v1/supervisor

curl -X POST \
     -H "Content-Type: application/json" \
     -u "druid_system:password2" \
     -d @cc_sec_log_syslog_ingestion.json \
     http://localhost:8888/druid/indexer/v1/supervisor

curl -X POST \
     -H "Content-Type: application/json" \
     -u "druid_system:password2" \
     -d @cc_sec_log_cef_ingestion.json \
     http://localhost:8888/druid/indexer/v1/supervisor