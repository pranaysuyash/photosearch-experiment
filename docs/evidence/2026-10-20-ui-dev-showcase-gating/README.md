# Evidence: dev-showcase route gating (2026-10-20)

Capture pair for the change in `ui/src/router/MainRouter.tsx` that wraps five
developer-showcase routes in `DevOnly` (production → NotFound).

| File | Build | Server | Route |
|---|---|---|---|
| `before-studio-code-splitting.png` | `git archive HEAD ui` built in `/tmp` (read-only) | `vite preview :4174` | `/studio/code-splitting` |
| `after-studio-code-splitting.png` | working tree | `vite preview :4173` | `/studio/code-splitting` |

Conditions: viewport 1280×820 CSS px; FastAPI backend running on :8000 with a
2,138-file library. Both previews are blocked by CORS (see addendum §6 in
`docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md`), so the "Backend is
offline" banner appears in both — it is an artifact of the web topology, not
of this change.

BEFORE: the Code Splitting demo renders in a production build.
AFTER: the 404 "Page not found" page renders; shell (mode rail, notch search,
actions) intact.

Caveat: BEFORE is the HEAD build, which excludes six unrelated uncommitted UI
edits present in the working tree (e.g. the `api.ts` host default — hence
`127.0.0.1` vs `localhost` in the banners).
