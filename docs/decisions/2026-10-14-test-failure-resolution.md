# Decision record: resolving the 17 known test failures — 2026-10-14

## Context

The full suite ran 418 passed / 17 failed for an extended period, with the failures
carried as "pre-existing." Per the operator's standing rule (blast radius is the
project — known issues get resolved, not deferred), every failure was driven to a
root cause and fixed in one pass.

## Changes

**Production fixes**
1. `server/clustering/faiss_face_clusterer.py` — `_find_similar_embeddings` guards
   `k <= 0` and the empty index before calling faiss (which asserts `k > 0`).
   Root cause: callers computing k dynamically could crash the search path.
2. `server/model_manager.py` — migration job IDs add a uuid suffix. Root cause:
   `migration_{int(time.time())}` collides for same-second migrations, breaking
   unique-ID expectations in the job store.
3. `server/privacy_controls.py` — `request_consent` validates its `consent_type`
   and raises `ValueError` for non-ConsentType input before any DB write. Root
   cause: a string slipped through to `consent_type.value` and surfaced as
   AttributeError. **Privacy note:** this is a validation tightening at the
   service boundary; consent records and their statuses are unchanged, and the
   router already maps ValueError to HTTP 400.

**Test migrations (intent-preserving; no skips, no weakened assertions)**
- `test_face_system_integration.py` was written against APIs that do not exist.
  Every call was moved to the real contracts read from the server modules
  (FAISSIndex `add_prototype`/`search`, VideoFaceTracker create-then-update
  consolidation, the analytics schema `face_clusters`/`face_detections`/
  `photo_person_associations`, `ModelManager(models_dir, face_db_path)`,
  `AdvancedFaceQualityAssessor`, the real privacy consent/export router for the
  features-integration file). The video processor is now exercised on a real
  synthesized video; quality assertions use distinct synthetic crops because
  random-noise crops score identically.
- `tests/test_features_integration.py`: the never-implemented
  `/privacy/control/{path}` endpoint was replaced with the shipped consent flow,
  including asserting the biometric-export-without-consent 403 gate.
- `pytest.ini`: `asyncio_mode = auto` (three test files use bare async tests;
  pytest-asyncio was missing from the rebuilt venv).

## Validation

Full suite: **435 passed / 0 failed** (was 418/17). Every fix has a
failing-before/passing-after run. All pre-commit hooks green.

## Falsifier

A future change that weakens any rewritten assertion, or a suite regression in
the touched modules, invalidates this record.
