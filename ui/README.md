# UI (React + Vite)

The UI lives in `ui/` and talks to the FastAPI backend (default `http://127.0.0.1:8000`).

## Run (recommended)

From the repo root:

```bash
./start.sh
```

This cleanly restarts both backend (`8000`) and frontend (`5173`) and writes logs to `server.log` / `frontend.log`.

## Run UI only

```bash
npm -C ui run dev
```

If you run the UI alone, make sure the backend is running separately.

## Styling conventions

See:

- `docs/UI_STYLING.md`
