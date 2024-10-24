# SIEM Optimization with Confluent Cloud, Flink, Druid, and Superset

This project implements a modern Security Information and Event Management (SIEM) system using Confluent Cloud for event streaming, Flink for real-time processing, Apache Druid for fast analytics, and Apache Superset for visualization.

## Architecture Overview

The system consists of several components:
- **Confluent Cloud**: Handles event streaming and Schema Registry
- **Flink SQL**: Processes security events in real-time
- **Apache Druid**: Provides fast analytics on historical data
- **Apache Superset**: Offers visualization and dashboarding capabilities

## Security Events Processing
The system processes three types of security logs:
- Syslog format logs
- JSON format security events
- Common Event Format (CEF) logs

## Prerequisites
- Confluent Cloud account
- Docker and Docker Compose
- Python 3.8+
- Access to Azure OpenAI (optional)

## Setup Instructions

### 1. Confluent Cloud Setup
Create a basic cluster in a Confluent Cloud Flink-supported region:
- Visit: https://docs.confluent.io/cloud/current/flink/reference/cloud-regions.html
- Create cluster at: https://confluent.cloud/

### 2. Flink Compute Pool
Create a Flink compute pool in the same region as your Kafka cluster:
- Go to Confluent Cloud UI
- Navigate to Flink
- Create new compute pool
- Note: Ensure the region matches your Kafka cluster

### 3. Optional: Druid Setup
Start Zookeeper and Druid services:
```bash
docker compose -f ./druid_setup/docker-compose.yaml up -d

# Verify containers are running
./check_containers_running.sh zookeeper postgres coordinator middlemanager router broker historical
```

Access Druid UI:
- URL: `http://localhost:8888`
- Credentials:
  - Username: druid_system
  - Password: password2

### 4. Optional: Superset Setup
Start Superset services:
```bash
docker compose -f ./superset_setup/docker-compose.yaml up -d

# Verify containers are running
./check_containers_running.sh superset_worker superset_worker_beat superset_app superset_db superset_cache
```

Access Superset UI:
- URL: `http://localhost:8088/dashboard/list/?pageIndex=0&sortColumn=changed_on_delta_humanized&sortOrder=desc&viewMode=table`
- Credentials:
  - Username: admin
  - Password: admin

### 5. Druid Ingestion Setup
Configure and start Kafka to Druid ingestion:
```bash
cd druid_artifacts/
./clean-druid.sh            # Clean existing ingestion tasks
./apply_cc_values.sh        # Apply Confluent Cloud credentials
./post-ingestion-tasks.sh   # Start ingestion tasks
cd ..
```

### 6. Confluent Cloud API Setup
1. Navigate to "Cluster Overview" > "API Keys"
2. Create new API key
3. Download credentials file

### 7. Producer Setup
```bash
# Setup Python environment
cd ./producers
python3 -m virtualenv env
source env/bin activate
pip3 install -r requirements.txt

# Parse API credentials
python3 cc_parse_api_key_file.py "<download_directory>" "./cc.env"
```

### 8. Schema Registry Setup
1. Create Schema Registry API key:
   - Navigate to: `https://confluent.cloud/environments/<env-id>/schema-registry/api-keys`
2. Add credentials to `./producers/cc.env`
3. Start data generation:
   ```bash
   python3 cc_all_security_datagen.py
   ```

Monitor messages:
```bash
# View latest messages with pretty printing
python3 cc_print_last_record_avro.py
```

### 9. Flink SQL Configuration
1. Open Flink SQL Workspace in Confluent Cloud UI
2. Execute SQL scripts from `./flink-sql/` directory

Optional: Configure OpenAI integration:
```bash
confluent flink connection create openaiazure \
  --cloud azure \
  --region westeurope \
  --type azureopenai \
  --endpoint https://xxx.openai.azure.com/openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-08-01-preview \
  --api-key <api-key>
```

### 10. Query Data
- Druid queries available in: `./druid-artifacts/druid-raw.sql`
- Superset dashboards: Coming soon in `./superset_dashboard`

### 11. Generate Additional Data
```bash
cd ./producers/
python3 cc_produce_more.py
```

## Component Details

### Security Log Types
1. **Syslog Format**:
   - Traditional system logs
   - Contains priority, timestamp, hostname, and message

2. **JSON Security Events**:
   - Structured security event data
   - Includes event type, status, username, and IP information

3. **CEF (Common Event Format)**:
   - Standardized security event format
   - Contains vendor, product, and detailed event information

### Data Processing Pipeline
1. **Event Generation**:
   - Python producers generate synthetic security events
   - Multiple formats supported
   - Schema Registry ensures data consistency

2. **Real-time Processing**:
   - Flink SQL analyzes events in real-time
   - Pattern matching for security incidents
   - Event enrichment with user data

3. **Analytics and Storage**:
   - Druid provides fast querying capabilities
   - Historical data analysis
   - Efficient storage and retrieval

4. **Visualization**:
   - Superset dashboards for monitoring
   - Custom charts and reports
   - Real-time updates

## Troubleshooting

Common issues and solutions:
1. **Connection Issues**:
   - Verify Confluent Cloud credentials
   - Check network connectivity
   - Ensure proper permissions

2. **Schema Registry**:
   - Verify API keys
   - Check schema compatibility
   - Review error messages

3. **Container Issues**:
   - Use `docker logs <container_name>` for details
   - Verify port availability
   - Check resource usage

## Additional Resources
- [Confluent Cloud Documentation](https://docs.confluent.io/cloud/current/overview.html)
- [Apache Flink Documentation](https://flink.apache.org/docs/stable/)
- [Apache Druid Documentation](https://druid.apache.org/docs/latest/design/)
- [Apache Superset Documentation](https://superset.apache.org/docs/intro)