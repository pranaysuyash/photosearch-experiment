# UI & UX Assessment — PhotoSearch

Date: 2025-12-08

## Overview

This document evaluates the current React UI, interaction patterns, accessibility, and performance characteristics. It also suggests improvements for user flows, privacy, and features consistent with the repository's design principles and the Tauri local/client strategy.

## Files Used

- `ui/src/components/PhotoGrid.tsx`
- `ui/src/hooks/usePhotoSearch.ts`
- `ui/src/api.ts`
- `ui/src/App.tsx` (exists)
- `ui/` project (tailwind, framer-motion, react masonry)

## High-level Observations

- The UI is modern, responsive, and uses a visual-heavy pattern appropriate to photo applications.
- The masonry grid layout, lazy loading, hover overlays, and animation via Framer Motion provide a polished and dynamic appearance.
- Key hooks/API usage (`usePhotoSearch` and `api.ts`) decouple UI and backend, allowing easy replacement of search providers.
- There are switchable modes (metadata/semantic) which is a clear UX affordance — excellent for progressive enhancement.

## Strengths

- Clear modular component architecture for PhotoGrid, PhotoDetail, Timeline, etc.
- Reasonable placeholder/tailwind skeleton design for loading states.
- API wrapper abstracts the backend for the UI, making it easier to support alternate endpoints.

> STATUS UPDATE (2025-12-13): Some UI regressions previously noted (global CSS leakage and misplaced components) were fixed by scoping CSS to component root selectors and lazy-loading non-core routes. The layout and glass design have been restored for most screens; see `ui/src/components/Layout.css`, `ui/src/components/StoryMode.tsx`, and `ui/src/router/MainRouter.tsx`.

## Opportunities & Recommendations

1. Image Serving & Security (Critical)

- PhotoGrid uses `api.getImageUrl(photo.path)` which encodes the path and queries the backend. Ensure backend strictly validates encoded paths and restricts access to `MEDIA_DIR` to prevent path traversal.
- Consider introducing a signed, ephemeral URL mechanism or token for fetching images in the Desktop app to avoid exposing absolute paths in the URL.

2. Query UX (Search Box)

- The `usePhotoSearch` hook supports an initialQuery & manual search. Consider enhancing auto-complete, type-ahead suggestions, query parsing hints and mapping natural language to metadata filters in the UI.
- Provide an explicit toggle for semantic vs. metadata search, with tooltips explaining each’s strengths.

3. Search Results Ranking & Feedback

- Provide an in-UI feedback mechanism to flag results as relevant/irrelevant for model retraining or to improve ranking heuristics.
- Show confidence/similarity score by default in semantic mode, and a small explanation of how the score should be interpreted.

4. Photo Detail & Metadata UX

- Create a single-photo detail view that shows:
  - Big image preview (with zoom/panning)
  - Full metadata folded into sections (Filesystem, EXIF, GPS, Likely Tags)
  - Version history (metadata_history)
  - Actions (open in external app, copy, export, delete, mark as favorite)
- Provide a minimal read-only experience with a toggle to reveal raw JSON metadata for power users.

5. Timeline & Browsing

- The timeline endpoint returns monthly data. Add a UI control to select a month/year and apply that as a filter to the grid.
- Consider heat-map or density visualizations (aggregated by day/time) to find patterns (e.g., travel days).

6. Accessibility & Keyboard Navigation

- Ensure `alt` attributes are set on images using either `photo.filename` or AI generated captions.
- Add keyboard focus/selection support (e.g. arrow keys to move between images, space to select, enter to open detail).
- Verify color contrast for the overlay and text.

7. Pagination & Virtualization

- For large datasets (10k+ images), implement virtualization (react-window) or progressive loading via pagination or infinite scroll with a cursor.
- Ensure the UI does not attempt to render more items than needed to avoid memory pressure.

8. Multi-select & Batch Actions

- Add selection mechanic (ctrl/cmd + click) and a floating toolbar to perform batch operations (export, tag, delete, favorite).
- Implement optimistic updates and undo to minimize accidental deletes.

9. Settings & Privacy Controls

- Add a settings panel where users can choose:
  - Local vs. cloud inference (if cloud-enabled)
  - AI provider selection & credentials
  - Thumbnail size/quality default
  - Where indexes/embeddings are persisted on disk
- For Tauri/Desktop: ensure the UI prompts the user for directory access and explains why access scope is required.

10. UX for Experimental Features

- Place experimental features behind a toggle flag in the UI.
- Provide a feedback CTA for experiments (e.g., "Try experimental accelerator — help us evaluate.")

## UI Patterns & Flow Recommendations

- Primary search input at top header with clear toggles for metadata/semantic.
- Left or top filter bar with common facets: date, camera, format, location, favorites, size.
- Grid in the center with infinite scroll, masonry layout, and skeleton placeholders.
- Right-side drawer or modal for photo details and actions.

## Testing & Metrics

- UI unit tests: component tests for PhotoGrid, PhotoDetail, and hook tests for `usePhotoSearch`.
- Integration tests: search flows; scan (mocked) → index → semantic search flow.
- Performance tracking: measure time-to-first-cell; search results render time; average request times.

## Accessibility

- Ensure ARIA roles for interactive elements.
- Provide keyboard navigation; use the `tabindex` where appropriate.
- Ensure all variants (semantic vs metadata) are reachable via keyboard and screen-readers.

## Tauri-specific Considerations

- Tauri allows tight OS file permissions. Respect user consent when requesting folder access.
- Use Tauri's secure privilege APIs for local file access rather than a localhost server, if you aim for higher security.
- For bundling Python, choose between a simple sidecar or the Tauri `Command` API; make sure to use signed/secure channels for communicating between the UI and Python.

## Design Handoff (Optional)

- Provide a `components.json` (exists) design tokens and shared components library to achieve visual consistency.
- Consider a design system or Figma for collaboration; export tokens to Tailwind theming for consistency.

## Next Steps (UI Implementation)

1. Add path-sandboxing review and testing for image URLs.
2. Implement the semantic/metadata toggle with tooltips explaining which type of search to use.

Security / Image Serving: The UI now supports signed/ephemeral image URLs via `api.getSignedImageUrl()` and includes a `ServerConfigPanel` (Settings → Sync & Security) that shows whether signed URLs are enabled on the server and allows developers to provide an issuer API key or Bearer JWT for testing token issuance. 3. Add an initial settings page to manage privacy & AI provider choices. 4. Add support for pagination/virtualization for large datasets. 5. Implement the photo detail modal with metadata & version history. 6. Add selection & batch operations.

End of UI Assessment
