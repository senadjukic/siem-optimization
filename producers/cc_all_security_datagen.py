import os
import sys
import json
import random
import time
import logging
from datetime import datetime, timezone
from dotenv import find_dotenv, load_dotenv
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Load environment variables
env_file = find_dotenv("cc.env")
load_dotenv(env_file)

# Kafka configuration with optimizations
kafka_config = {
    'bootstrap.servers': os.getenv('BOOTSTRAP_SERVERS'),
    'security.protocol': os.getenv('SECURITY_PROTOCOL'),
    'sasl.mechanism': os.getenv('SASL_MECHANISM'),
    'sasl.username': os.getenv('CC_API_KEY'),
    'sasl.password': os.getenv('CC_API_KEY_SECRET'),
    'client.id': os.getenv('CLIENT_ID')+'-producer',
    'compression.type': 'none',  # Disable compression
    'batch.size': 100000,  # Increase batch size (in bytes)
    'linger.ms': 100,  # Wait up to 100ms to batch messages
    'queue.buffering.max.messages': 1000000,  # Max messages to buffer in memory
}

# Schema Registry configuration
schema_registry_config = {
    'url': os.getenv('SCHEMA_REGISTRY_URL'),
    'basic.auth.user.info': f"{os.getenv('SCHEMA_REGISTRY_API_KEY')}:{os.getenv('SCHEMA_REGISTRY_API_SECRET')}"
}

# Topics and schema files
topics_and_schemas = {
    'syslog': {'topic': 'SECURITY_LOGS_SYSLOG', 'schema_file': 'schema_syslog.avsc'},
    'json': {'topic': 'SECURITY_LOGS_JSON', 'schema_file': 'schema_json.avsc'},
    'cef': {'topic': 'SECURITY_LOGS_CEF', 'schema_file': 'schema_cef.avsc'}
}

def create_topic(admin_client, topic_name, num_partitions=1, replication_factor=3):
    new_topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
    try:
        futures = admin_client.create_topics([new_topic])
        for topic, future in futures.items():
            future.result()  # The result itself is None
        print(f"Topic '{topic_name}' created successfully.")
    except Exception as e:
        print(f"Failed to create topic '{topic_name}': {e}")

def ensure_topic_exists(admin_client, topic_name):
    try:
        topic_metadata = admin_client.list_topics(timeout=5)
        if topic_name not in topic_metadata.topics:
            print(f"Topic '{topic_name}' does not exist. Creating it...")
            create_topic(admin_client, topic_name)
        else:
            print(f"Topic '{topic_name}' already exists.")
            action = input("Do you want to delete and recreate the topic, skip, or exit? (delete/skip/exit): \n").lower()
            if action == 'delete':
                admin_client.delete_topics([topic_name])
                print(f"Deleted topic '{topic_name}'. Waiting before recreating...")
                time.sleep(5)  # Wait for 5 seconds
                create_topic(admin_client, topic_name)
            elif action == 'skip':
                print(f"Skipping recreation of topic '{topic_name}'.")
            elif action == 'exit':
                print("Exiting program.")
                sys.exit(0)
            else:
                print("Invalid input. Skipping topic creation.")
    except Exception as e:
        print(f"Error checking/creating topic '{topic_name}': {e}")

def load_schema(schema_file):
    try:
        with open(schema_file, 'r') as f:
            schema_str = f.read()
            schema_dict = json.loads(schema_str)
            if 'type' not in schema_dict:
                schema_dict['type'] = 'object'
            if 'title' not in schema_dict:
                schema_dict['title'] = f"Schema for {schema_file}"
            return Schema(json.dumps(schema_dict), schema_type="JSON")
    except FileNotFoundError:
        print(f"Error: Schema file '{schema_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in schema file '{schema_file}'.")
        sys.exit(1)

def register_schema(schema_registry_client, subject, schema):
    try:
        versions = schema_registry_client.get_versions(subject)
        if versions:
            print(f"Schema for subject '{subject}' already exists.")
            action = input("Do you want to register a new version, delete all versions, or skip? (register/delete/skip): ").lower()
            if action == 'register':
                schema_id = schema_registry_client.register_schema(subject, schema)
                print(f"New schema version registered successfully. Schema ID: {schema_id}")
                return schema_id
            elif action == 'delete':
                for version in versions:
                    schema_registry_client.delete_version(subject, version)
                print(f"Deleted all versions of schema for subject '{subject}'.")
                schema_id = schema_registry_client.register_schema(subject, schema)
                print(f"New schema registered successfully. Schema ID: {schema_id}")
                return schema_id
            elif action == 'skip':
                print(f"Skipping schema registration for subject '{subject}'.")
                return schema_registry_client.get_latest_version(subject).schema_id
            else:
                print("Invalid input. Skipping schema registration.")
                return None
        else:
            schema_id = schema_registry_client.register_schema(subject, schema)
            print(f"Schema registered successfully. Schema ID: {schema_id}")
            return schema_id
    except Exception as e:
        print(f"Error registering schema: {e}")
        return None

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        # print(f'Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')
        pass

def get_global_action():
    while True:
        action = input("Do you want to delete and recreate all topics and schemas, skip, or exit? ([d]elete/[s]kip/[e]xit): ").lower()
        if action in ['d', 'delete', 's', 'skip', 'e', 'exit']:
            return action[0]  # Return just the first letter
        print("Invalid input. Please try again.")

# Generate a list of 50 unique IP addresses
source_ips = [f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}" for _ in range(50)]
destination_ips = [f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}" for _ in range(50)]

def get_unique_ips():
    src_ip = random.choice(source_ips)
    dst_ip = random.choice([ip for ip in destination_ips if ip != src_ip])
    return src_ip, dst_ip

def load_avro_schema(schema_file):
    try:
        with open(schema_file, 'r') as f:
            schema_str = f.read()
            return Schema(schema_str, schema_type="AVRO")
    except FileNotFoundError:
        print(f"Error: Schema file '{schema_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid Avro schema in file '{schema_file}'.")
        sys.exit(1)

# Update generate functions to return dictionaries (Avro-compatible)
def generate_syslog(count):
    src_ip, dst_ip = get_unique_ips()
    return {
        "priority": random.randint(0, 191),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": f"host-{random.randint(1, 100)}",
        "application": "security-app",
        "process_id": str(random.randint(1000, 9999)),
        "message": f"Security event {count:09} occurred from {src_ip} to {dst_ip}",
        "event_time": int(time.time() * 1000)
    }

def generate_json_log(count):
    src_ip, dst_ip = get_unique_ips()
    return {
        "log_id": f'{count:09}',
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": random.choice(["login", "logout", "file_access", "network_access", "system_update"]),
        "status": random.choice(["success", "failure", "warning"]),
        "username": random.choice(["admin", "user1", "user2", "system", "root", "guest"]),
        "source_ip": src_ip,
        "destination_ip": dst_ip,
        "details": f"Security event details for log {count:09}",
        "event_time": int(time.time() * 1000)
    }

def generate_cef_log(count):
    src_ip, dst_ip = get_unique_ips()
    return {
        "version": "0",
        "device_vendor": random.choice(["Microsoft", "Cisco", "Symantec", "Palo Alto"]),
        "device_product": random.choice(["Windows", "ASA", "Endpoint Protection", "NGFW"]),
        "device_version": random.choice(["10.0", "9.8", "14.2", "8.1"]),
        "signature_id": str(random.choice([4625, 106023, 8001, 13001])),
        "name": random.choice(["Login Failure", "Access Denied", "Malware Detected", "Traffic Allowed"]),
        "severity": str(random.randint(1, 10)),
        "extension": {
            "src": src_ip,
            "dst": dst_ip,
            "spt": random.randint(1024, 65535),
            "dpt": random.randint(1, 1023),
            "proto": random.choice(["TCP", "UDP", "ICMP"]),
            "msg": f"Security event {count:09}"
        },
        "event_time": int(time.time() * 1000)
    }

def handle_topics_and_schemas(admin_client, schema_registry_client):
    action = get_global_action()
    
    if action == 'e':
        print("Exiting program.")
        sys.exit(0)
    
    serializers = {}
    for log_type, info in topics_and_schemas.items():
        topic_name = info['topic']
        schema_subject = f"{topic_name}-value"
        
        if action == 'd':
            # Delete and recreate topic
            try:
                admin_client.delete_topics([topic_name])
                print(f"Deleted topic '{topic_name}'. Waiting before recreating...")
                time.sleep(5)  # Wait for 5 seconds
            except Exception as e:
                print(f"Error deleting topic '{topic_name}': {e}")
            
            create_topic(admin_client, topic_name)
            
            # Delete all schema versions and recreate
            try:
                versions = schema_registry_client.get_versions(schema_subject)
                for version in versions:
                    schema_registry_client.delete_version(schema_subject, version)
                print(f"Deleted all versions of schema for subject '{schema_subject}'.")
            except Exception as e:
                print(f"Error deleting schema versions for '{schema_subject}': {e}")
        
        # Load and register schema
        schema = load_avro_schema(info['schema_file'])
        try:
            schema_id = schema_registry_client.register_schema(schema_subject, schema)
            print(f"Schema registered successfully for '{schema_subject}'. Schema ID: {schema_id}")
            serializers[log_type] = AvroSerializer(schema_registry_client, schema.schema_str)
        except Exception as e:
            print(f"Error registering schema for '{schema_subject}': {e}")
    
    return serializers

def main():
    # Suppress excessive logging
    logging.getLogger('confluent_kafka').setLevel(logging.ERROR)

    admin_client = AdminClient(kafka_config)
    schema_registry_client = SchemaRegistryClient(schema_registry_config)

    serializers = handle_topics_and_schemas(admin_client, schema_registry_client)

    # If no schemas were successfully registered/loaded, exit the program
    if not serializers:
        print("No schemas were successfully registered or loaded. Exiting.")
        return

    # Create producer
    producer = Producer(kafka_config)

    print("Producer initialized, start to produce")

    try:
        for i in range(1000000):  # Adjust the number of messages as needed
            log_type = random.choice(list(serializers.keys()))
            
            if log_type == 'syslog':
                data = generate_syslog(i)
            elif log_type == 'json':
                data = generate_json_log(i)
            else:  # cef
                data = generate_cef_log(i)

            producer.produce(
                topic=topics_and_schemas[log_type]['topic'],
                key=str(i),
                value=serializers[log_type](data, SerializationContext(topics_and_schemas[log_type]['topic'], MessageField.VALUE)),
                on_delivery=delivery_report
            )

            producer.poll(0)

            if i % 10000 == 0 and i > 0:
                print(f"Produced {i} messages")

        producer.flush()

    except KeyboardInterrupt:
        print("Interrupted by user, shutting down...")
    finally:
        producer.flush()

if __name__ == "__main__":
    main()