# Branch Dispositions

Canonical log of branch retirements per OPERATING_DOCTRINE.md §6 (semantic salvage
and supersession). One entry per retired branch: salvage check scope, outcome, and
provenance boundary.

## gemini/fix-face-scan — retired 2026-10-13

- Tip 43e7baa ("feat: face system updates and docs") — ancestor of master.
- Salvage check vs master: tree identical except 7 files, none salvageable.
  - 6 files missing here are metadata docs master gained in 84d76f0
    (COMPLETE_METADATA_CATALOG.md, METADATA_COMPLETE_EXHAUSTIVE.md,
    METADATA_COMPLETE_UNIVERSE.md, METADATA_ENHANCEMENT_PLAN.md,
    METADATA_GAPS_ANALYSIS.md, METADATA_ROADMAP_COMPLETE.md) — all present on
    master and descendants.
  - 1 file master deleted: server/photo_metadata.db-wal (stray SQLite WAL,
    correctly removed; *.db-wal now gitignored at .gitignore:35).
- Zero modified files, zero removed definitions. Nothing to salvage.
- Note: remote origin/gemini/fix-face-scan still exists, 1 commit behind this
  tip; remote-side deletion is a separate owner-approved action.

## refactor/main-split — retired 2026-10-13

- Tip f752212 ("refactor: split main into routers and services") — ancestor of master.
- Salvage check vs master at definition level (src/ + server/: zero removed
  functions/classes), UI API-surface level (all 7 master-deleted files were dead,
  broken-at-birth, or superseded), and docs level (nothing deleted).
- Full analysis and retirement boundary: docs/refactor-main-split.md (Disposition section).

## gemini/ux-polish-phase1 — retired 2026-10-13

- Tip 903d5c1 (2025-12-21, "feat: Gmail-style dropdown for Select button") —
  ancestor of master; oldest branch, pre-split.
- Salvage check vs master: 388 added / 270 modified / 7 deleted from branch
  perspective. The 7 deletions are the same set classified under
  refactor/main-split (photo_metadata.db-wal + 6 UI files: dead, broken-at-birth,
  or superseded). Definition-level sweep: zero removed functions/classes in
  src/ + server/, zero removed exported components in ui/src/, zero deleted docs.
- Nothing to salvage. UI polish content (Gmail-style dropdown et al.) merged
  into master via ancestry.

## Remote-branch cleanup — 2026-10-13 (owner-approved)

All stale remote branches deleted from origin after ancestry verification
(each an ancestor of origin/master, zero unique content):
- gemini/fix-face-scan (tip 43e7baa, content on origin/master)
- refactor/main-split, gemini/ux-polish-phase1, nervous-wright
Final topology: local master (in sync with origin/master) + local
feature/metadata-enhancement-2025 (fully merged, no upstream).
