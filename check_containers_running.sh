#!/bin/bash

# Function to check if a container is running
is_container_running() {
    local container_name=$1
    local status=$(docker inspect -f '{{.State.Status}}' "$container_name" 2>/dev/null)
    
    if [ "$status" = "running" ]; then
        return 0  # Container is running
    else
        return 1  # Container is not running
    fi
}

# Check if arguments are provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <container1> <container2> ..."
    exit 1
fi

# Variable to track if all containers are running
all_running=true

# Check each container
for container in "$@"; do
    if is_container_running "$container"; then
        echo "✅ $container is running"
    else
        echo "❌ $container is not running"
        all_running=false
        
        # Show the last 20 lines of logs for non-running containers
        echo "Last 20 lines of logs for $container:"
        docker logs --tail 20 "$container"
        echo "----------------------------------------"
    fi
done

# Final status
if $all_running; then
    echo "✅ All containers are running."
    exit 0
else
    echo "❌ Not all containers are running."
    exit 1
fi