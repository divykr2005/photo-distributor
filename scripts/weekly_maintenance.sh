#!/bin/bash
# weekly_maintenance.sh
# Safely prunes unused Docker images, containers, and networks.
# Runs weekly via cron to prevent disk space exhaustion.

set -e

echo "Starting weekly Docker maintenance..."
echo "Current disk usage before prune:"
df -h /

echo "Pruning unused Docker resources..."
# -a removes all unused images not just dangling ones
# -f forces execution without prompt
# --volumes removes unused volumes (WARNING: only safe if all needed containers are running)
docker system prune -af --volumes

echo "Current disk usage after prune:"
df -h /

echo "Weekly maintenance complete."
