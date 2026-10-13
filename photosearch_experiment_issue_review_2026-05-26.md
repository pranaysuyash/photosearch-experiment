# Photosearch Experiment Issue Review

Date: 2026-05-26

## Scope

This review captures the current local preservation state of the repository:

- local worktrees
- stash entries
- local branches not merged to the repository mainline
- remote branches not merged to the remote mainline
- current uncommitted work in the active worktree

## Mainline Note

There is no `main` ref in this repository right now.

The effective mainline is `master`:

- local mainline: `master`
- remote mainline: `origin/master`
- `origin/HEAD` also resolves to `origin/master`

All merge-state checks below are therefore against `master` / `origin/master`.

## Executive Summary

- The active worktree is dirty on `feature/metadata-enhancement-2025`.
- There are three additional local worktrees and all of them are clean.
- There are no stash entries.
- Only one local branch is not yet merged into `master`: `feature/metadata-enhancement-2025`.
- There are no remote branches not yet merged into `origin/master`.
- The active worktree contains both source-worthy changes and generated/runtime artifacts, so preservation should be handled carefully.

## Worktree Inventory

| Worktree | Branch | State | Notes |
|---|---|---:|---|
| `/Users/pranay/Projects/photosearch_experiment` | `feature/metadata-enhancement-2025` | Dirty | 14 tracked files modified and multiple untracked source/doc/runtime artifacts |
| `/Users/pranay/.claude-worktrees/photosearch_experiment/bold-buck` | `bold-buck` | Clean | Points at commit `42e8024` |
| `/Users/pranay/.claude-worktrees/photosearch_experiment/hungry-gauss` | `hungry-gauss` | Clean | Points at commit `42e8024` |
| `/Users/pranay/.claude-worktrees/photosearch_experiment/nervous-wright` | `nervous-wright` | Clean | Tracks `origin/nervous-wright` at commit `84d76f0` |

## Branch Inventory

### Local branches not merged into `master`

- `feature/metadata-enhancement-2025` at `1d3e97f`

This branch is ahead of `origin/master` by 1 commit and has no commits behind `origin/master`.

### Remote branches not merged into `origin/master`

- None detected

### Other branch observations

- `master` is present locally and tracks `origin/master`.
- `nervous-wright` is already merged into the `master` history.
- `bold-buck` and `hungry-gauss` are local-only branches that are already represented in the current history and do not appear as unmerged branches.
- `refactor/main-split` is present locally and is not currently listed as unmerged to `master`.

## Stash Inventory

- No stash entries were present.

## Active Worktree State

### Tracked files modified

These are the tracked paths currently modified in the active worktree:

- `.pre-commit-config.yaml`
- `photo_catalog.json`
- `requirements.txt`
- `server/api/routers/core.py`
- `server/api/routers/sources.py`
- `server/main.py`
- `src/metadata_extractor.py`
- `src/metadata_search.py`
- `src/photo_search.py`
- `src/video_analysis.py`
- `tests/test_server_config.py`
- `ui/src/api.ts`
- `ui/src/components/layout/Layout.tsx`
- `ui/src/services/BulkActionsService.ts`

### Untracked items likely to be source-worthy

These untracked paths look like durable project content and should be preserved, reviewed, or intentionally added:

- `.kiro/specs/metadata-completion/design.md`
- `.kiro/specs/metadata-completion/requirements.md`
- `.kiro/specs/metadata-completion/tasks.md`
- `SAST_REMEDIATION_20260312.md`
- `TASK_1_COMPLETION_SUMMARY.md`
- `motto_v2.md`
- `scripts/precommit_python.sh`
- `server/database/metadata_migration.py`
- `server/database/metadata_schema_v2.py`
- `server/metadata/metadata_mapper.py`
- `tests/test_metadata_schema_properties.py`
- `ui/.env.example`
- `ui/src/components/common/ApiStatusBanner.tsx`
- `ui/src/test/api-ping.test.ts`

### Untracked items likely to be generated/runtime artifacts

These look like local runtime or environment outputs rather than source:

- `.hypothesis/` with 15 files
- `requirements..venv.snapshot.txt`

## Preservation Assessment

### Low-risk / clean items

- `bold-buck`, `hungry-gauss`, and `nervous-wright` are present as clean sibling worktrees, so no work is currently stranded there.
- No stash entries means there is no hidden work waiting in stashes.
- No remote branches are waiting on merge into `origin/master`.

### Higher-risk items

- The active worktree is dirty and contains both implementation changes and new files.
- `motto_v2.md` is currently untracked even though it functions as repo-local instruction/context material.
- `.hypothesis/` and `requirements..venv.snapshot.txt` are generated artifacts that should be handled separately from source changes.

## Recommended Next Actions

1. Decide whether `feature/metadata-enhancement-2025` should remain the active integration branch or be snapshot-reviewed before any further edits.
2. Separate source-worthy untracked files from generated artifacts before any cleanup or commit planning.
3. Confirm whether `motto_v2.md` should be tracked as part of the repo-local instruction stack.
4. If desired, I can now produce a branch-by-branch preservation matrix with classification for each untracked path and tracked diff category.

## Evidence Summary

Commands used for this review:

- `git worktree list --porcelain`
- `git stash list`
- `git branch -vv`
- `git branch --all --no-merged master`
- `git branch -r --no-merged origin/master`
- `git log --oneline origin/master..HEAD`
- `git log --oneline HEAD..origin/master`
- `git status --short --untracked-files=all`
