# Tauri Mac-First Packaging & MPS Guidance

This document provides focused guidance for building a macOS-first Tauri app that uses local models and takes advantage of Apple MPS where possible.

Target: macOS first (M1/M2) with a later plan for Windows/Linux.

## Embedding Model & Device Considerations

- Apple MPS: Many ML frameworks now support Apple’s Metal Performance Shaders (MPS). If local models are used: make them compatible with MPS for better performance on Mac M1/M2.
- GPU detection: Use `settings.DEVICE` or an auto-detect routine on startup to choose `cpu`, `mps`, or `cuda`.
- Model packaging: If distributing with a local model, bundle a light/medium model and provide an option to download a larger optional model.

## Tauri Architectures & Sidecars

- Two options for the Python backend:
  1. Python Sidecar: Use Tauri’s sidecar architecture to run Python scripts and interact via Tauri’s `invoke` commands. Pros: small integration burden, works well offline.
  2. HTTP Local Server: Use FastAPI as a local server with secure CORS and local-only binding (127.0.0.1). Pros: easier dev & reuse; cons: port conflicts and more surface area.

Recommendation: Use the Python sidecar for production builds to minimize network exposure. For dev, continue with FastAPI for quick iteration.

## File Access & Permissions

- On first run, prompt for directory access and explain why it's needed.
- Use the macOS Security-Scoped Bookmarks to preserve access to user-selected directories across launches.
- For production: ensure the builder signs the app and declares the correct file-access usage messages in the `Info.plist`.

## Model Footprint & Bundling

- Keep default local models small (e.g., CLIP-lite or mobile-friendly variants) to keep the app lightweight.
- Offer a "Download recommended model" option on-demand to reduce initial download size.

## Memory & Resourcing

- MPS helps reduce CPU usage. For large datasets, do not embed all images at once — use batching.
- Keep embeddings on disk and load needed partitions when required.

## Background Workers & UI

- Indexing should be backgrounded (sidecar worker or system daemon). Provide a Job UI in Tauri with the ability to pause, cancel, and resume.

## OTA Updates & Data Safety

- Keep user data and model files under `Library/Application Support/PhotoSearch`.
- Provide a clear versioning strategy for models (e.g., `clip-v2.0`) so embeddings can be associated with versions for migration.

## Dev/QA Checklist for Mac Packaging

- [ ] Code-signed app with correct entitlements
- [ ] Packaging includes sidecar and embedded Python runtime
- [ ] Tests on M1 and M2 chips for memory and smaller model profiling
- [ ] Validate OS permission prompts and persistence behavior

## Business & UX Notes

- Make "local-first" default and highlight the "Download larger model" option that improves results for users willing to use more disk/CPU.
- Provide a mode to switch to cloud provider for compute-heavy features like batch reindexing.

End of Tauri Mac Guidance
