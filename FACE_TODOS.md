# Face System TODOs (Remaining Work)

## Requested Next Steps
- [ ] Implement a concrete hosted provider adapter (AWS/Azure/Google/Face++).
- [ ] Add backend/embedding compatibility gating + tests.
- [ ] Update README with the new fallback configs.

## Fallback Providers (Detection + Embeddings)
- [ ] Implement concrete adapters for at least one hosted provider (AWS/Azure/Google/Face++), mapping to the remote HTTP contract.
- [ ] Add embedding version compatibility gating (avoid mixing ArcFace + CLIP vectors in the same cluster).
- [ ] Add rate limiting + retry/backoff for remote providers.
- [ ] Add caching for remote embeddings to reduce API calls.
- [ ] Add health/status reporting for active detection + embedding backends.

## Testing & Validation
- [ ] Add tests for detection-only backends with embedding fallback (MediaPipe/YOLO + CLIP/Remote).
- [ ] Add tests for remote detection/embedding error paths (timeouts, malformed payloads).
- [ ] Run end-to-end UI workflows for face management with fallback backends enabled.
- [ ] Expand scale tests for 10K+ faces (performance + memory).

## UX & Observability
- [ ] Expose active backend + embedding source in People UI (diagnostics panel).
- [ ] Add user-facing warnings when clustering uses fallback embeddings (lower precision).
- [ ] Add telemetry for remote backend latency and failure rate.

## Documentation
- [ ] Update README with fallback env examples and a short provider comparison.
- [ ] Publish a provider selection guide (accuracy, cost, privacy).
