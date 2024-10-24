#!/bin/bash

# Druid connection details
DRUID_HOST="localhost:8888"  # Druid router host
DRUID_COORDINATOR_HOST="localhost:28081"  # Druid coordinator host
DRUID_OVERLORD_HOST="localhost:8888"  # Druid overlord host

# Authentication
DRUID_BASIC_AUTH="druid_system:password2"

# Function to make API calls
druid_api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local response=$(curl -X $method -H "Content-Type: application/json" \
         -u "$DRUID_BASIC_AUTH" \
         -s -w "\nHTTP_STATUS:%{http_code}\n" \
         ${data:+-d "$data"} \
         "http://$endpoint")
    echo "$response"
    if [[ "$response" == *"HTTP_STATUS:200"* ]]; then
        return 0
    else
        return 1
    fi
}

# Confirm action
confirm() {
    read -p "$1 (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
}

echo "WARNING: This script will delete all datasources, segments, and ingestion tasks in Druid."
confirm "Are you sure you want to proceed?"

# Stop all supervisors
echo "Stopping all supervisors..."
supervisors=$(druid_api_call GET "${DRUID_OVERLORD_HOST}/druid/indexer/v1/supervisor" | sed '$d' | jq -r '.[]')
for supervisor in $supervisors; do
    echo "Stopping supervisor: $supervisor"
    druid_api_call POST "${DRUID_OVERLORD_HOST}/druid/indexer/v1/supervisor/$supervisor/shutdown"
done

# Terminate all running tasks
echo "Terminating all running tasks..."
tasks=$(druid_api_call GET "${DRUID_OVERLORD_HOST}/druid/indexer/v1/tasks" | sed '$d' | jq -r '.[].id')
for task in $tasks; do
    echo "Terminating task: $task"
    druid_api_call POST "${DRUID_OVERLORD_HOST}/druid/indexer/v1/task/$task/shutdown"
done

echo "Waiting for supervisors and tasks to fully stop..."
sleep 30

# Get list of all datasources
datasources=$(druid_api_call GET "${DRUID_COORDINATOR_HOST}/druid/coordinator/v1/metadata/datasources" | sed '$d' | jq -r '.[]')

# Delete each datasource and its segments
for datasource in $datasources; do
    echo "Deleting datasource and segments: $datasource"
    if druid_api_call DELETE "${DRUID_COORDINATOR_HOST}/druid/coordinator/v1/datasources/$datasource?kill=true&interval=1000/3000"; then
        echo "Successfully deleted datasource: $datasource"
    else
        echo "Failed to delete datasource: $datasource. Attempting force deletion..."
        if druid_api_call DELETE "${DRUID_COORDINATOR_HOST}/druid/coordinator/v1/datasources/$datasource?kill=true&interval=1000/3000&force=true"; then
            echo "Force deletion successful for datasource: $datasource"
        else
            echo "Force deletion failed for datasource: $datasource"
        fi
    fi
    
    # Double-check if segments are deleted
    segments=$(druid_api_call GET "${DRUID_COORDINATOR_HOST}/druid/coordinator/v1/datasources/$datasource/segments" | sed '$d' | jq -r '.[]')
    if [ -n "$segments" ]; then
        echo "Some segments still exist for $datasource. Attempting individual deletion..."
        for segment in $segments; do
            if druid_api_call DELETE "${DRUID_COORDINATOR_HOST}/druid/coordinator/v1/datasources/$datasource/segments/$segment"; then
                echo "Deleted segment: $segment"
            else
                echo "Failed to delete segment: $segment"
            fi
        done
    fi
done

echo "Cleanup completed. All datasources, segments, and ingestion tasks should have been deleted."
echo "Please check the Druid console to confirm all deletions were successful."