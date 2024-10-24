import os
import json
import random
import time
from datetime import datetime, timezone
from dotenv import find_dotenv, load_dotenv
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Load environment variables
env_file = find_dotenv("cc.env")
load_dotenv(env_file)

# Kafka configuration
kafka_config = {
    'bootstrap.servers': os.getenv('BOOTSTRAP_SERVERS'),
    'security.protocol': os.getenv('SECURITY_PROTOCOL'),
    'sasl.mechanism': os.getenv('SASL_MECHANISM'),
    'sasl.username': os.getenv('CC_API_KEY'),
    'sasl.password': os.getenv('CC_API_KEY_SECRET'),
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

def load_avro_schema(schema_file):
    with open(schema_file, 'r') as f:
        schema_str = f.read()
    return schema_str

def generate_syslog(count):
    return {
        "priority": random.randint(0, 191),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": f"host-{random.randint(1, 100)}",
        "application": "security-app",
        "process_id": str(random.randint(1000, 9999)),
        "message": f"Security event {count} occurred",
        "event_time": int(time.time() * 1000)
    }

def generate_json_log(count):
    return {
        "log_id": f'{count:09}',
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": random.choice(["login", "logout", "file_access", "network_access", "system_update"]),
        "status": random.choice(["success", "failure", "warning"]),
        "username": random.choice(["admin", "user1", "user2", "user3", "system", "root", "guest"]),
        "source_ip": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "destination_ip": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "details": f"Security event details for log {count}",
        "event_time": int(time.time() * 1000)
    }

def generate_cef_log(count):
    return {
        "version": "0",
        "device_vendor": random.choice(["Microsoft", "Cisco", "Symantec", "Palo Alto"]),
        "device_product": random.choice(["Windows", "ASA", "Endpoint Protection", "NGFW"]),
        "device_version": random.choice(["10.0", "9.8", "14.2", "8.1"]),
        "signature_id": str(random.choice([4625, 106023, 8001, 13001])),
        "name": random.choice(["Login Failure", "Access Denied", "Malware Detected", "Traffic Allowed"]),
        "severity": str(random.randint(1, 10)),
        "extension": {
            "src": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "dst": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "spt": random.randint(1024, 65535),
            "dpt": random.randint(1, 1023),
            "proto": random.choice(["TCP", "UDP", "ICMP"]),
            "msg": f"Security event {count}"
        },
        "event_time": int(time.time() * 1000)
    }

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')

def main():
    schema_registry_client = SchemaRegistryClient(schema_registry_config)
    producer = Producer(kafka_config)

    serializers = {}
    for log_type, info in topics_and_schemas.items():
        schema_str = load_avro_schema(info['schema_file'])
        serializers[log_type] = AvroSerializer(schema_registry_client, schema_str)

    print("Producer initialized, starting to produce 10 messages for each topic")

    for log_type, info in topics_and_schemas.items():
        for i in range(10):
            if log_type == 'syslog':
                data = generate_syslog(i)
            elif log_type == 'json':
                data = generate_json_log(i)
            else:  # cef
                data = generate_cef_log(i)

            producer.produce(
                topic=info['topic'],
                key=str(i),
                value=serializers[log_type](data, SerializationContext(info['topic'], MessageField.VALUE)),
                on_delivery=delivery_report
            )
            producer.poll(0)

        print(f"Produced 10 messages for topic {info['topic']}")

    producer.flush()
    print("All messages produced successfully")

if __name__ == "__main__":
    main()