# Issue: Async Scan & Job API

## Description

Refactor `/scan` endpoint to support an async mode where `POST /scan?async=true` returns `202 Accepted` plus a `job_id`. Provide `GET /jobs/{job_id}` to track progress and status.

## Why

Synchronous scanning can block the server for long periods and cause timeouts on large libraries. A job API provides better UX and resilience.

## Acceptance Criteria

- [ ] `POST /scan?async=true` returns `202` and a `job_id` without blocking.
- [ ] `GET /jobs/{id}` returns job status: `queued`, `running`, `paused`, `completed`, `failed`, progress percent, and any `errors` or `files_processed` stats.
- [ ] UI adds a job tray showing active jobs, with controls to pause/cancel.
- [ ] Add a simple local job worker (start with `asyncio` or thread pool) to process jobs.

## Implementation Notes

- Use a simple in-memory job registry for v1; add persistence for jobs in DB for survivability later.
- Job payload includes `path`, `force`, and maybe granularity for batch size.
- Jobs must checkpoint progress to handle restarts.

## Estimate

3–5 days

## Labels

feature, backend, ui, infra
