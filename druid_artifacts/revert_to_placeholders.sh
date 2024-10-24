#!/bin/bash

echo "Reverting JSON files back to templates..."

for file in cc_sec_log_*_ingestion.json; do
    echo "Processing $file..."
    
    # Create a temporary file with the modifications
    jq '
    (.spec.dataSchema.parser.avroBytesDecoder.url) = "{{SCHEMA_REGISTRY_URL}}" |
    (.spec.dataSchema.parser.avroBytesDecoder.config."basic.auth.user.info") = "{{SCHEMA_REGISTRY_API_KEY}}:{{SCHEMA_REGISTRY_API_SECRET}}" |
    (.spec.ioConfig.consumerProperties."bootstrap.servers") = "{{BOOTSTRAP_SERVERS}}" |
    (.spec.ioConfig.consumerProperties."sasl.jaas.config") = "org.apache.kafka.common.security.plain.PlainLoginModule required username=\"{{CC_API_KEY}}\" password=\"{{CC_API_KEY_SECRET}}\";"
    ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
    
    echo "Reverted $file back to template"
done

echo "All files have been reverted to templates"