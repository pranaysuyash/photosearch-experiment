# Prioritized Feature Matrix — PhotoSearch

Prioritization is driven by user impact for a typical photo enthusiast (10k+ images) and privacy/local-first goals.

## Priority Legend

- Critical: Must-have before production/demos
- High: Important for usability and performance
- Medium: Value-added features that improve workflow
- Low: Nice-to-have features & experiments

> STATUS UPDATE (2025-12-13): Implementation progress
>
> - Core search, scanning, job queue, and saved searches are implemented in the backend.
> - Face clustering and many media analysis modules exist in `src/` but corresponding user-facing endpoints are not all wired in `server/main.py` yet.
> - AI Storytelling is prioritized and has a working frontend surface (`ui/src/components/StoryMode.tsx`), but the backend story-building and LLM narration stack remains a planned item.

## Critical (MVP)

- Secure image serving and path sandboxing (`server/main.py` `GET /image/thumbnail`).
- Non-blocking scan & indexing (background queue + job endpoints).
- Basic semantic search & metadata search toggles with clear UI affordance.
- Thumbnail cache & effective cache headers.
- Settings page to toggle privacy (local-only / cloud providers) + `.env.example`.

## High Impact

- Deduplication & clustering (visual similarity-based suggestions).
- Face detection & grouping (people clustering).
- Batch operations (select & export/tag/delete) with undo.
- Responsive UI virtualization for 10k+ images.
- Device selection and efficient embedding generation (MPS/GPU support).

## Medium Impact

- Export/Backup tools (export metadata & images with JSON/csv for compliance).
- Jobs & long-run status UI for large batch imports.
- Integration points for cloud storage (Google Drive/Dropbox).
- Upgradeable vector store adapters & migration tools (FAISS, Milvus, Lance).

## Low Impact / Future

- Smart albums and auto-tagging (AI derived).
- Live/continuous indexing via OS file events.
- Multi-user accounts & auth (only if moving to multi-user server deployment).
- Mobile companion app (sync/preview).

## Experimentation & Configuration

- Keep experimental features behind flags and a "lab" section.
- Add A/B test toggles to measure semantic vs metadata search impact.
- Provide feature usage telemetry (with privacy consent) for research & improvement.

## Metrics & KPIs

- Query latency (milliseconds 95th percentile).
- Indexing throughput (file/s).
- Memory usage & CPU/GPU utilization during indexing.
- Search relevancy (user rated) and top-N click-through.

## Next Steps

- Start implementation of critical MVP features; then iterate with high-impact features.
- Keep experiments simple & controlled with opt-in toggles and clean rollbacks.

End of Features Prioritization
