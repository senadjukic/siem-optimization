#!/bin/bash

# Source the environment variables
source ../producers/cc.env

echo "Applying values from environment to JSON files..."

for file in cc_sec_log_*_ingestion.json; do
    echo "Processing $file..."
    
    # Create a temporary file with the modifications
    jq --arg sr_url "$SCHEMA_REGISTRY_URL" \
       --arg sr_key "$SCHEMA_REGISTRY_API_KEY" \
       --arg sr_secret "$SCHEMA_REGISTRY_API_SECRET" \
       --arg bs "$BOOTSTRAP_SERVERS" \
       --arg cc_key "$CC_API_KEY" \
       --arg cc_secret "$CC_API_KEY_SECRET" \
    '
    (.spec.dataSchema.parser.avroBytesDecoder.url) = $sr_url |
    (.spec.dataSchema.parser.avroBytesDecoder.config."basic.auth.user.info") = ($sr_key + ":" + $sr_secret) |
    (.spec.ioConfig.consumerProperties."bootstrap.servers") = $bs |
    (.spec.ioConfig.consumerProperties."sasl.jaas.config") = "org.apache.kafka.common.security.plain.PlainLoginModule required username=\"" + $cc_key + "\" password=\"" + $cc_secret + "\";"
    ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
    
    echo "Applied values to $file"
done

echo "All files have been updated with environment values"