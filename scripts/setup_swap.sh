#!/bin/bash
# setup_swap.sh
# Allocates, formats, and enables a 4GB swap file on an Ubuntu/Debian host.

set -e

# Require root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

SWAP_FILE="/swapfile"
SWAP_SIZE="4G"

echo "Checking for existing swap..."
if swapon --show | grep -q "$SWAP_FILE"; then
  echo "Swap file $SWAP_FILE is already enabled."
  exit 0
fi

if [ -f "$SWAP_FILE" ]; then
  echo "Swap file $SWAP_FILE already exists but is not enabled. Enabling..."
  swapon "$SWAP_FILE"
else
  echo "Allocating $SWAP_SIZE swap file..."
  fallocate -l "$SWAP_SIZE" "$SWAP_FILE" || dd if=/dev/zero of="$SWAP_FILE" bs=1M count=4096
  
  echo "Setting correct permissions..."
  chmod 600 "$SWAP_FILE"
  
  echo "Formatting swap..."
  mkswap "$SWAP_FILE"
  
  echo "Enabling swap..."
  swapon "$SWAP_FILE"
fi

# Persist in fstab if not already present
if ! grep -q "$SWAP_FILE" /etc/fstab; then
  echo "Adding swap to /etc/fstab for persistence..."
  echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
fi

echo "Swap setup complete!"
swapon --show
free -h
