#!/usr/bin/env bash
# Idempotently provision a persistent swap file on Ubuntu/Debian.

set -Eeuo pipefail

SWAP_FILE="${SWAP_FILE:-/swapfile}"
SWAP_SIZE_MIB="${1:-4096}"
SWAPPINESS="${SWAPPINESS:-10}"
SYSCTL_FILE="/etc/sysctl.d/99-photo-distr-swap.conf"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script as root: sudo $0 [size-in-MiB]" >&2
  exit 1
fi

if ! [[ "${SWAP_SIZE_MIB}" =~ ^[0-9]+$ ]] || (( SWAP_SIZE_MIB < 512 )); then
  echo "Swap size must be an integer of at least 512 MiB." >&2
  exit 1
fi

ensure_persistence() {
  if ! grep -Eq "^[[:space:]]*${SWAP_FILE//\//\\/}[[:space:]]+none[[:space:]]+swap[[:space:]]" /etc/fstab; then
    printf '%s none swap sw 0 0\n' "${SWAP_FILE}" >> /etc/fstab
  fi
  printf 'vm.swappiness=%s\n' "${SWAPPINESS}" > "${SYSCTL_FILE}"
  sysctl -q "vm.swappiness=${SWAPPINESS}"
}

swap_is_active() {
  awk 'NR > 1 {print $1}' /proc/swaps | grep -Fxq "${SWAP_FILE}"
}

if swap_is_active; then
  ensure_persistence
  echo "${SWAP_FILE} is already active; persistence and swappiness were verified."
  swapon --show
  free -h
  exit 0
fi

required_kib=$((SWAP_SIZE_MIB * 1024 + 1024 * 1024))
available_kib=$(df --output=avail -k "$(dirname "${SWAP_FILE}")" | tail -n 1 | tr -d ' ')
if (( available_kib < required_kib )); then
  echo "Insufficient disk space: ${SWAP_SIZE_MIB} MiB swap plus 1 GiB headroom is required." >&2
  exit 1
fi

created=false
cleanup() {
  if [[ "${created}" == true ]] && ! swap_is_active; then
    rm -f -- "${SWAP_FILE}"
  fi
}
trap cleanup ERR

if [[ -e "${SWAP_FILE}" ]]; then
  if ! file -b "${SWAP_FILE}" | grep -qi 'swap file'; then
    echo "Refusing to overwrite existing non-swap file: ${SWAP_FILE}" >&2
    exit 1
  fi
else
  echo "Allocating ${SWAP_SIZE_MIB} MiB at ${SWAP_FILE}..."
  if ! fallocate -l "${SWAP_SIZE_MIB}M" "${SWAP_FILE}"; then
    dd if=/dev/zero of="${SWAP_FILE}" bs=1M count="${SWAP_SIZE_MIB}" status=progress
  fi
  created=true
  chmod 600 "${SWAP_FILE}"
  mkswap "${SWAP_FILE}"
fi

chmod 600 "${SWAP_FILE}"
swapon "${SWAP_FILE}"
ensure_persistence
trap - ERR

echo "Swap configured successfully."
swapon --show
free -h
sysctl vm.swappiness
