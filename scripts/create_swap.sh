#!/usr/bin/env bash
# Compatibility wrapper; setup_swap.sh is the canonical implementation.
set -Eeuo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${SCRIPT_DIR}/setup_swap.sh" "$@"
