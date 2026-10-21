# UI Audit Findings — 2026-10-20

**Audit date:** October 20, 2026
**Scope:** `ui/src` (React 19 + TypeScript + Vite 7 + Tailwind 3)
**Method:** Read-only static inspection; live dev servers verified during the audit.
**Related:** [`docs/AUDIT_FINDINGS.md`](./AUDIT_FINDINGS.md) (code-level audit, Dec 2025), [`docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md`](./UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md) (prior remediation exploration), [`docs/reviews/photosearch_ui_issue_review_2026-10-18.md`](./reviews/photosearch_ui_issue_review_2026-10-18.md).

This document is a **UI/UX inventory and hygiene report**. It does not repeat the code-audit findings in `docs/AUDIT_FINDINGS.md`; where the two overlap, this document cross-references and records whether the prior finding is still reproducible.

> **Status addendum — 2026-10-21.** This is a point-in-time audit; the remediation that followed it is recorded here so the report is not read as "still open".
>
> - **Provenance is no longer fabricated.** The fabricated `ProvenanceChips.tsx` was **deleted** and `ProvenanceChip.tsx` was **rewritten** to render a real, registry-derived attribution record, then mounted in the photo detail. The backend capability the old doc called missing now exists: `server/attribution.py` + `GET /attribution` + `GET /attribution/batch` + an `attribution` key on `/browse` and `/search` items. See [`docs/decisions/2026-10-21-photo-source-attribution.md`](./decisions/2026-10-21-photo-source-attribution.md).
> - **The live source filter was wrong and is now fixed.** `server/api/routers/search.py` classified `local|cloud|hybrid` by regex over the path, which mislabelled every synced cloud photo as local; it now derives the classification from the source registry. `/browse` accepted `source_filter` and silently ignored it — it now applies it.
> - **The three navigation components were deleted** (`SidebarNavigation`, `TopNavigation`, `MobileNavigation`); `OCRSearch.tsx` + `OCRSearch.css` remain the only unmounted pair awaiting a removal decision.
> - The `@deprecated` counts in §1–§2 are the audit-time snapshot, not the current tree.

---

## 1. Executive summary

The mounted application shell is coherent: `App.tsx` composes the provider chain and `MainRouter.tsx` maps a complete route set to pages. The debt is concentrated in **unmounted code that is still shipped in the bundle** and in a small number of **styling/behavior inconsistencies** in that code.

Verified headline numbers:

| Metric | Value |
| --- | --- |
| Components marked `@deprecated` | **6** |
| Total lines in those components | **1,167** |
| External importers of those components | **0** |
| Dead route targets referenced by them | **3** (`/gallery`, `/collections`, `/sources`) |
| Prior CRITICAL XSS finding still reproducible | **No** |

None of these are live rendering defects, because none of the six components are mounted. They are bundle weight, maintenance surface, and trap risk for the next contributor.

---

## 2. Deprecated component inventory

All six files carry an `@deprecated` tag on line 6 and cite `docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md §0` plus “Removal candidate after one release cycle”.

| File | Lines | Why it is deprecated |
| --- | --- | --- |
| `ui/src/components/navigation/SidebarNavigation.tsx` | 122 | Superseded by Layout's ActionsPod |
| `ui/src/components/navigation/TopNavigation.tsx` | 152 | Unmounted; superseded by Layout's header (ModeRail) |
| `ui/src/components/navigation/MobileNavigation.tsx` | 289 | Never integrated; arrived in a bulk feature commit |
| `ui/src/components/provenance/ProvenanceChip.tsx` | 103 | Only consumer is the deprecated `ProvenanceChips` |
| `ui/src/components/provenance/ProvenanceChips.tsx` | 235 | Unmounted and unusable as built: fabricates provenance |
| `ui/src/components/features/OCRSearch.tsx` | 266 | Superseded by `advanced/OCRTextSearchPanel` (mounted at `/analytics/ocr`) |
| **Total** | **1,167** | |

### 2.1 Importer verification

```
grep -rln "SidebarNavigation\|TopNavigation\|MobileNavigation\|ProvenanceChip\|ProvenanceChips\|OCRSearch" ui/src
```

returns **exactly the six files themselves** — no page, router, or layout imports any of them. A second sweep excluding the six paths returned no matches.

**Conclusion:** this is true dead code, not merely "deprecated but still reachable". Removal is a contained change: delete six files (plus `OCRSearch.css`), drop one stale `optimizeDeps` entry and one types-only dev dependency, then rebuild.

---

## 3. Dead route targets

The deprecated navigation components link to routes that do not exist in `MainRouter.tsx`:

| File:line | Target | Status |
| --- | --- | --- |
| `MobileNavigation.tsx:53` | `/gallery` | No route |
| `MobileNavigation.tsx:56` | `/collections` | No route |
| `SidebarNavigation.tsx:47` | `/sources` | No route |
| `TopNavigation.tsx:49` | `/sources` | No route |

Confirmed absent from the router: `/sources`, `/gallery`, `/collections`. The canonical gallery and collection surfaces are `/albums` and the search/home views; there is no separate sources page.

This matters less as a live bug (the components are unmounted) than as evidence that the files encode an abandoned information architecture. If any of them were ever re-mounted, those links would 404 into `NotFound`.

---

## 4. Fabricated-data risk in provenance components

`ProvenanceChips.tsx` does not fetch provenance; it derives it client-side from the photo path string:

- `loadProvenanceData` computes `isCloudPath` / `isNetworkPath` / `sourceType` from path text.
- Two ternaries are provably dead:
  - `status = sourceType === 'cloud' ? 'online' : 'online'`
  - `syncStatus = isCloudPath ? 'up_to_date' : 'up_to_date'`
- A `mockSource: SourceInfo` object hardcodes `name: 'Cloud Storage'`.
- A source comment states: “In a real implementation, this would fetch from the API / For now, derive from photo path”.

`ProvenanceChip.tsx` renders whatever `statusConfig[status]` and an optional `lastSync` date it is handed, with no verification of its own.

**Risk:** provenance is a trust surface. A component that synthesizes “online / up to date” from a file path is worse than no indicator, because it tells the user something the backend never asserted. Keeping it in the tree invites re-mounting. This is the strongest argument for deletion ahead of the general dead-code cleanup.

**Resolution (2026-10-21):** the risk was real and the fix was not deletion but *replacement with the real thing*. The registry already held the truth (`SourceStore` + `SourceItemStore.find_by_local_path`); it was never joined to the photo payloads. `server/attribution.py` now resolves attribution server-side (source item → registered local-folder root → app media root → honestly `unattributed`/`unknown`), `ProvenanceChips.tsx` was deleted, and `ProvenanceChip.tsx` was rewritten to render the returned record — including an explicit "Unattributed" state instead of a guess. Content provenance (C2PA) is separate and remains detection-only: `server/content_provenance.py` reports marker presence with `verified: false` and says so. See [`docs/decisions/2026-10-21-photo-source-attribution.md`](./decisions/2026-10-21-photo-source-attribution.md).

---

## 5. `OCRSearch.tsx` drift (superseded implementation)

The mounted OCR experience is `ui/src/components/advanced/OCRTextSearchPanel.tsx` at `/analytics/ocr`. The deprecated `OCRSearch.tsx` is a strict-subset predecessor that bypasses the canonical API client:

| Line | Observation |
| --- | --- |
| 41 | `fetch('/api/ocr/stats')` — raw fetch, no auth header, no base URL |
| 63 | `fetch(` — second raw call |
| 89 | `fetch('/api/ocr/extract', …)` |
| 126 | `fetch('/api/ocr/all', …)` |
| 124 | `window.confirm('Are you sure you want to clear all OCR data?')` |
| 171 | dynamic class `progress-fill score-fill-${…}` |
| 221 | `key={index}` |

Issues worth naming even for dead code, because they are the patterns a re-mount would reintroduce:

1. **API-client bypass.** `ui/src/api.ts` is the canonical axios client carrying auth and base URL. `OCRSearch` talks to the backend directly, so it would fail or misbehave outside the dev proxy.
2. **Native `confirm()`** for a destructive action, diverging from the app's dialog conventions.
3. **Dynamic Tailwind class construction** (`score-fill-${…}`) — Tailwind cannot see runtime-built class names, so these styles are at purge risk in production builds.
4. **`key={index}`** in a list that can reorder.
5. **Silent failures** — `console.error('Error fetching OCR stats:', err)` with no user-visible state.
6. Raw thumbnail URL `/api/image/thumbnail?path=...&size=200` with an `onError` fallback to `/placeholder-image.jpg`.

---

## 6. Styling-system inconsistency

Two design languages coexist in the navigation components:

- `MobileNavigation.tsx`, `ProvenanceChip.tsx`, `ProvenanceChips.tsx` use the shared `glass` tokens from `ui/src/components/design/glass.ts` (`glass.surface`, `glass.surfaceStrong`).
- `SidebarNavigation.tsx` and `TopNavigation.tsx` use plain Tailwind (`bg-white dark:bg-gray-800`, `border-gray-200 dark:border-gray-700`, `bg-blue-100 text-blue-800 …`) and never import `glass`.

They also hardcode product and identity strings: “PhotoSearch” in both navs, and a dummy avatar plus “User” / “Admin” in the `SidebarNavigation` footer.

Since these are all deprecated, the correct fix is deletion rather than restyling. Recorded here so the divergence is not mistaken for a live theming bug.

---

## 7. Behavioral inconsistency (for the record)

`MobileNavigation.tsx` has two ways to navigate: sidebar-overlay buttons call `onNavigate(item.path)` **and** `closeSidebar()`, while the bottom-bar buttons call only `onNavigate(item.path)`. If this component were restored, tapping the bottom bar would change route without dismissing the overlay.

By contrast, `TopNavigation.tsx`'s mobile panel does close on navigation (`onClick={() => setIsMenuOpen(false)}` on each link). The inconsistency is internal to `MobileNavigation`, not universal.

Again: unmounted, so no user impact today.

---

## 8. Build/config hygiene

- `ui/vite.config.ts:46` still lists `react-window` in `optimizeDeps.include`. There is **no runtime `react-window` dependency** in `ui/package.json` and no source importer; only `@types/react-window` (dev, types-only) remains at line 24. This entry is residue from a removed virtualized list.
- `ui/package.json:37` keeps `react-virtualized-auto-sizer` as a runtime dependency. It is not obviously wrong, but it pairs with the removed `react-window`; worth confirming it is still used before the next dependency prune.
- `.run/backend.pid` (91383) and `.run/frontend.pid` (91436) are stale — `scripts/dev-status.sh` reports them as not running while the real servers run under different PIDs. Cosmetic, but it makes `dev-status` misleading.

---

## 9. Prior findings re-check

### 9.1 CRITICAL XSS — not reproducible

`docs/AUDIT_FINDINGS.md` line 12 records a CRITICAL XSS via `dangerouslySetInnerHTML` at `ui/src/components/advanced/OCRTextSearchPanel.tsx:274`. Re-check:

```
grep -n "dangerouslySetInnerHTML" ui/src/components/advanced/OCRTextSearchPanel.tsx
```

returns **no matches** (exit 1). The vulnerable code block quoted in `AUDIT_FINDINGS.md` line 18 is no longer present in the file.

**Disposition:** treat as resolved/removed, not live. Recommend annotating the entry in `docs/AUDIT_FINDINGS.md` as “no longer present as of 2026-10-20” rather than leaving it as an open CRITICAL.

### 9.2 HIGH path traversal — carried forward, not re-verified

`docs/AUDIT_FINDINGS.md` line 23 records a path-traversal weakness in `/server/main.py:2845-2875` (note the doc's leading slash; the repo path is `server/main.py`). This audit did not re-verify it — it is a backend concern outside the UI scope. Cross-referenced only.

---

## 10. Recommended actions

Ordered by risk-to-effort, all optional and separate from this read-only audit:

1. **Delete the six deprecated components** and `OCRSearch.css`. Zero importers, 1,167 lines removed, no runtime behavior change. Do this before any refactor that might tempt a re-mount.
2. **Remove the stale `optimizeDeps` entry** (`react-window`) and re-check `react-virtualized-auto-sizer` usage.
3. **Annotate the XSS entry** in `docs/AUDIT_FINDINGS.md` as no longer reproducible.
4. **Fix `.run/*.pid` staleness** in `scripts/dev-status.sh` or stop relying on PID files where `lsof` already answers the question.
5. **Defer** any styling/behavior fixes to the deprecated navs — deletion supersedes them.

---

## 11. Non-goals and limitations

- This audit made **no code changes**. It is a findings document only.
- No runtime interaction testing was performed beyond confirming the dev servers respond (`5173`, `5174`, `8000` all HTTP 200).
- Bundle-size impact of the dead code was not measured; the 1,167-line figure is source lines, not shipped bytes.
- Accessibility was not re-audited in depth; the deprecated components' `aria-label`/`sr-only` text is noted but not scored.
- Backend behavior, contract drift in `tests/contracts/`, and non-UI concerns are out of scope.
