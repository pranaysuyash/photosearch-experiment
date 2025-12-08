# Issue: Device Auto-Detection (MPS/CPU/CUDA) & Settings

## Description

Auto-detect the available compute device for the embedding model and expose it via config & settings. Provide a fallback order (mps -> cuda -> cpu) and expose a setting for the user to choose preferred device.

## Why

Performance tuning on macOS (M1/M2 MPS) and systems with GPUs improves indexing/search throughput and user experience.

## Acceptance Criteria

- [ ] `server/config.py` auto-detects device at startup using `torch.backends.mps.is_available()` and `torch.cuda.is_available()` (or equivalent for framework in use), defaulting to `cpu`.
- [ ] The embedding generator uses `settings.DEVICE` when constructing models and can switch at runtime or on restart.
- [ ] UI shows device info in settings and provides a `Test device` button to validate.

## Implementation Notes

- EmbeddingGenerators should validate device availability and log memory usage.
- For local-only mode, inform users about MPS/setup benefits, but do not force selection.

## Estimate

0.5–1 day

## Labels

feature, backend, config
