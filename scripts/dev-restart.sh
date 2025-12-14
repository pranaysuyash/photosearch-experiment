#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_LOG="${BACKEND_LOG:-${ROOT_DIR}/server.log}"
FRONTEND_LOG="${FRONTEND_LOG:-${ROOT_DIR}/frontend.log}"

DRY_RUN=0
FORCE=1
VENV_DIR=""

usage() {
  cat <<'EOF'
Usage: scripts/dev-restart.sh [--dry-run] [--no-force]

Stops anything currently listening on the backend/frontend dev ports, then
restarts both servers and writes PID files to .run/.

Defaults:
  backend:  python server/main.py  (port 8000)
  frontend: npm -C ui run dev      (port 5173)

Env:
  BACKEND_PORT, FRONTEND_PORT
  BACKEND_LOG, FRONTEND_LOG
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --no-force) FORCE=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

have_cmd() { command -v "$1" >/dev/null 2>&1; }

pick_venv() {
  if [[ -d "${ROOT_DIR}/.venv" ]]; then
    VENV_DIR="${ROOT_DIR}/.venv"
    return 0
  fi
  VENV_DIR="${ROOT_DIR}/venv"
}

run_cmd() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf 'DRY:'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

kill_tree() {
  local pid="$1"
  local sig="${2:-TERM}"
  [[ -n "${pid}" ]] || return 0
  kill -0 "${pid}" 2>/dev/null || return 0

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

wait_port_free() {
  local port="$1"
  local i
  for ((i=0; i<80; i++)); do
    if have_cmd lsof; then
      if ! lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
        return 0
      fi
    else
      return 0
    fi
    sleep 0.1
  done
  return 1
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
    echo "Stopping pid ${pid} on port ${port}..."
    kill_tree "${pid}" TERM
    if [[ "${FORCE}" == "1" ]]; then
      sleep 0.3
      kill_tree "${pid}" KILL
    fi
  done < <(pids_listening_on_port "${port}")
}

wait_backend_ready() {
  local url="http://127.0.0.1:${BACKEND_PORT}/"
  local i
  for ((i=0; i<60; i++)); do
    if have_cmd curl; then
      if curl -fsS "${url}" >/dev/null 2>&1; then return 0; fi
    else
      # Fallback: just wait a bit if curl isn't present.
      sleep 0.5
      return 0
    fi
    sleep 0.25
  done
  return 1
}

mkdir -p "${RUN_DIR}"
pick_venv

echo "== Living Museum dev restart =="
echo "Repo: ${ROOT_DIR}"
echo "Backend port: ${BACKEND_PORT}  Frontend port: ${FRONTEND_PORT}"
echo "Python venv: ${VENV_DIR}"
echo ""

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "DRY RUN: would stop anything listening on ${FRONTEND_PORT} and ${BACKEND_PORT}, then start:"
  echo "  backend:  python server/main.py  >> ${BACKEND_LOG}"
  echo "  frontend: npm -C ui run dev      >> ${FRONTEND_LOG}"
  echo ""
  if have_cmd lsof; then
    echo "Currently listening:"
    lsof -nP -iTCP:"${BACKEND_PORT}" -sTCP:LISTEN || true
    lsof -nP -iTCP:"${FRONTEND_PORT}" -sTCP:LISTEN || true
  fi
  exit 0
fi

echo "Stopping existing servers (by port)..."
stop_port "${FRONTEND_PORT}"
stop_port "${BACKEND_PORT}"

if ! wait_port_free "${FRONTEND_PORT}"; then
  echo "Warning: port ${FRONTEND_PORT} still busy." >&2
fi
if ! wait_port_free "${BACKEND_PORT}"; then
  echo "Warning: port ${BACKEND_PORT} still busy." >&2
fi

echo ""
echo "Starting backend..."
if [[ "${DRY_RUN}" == "0" ]]; then
  if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  : > "${BACKEND_LOG}"
  (cd "${ROOT_DIR}" && exec python server/main.py) >> "${BACKEND_LOG}" 2>&1 &
  BACKEND_PID=$!
  echo "${BACKEND_PID}" > "${RUN_DIR}/backend.pid"
  echo "✓ Backend started (pid ${BACKEND_PID})"
else
  run_cmd bash -lc "cd \"${ROOT_DIR}\" && python server/main.py >> \"${BACKEND_LOG}\" 2>&1 & echo \$! > \"${RUN_DIR}/backend.pid\""
fi

if [[ "${DRY_RUN}" == "0" ]]; then
  if ! wait_backend_ready; then
    echo "Warning: backend did not respond on http://127.0.0.1:${BACKEND_PORT}/ (check ${BACKEND_LOG})" >&2
  fi
fi

echo ""
echo "Starting frontend..."
if [[ "${DRY_RUN}" == "0" ]]; then
  : > "${FRONTEND_LOG}"
  (cd "${ROOT_DIR}/ui" && exec npm run dev) >> "${FRONTEND_LOG}" 2>&1 &
  FRONTEND_PID=$!
  echo "${FRONTEND_PID}" > "${RUN_DIR}/frontend.pid"
  echo "✓ Frontend started (pid ${FRONTEND_PID})"
else
  run_cmd bash -lc "cd \"${ROOT_DIR}/ui\" && npm run dev >> \"${FRONTEND_LOG}\" 2>&1 & echo \$! > \"${RUN_DIR}/frontend.pid\""
fi

echo ""
echo "URLs:"
echo "  Backend:  http://localhost:${BACKEND_PORT}"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo ""
echo "Logs:"
echo "  Backend:  tail -f ${BACKEND_LOG}"
echo "  Frontend: tail -f ${FRONTEND_LOG}"
echo ""
echo "Stop:"
echo "  bash scripts/dev-stop.sh"
echo "  bash stop.sh"
