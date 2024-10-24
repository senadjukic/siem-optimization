import os
import time
from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from dotenv import find_dotenv, load_dotenv
from prettytable import PrettyTable

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
    'group.id': 'topic_monitor',
    'auto.offset.reset': 'latest'
}

# Schema Registry configuration
schema_registry_conf = {
    'url': os.getenv('SCHEMA_REGISTRY_URL'),
    'basic.auth.user.info': f"{os.getenv('SCHEMA_REGISTRY_API_KEY')}:{os.getenv('SCHEMA_REGISTRY_API_SECRET')}"
}

# Topics to monitor
topics = ['SECURITY_LOGS_SYSLOG', 'SECURITY_LOGS_JSON', 'SECURITY_LOGS_CEF']

# Create Schema Registry client
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# Dictionary to store AvroDeserializer instances for each topic
avro_deserializers = {}

def get_schema_and_deserializer(topic):
    try:
        schema_str = schema_registry_client.get_latest_version(f"{topic}-value").schema.schema_str
        return AvroDeserializer(schema_registry_client, schema_str)
    except Exception as e:
        print(f"Failed to fetch schema for topic {topic}: {e}")
        return None

def pretty_print_message(topic, message, offset):
    table = PrettyTable()
    table.field_names = ["Attribute", "Value"]
    table.align["Attribute"] = "r"
    table.align["Value"] = "l"

    table.add_row(["Topic", topic])
    table.add_row(["Offset", offset])
    
    if isinstance(message, dict):
        for key, value in message.items():
            table.add_row([key, str(value)])
    elif isinstance(message, bytes):
        table.add_row(["Raw message (hex)", message.hex()])
    else:
        table.add_row(["Message", str(message)])

    print(table)
    print("\n" + "="*50 + "\n")

def get_latest_message(consumer, topic):
    # Get metadata for all topics
    metadata = consumer.list_topics(topic, timeout=10)
    
    if topic not in metadata.topics:
        print(f"Topic {topic} not found")
        return None

    topic_metadata = metadata.topics[topic]
    partitions = topic_metadata.partitions
    
    if not partitions:
        print(f"No partitions found for topic {topic}")
        return None

    # For simplicity, we're just using the first partition
    partition = list(partitions.keys())[0]
    tp = TopicPartition(topic, partition)
    
    # Get the last offset
    low, high = consumer.get_watermark_offsets(tp)
    if high > 0:
        tp.offset = high - 1  # Set the TopicPartition to point to the last message
        consumer.assign([tp])
        msg = consumer.poll(1.0)
        if msg is None:
            print(f"Failed to fetch message for topic {topic}")
            return None
        if msg.error():
            print(f"Error fetching message: {msg.error()}")
            return None
        return msg
    else:
        print(f"No messages in topic {topic}")
        return None

def deserialize_avro(msg_value, topic):
    if topic not in avro_deserializers:
        avro_deserializers[topic] = get_schema_and_deserializer(topic)
    
    deserializer = avro_deserializers[topic]
    if deserializer is None:
        return None

    try:
        return deserializer(msg_value, SerializationContext(topic, MessageField.VALUE))
    except Exception as e:
        print(f"Failed to deserialize message: {e}")
        return None

def main():
    while True:
        try:
            consumer = Consumer(kafka_config)

            print("Connected to Confluent Cloud. Fetching latest messages...")

            for topic in topics:
                msg = get_latest_message(consumer, topic)
                if msg:
                    # Try to deserialize with Avro
                    deserialized_value = deserialize_avro(msg.value(), msg.topic())
                    if deserialized_value is not None:
                        pretty_print_message(msg.topic(), deserialized_value, msg.offset())
                    else:
                        # If Avro deserialization fails, print as hex
                        pretty_print_message(msg.topic(), msg.value(), msg.offset())
                else:
                    print(f"No message retrieved for topic {topic}")
                print("\n")

            break  # Exit after fetching messages once

        except KafkaException as e:
            print(f"Kafka Exception: {e}")
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Interrupted by user, shutting down...")
            break
        finally:
            consumer.close()

if __name__ == "__main__":
    main()