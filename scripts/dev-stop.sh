#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

DRY_RUN=0
FORCE=0

usage() {
  cat <<'EOF'
Usage: scripts/dev-stop.sh [--force] [--dry-run]

Stops the dev backend (port 8000) and frontend (port 5173) by:
1) PID files in .run/{backend,frontend}.pid (if present), then
2) Anything listening on those ports.

Env:
  BACKEND_PORT   default 8000
  FRONTEND_PORT  default 5173
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

have_cmd() { command -v "$1" >/dev/null 2>&1; }

kill_tree() {
  local pid="$1"
  local sig="${2:-TERM}"
  if [[ -z "${pid}" ]]; then return 0; fi
  if ! kill -0 "${pid}" 2>/dev/null; then return 0; fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "DRY: kill -${sig} ${pid}"
    return 0
  fi

  kill "-${sig}" "${pid}" 2>/dev/null || true

  if have_cmd pgrep; then
    local child
    while read -r child; do
      [[ -n "${child}" ]] || continue
      kill_tree "${child}" "${sig}"
    done < <(pgrep -P "${pid}" 2>/dev/null || true)
  fi
}

wait_dead() {
  local pid="$1"
  local seconds="${2:-5}"
  local i
  for ((i=0; i<seconds*10; i++)); do
    if ! kill -0 "${pid}" 2>/dev/null; then return 0; fi
    sleep 0.1
  done
  return 1
}

stop_pidfile() {
  local name="$1"
  local file="${RUN_DIR}/${name}.pid"
  [[ -f "${file}" ]] || return 0
  local pid
  pid="$(cat "${file}" || true)"
  [[ -n "${pid}" ]] || return 0

  if kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping ${name} (pid ${pid})..."
    if [[ "${DRY_RUN}" == "0" ]]; then
      kill_tree "${pid}" TERM
      if ! wait_dead "${pid}" 6; then
        if [[ "${FORCE}" == "1" ]]; then
          echo "Force killing ${name} (pid ${pid})..."
          kill_tree "${pid}" KILL
        else
          echo "Still running: ${name} (pid ${pid}); rerun with --force to SIGKILL" >&2
        fi
      fi
    else
      echo "DRY: would stop pid ${pid} from ${file}"
    fi
  fi
}

pids_listening_on_port() {
  local port="$1"
  if have_cmd lsof; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true
  else
    echo ""
  fi
}

stop_port() {
  local port="$1"
  local pid
  while read -r pid; do
    [[ -n "${pid}" ]] || continue
    echo "Stopping process listening on ${port} (pid ${pid})..."
    if [[ "${DRY_RUN}" == "0" ]]; then
      kill_tree "${pid}" TERM
      if ! wait_dead "${pid}" 6; then
        if [[ "${FORCE}" == "1" ]]; then
          echo "Force killing pid ${pid} on port ${port}..."
          kill_tree "${pid}" KILL
        else
          echo "Still running pid ${pid} on port ${port}; rerun with --force to SIGKILL" >&2
        fi
      fi
    else
      echo "DRY: would stop pid ${pid} listening on ${port}"
    fi
  done < <(pids_listening_on_port "${port}")
}

mkdir -p "${RUN_DIR}"

stop_pidfile "frontend"
stop_pidfile "backend"

stop_port "${FRONTEND_PORT}"
stop_port "${BACKEND_PORT}"

if [[ "${DRY_RUN}" == "0" ]]; then
  rm -f "${RUN_DIR}/backend.pid" "${RUN_DIR}/frontend.pid" 2>/dev/null || true
fi

echo "Done."
