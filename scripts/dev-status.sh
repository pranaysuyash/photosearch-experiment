#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

show_port() {
  local port="$1"
  echo "Port ${port}:"
  if have_cmd lsof; then
    # shellcheck disable=SC2009
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN || true
  else
    echo "  (lsof not found)"
  fi
}

show_pidfile() {
  local name="$1"
  local file="${RUN_DIR}/${name}.pid"
  if [[ -f "${file}" ]]; then
    local pid
    pid="$(cat "${file}" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      echo "${name}.pid: ${pid} (running)"
      ps -p "${pid}" -o pid,ppid,command= || true
    else
      echo "${name}.pid: ${pid:-<empty>} (not running)"
    fi
  else
    echo "${name}.pid: (missing)"
  fi
}

echo "== Living Museum dev status =="
echo "Repo: ${ROOT_DIR}"
echo ""
show_pidfile "backend"
show_pidfile "frontend"
echo ""
show_port "${BACKEND_PORT}"
echo ""
show_port "${FRONTEND_PORT}"

