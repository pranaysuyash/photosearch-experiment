# Dev Workflow (Servers + UI)

This repo runs two dev servers:

- **Backend API**: FastAPI via `python server/main.py` (default `localhost:8000`)
- **Frontend UI**: Vite via `npm -C ui run dev` (default `localhost:5173`)

When iterating quickly, it’s easy to end up with stale `node`/`python` processes holding ports. The scripts below standardize “kill what’s running and restart cleanly”.

## One-command restart

From the repo root:

```bash
./start.sh
```

What it does:

- Stops anything currently **listening on ports** `5173` and `8000`
- Starts backend + frontend
- Writes PID files to `.run/backend.pid` and `.run/frontend.pid`
- Streams output to `server.log` and `frontend.log`

## Stop everything

```bash
bash stop.sh
```

Or directly:

```bash
bash scripts/dev-stop.sh --force
```

## Status / debugging

```bash
bash scripts/dev-status.sh
```

Shows:

- PID files (if present)
- Which process is listening on each port (uses `lsof`)

## Dry run

Print what would be stopped/started without killing anything:

```bash
bash scripts/dev-restart.sh --dry-run
bash scripts/dev-stop.sh --dry-run
```

## Configuration

Override defaults with env vars:

```bash
BACKEND_PORT=8001 FRONTEND_PORT=5174 bash scripts/dev-restart.sh
BACKEND_LOG=/tmp/backend.log FRONTEND_LOG=/tmp/frontend.log bash scripts/dev-restart.sh
```

## Virtualenv selection

Backend startup prefers an existing `.venv/` if it exists, otherwise it falls back to `venv/`:

- `.venv/` (preferred when present)
- `venv/` (fallback)

This keeps local dev aligned with the repo’s conventions while still working on a fresh machine.

## Pre-commit hooks

Local hooks call `scripts/precommit_python.sh` to pick a Python interpreter in this order:

- `.venv/bin/python` when it exists
- `venv/bin/python` when it exists
- `python3` or `python` from your PATH

This avoids hardcoding a single venv path so hooks keep working across machines.
