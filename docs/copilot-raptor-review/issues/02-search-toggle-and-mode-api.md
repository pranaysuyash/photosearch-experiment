# Issue: Search Toggle & `mode` API Parameter

## Description

Add a frontend toggle for `Metadata | Hybrid | Semantic`. Update server `GET /search` to accept `mode` as a query parameter and perform correct search path: metadata/semantic/hybrid.

## Why

Users must know which search approach they're using; semantic uses heavy compute and provides different results; metadata is fast and precise. Providing both modes improves UX and flexibility.

## Acceptance Criteria

- [ ] `ui` has a segmented toggle with `Metadata`, `Hybrid`, `Semantic` near the search input.
- [ ] `api.ts` adds `searchSemantic` and updates `search` to accept `mode` parameter or call `/search/semantic`.
- [ ] Backend `GET /search` supports `mode` param (default: `metadata`) and returns consistent JSON schema for results.
- [ ] UI placeholders provide mode-specific hints and example queries.

## UI Notes

- Place the toggle with `aria` labels and tooltips; default to `Metadata`.
- For `Hybrid` provide a small `weight` slider (optional; basic v1 can use 50/50).

## Backend Notes

- `mode` param can be optional; if `semantic` and model is not loaded, return an `503` or fallback to metadata with a notice.
- Add telemetry logs to track `mode` use across sessions (opt-in only).

## Estimate

2–3 days

## Labels

feature, frontend, api
