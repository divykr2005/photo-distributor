#!/usr/bin/env bash
set -e

# Size in megabytes (default 4096 = 4GB)
SWAP_SIZE=${1:-4096}
SWAP_FILE="/swapfile"

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (or use sudo)"
  exit 1
fi

if grep -q "swap" /proc/swaps; then
  echo "Swap is already active."
  cat /proc/swaps
  exit 0
fi

echo "Creating ${SWAP_SIZE}MB swap file at ${SWAP_FILE}..."
fallocate -l "${SWAP_SIZE}M" ${SWAP_FILE} || dd if=/dev/zero of=${SWAP_FILE} bs=1M count=${SWAP_SIZE}

chmod 600 ${SWAP_FILE}
mkswap ${SWAP_FILE}
swapon ${SWAP_FILE}

# Make it permanent
if ! grep -q "${SWAP_FILE}" /etc/fstab; then
  echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab
fi

echo "Swap configured successfully."
cat /proc/swaps
