#!/usr/bin/env bash
set -euo pipefail

# Living Museum Startup Script (dev)
# Delegates to scripts/dev-restart.sh so restart behavior stays consistent.

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${ROOT_DIR}/scripts/dev-restart.sh"
