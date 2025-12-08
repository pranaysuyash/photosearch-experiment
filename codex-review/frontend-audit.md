# Frontend UX/Code Audit – “Living Museum”

## Scope
- Reviewed the Vite/React/Tailwind UI (`ui/`) for UX, user flows, and implementation gaps.
- Read product context from `README.md` and backend APIs (`server/main.py`) to align findings.
- No builds/tests were run; assessment is code/UX review only.

## Highest-Risk Findings
- **Theme toggle can’t work**: Root container is hard-coded to `dark` (`ui/src/App.tsx:73`), while the command palette toggle edits `document.documentElement` (`ui/src/config/commands.ts:6-18`). Light mode will never appear and users get no feedback.
- **Command palette doesn’t open photos**: Selecting a photo only logs to the console (`ui/src/components/Spotlight.tsx:210-229`). There’s no integration with the main detail modal or grid state, so the “⌘K” affordance fails user expectations.
- **Search mode preference is siloed**: First-run modal doesn’t persist choice, and other surfaces ignore it. Spotlight and Hero Carousel always query metadata (`ui/src/components/Spotlight.tsx:15-18`, `ui/src/components/HeroCarousel.tsx:6-18`), while the main search uses the toggle (`ui/src/App.tsx:34-169`). Results differ across surfaces and revert to semantic on reload.
- **Onboarding is non-actionable**: Empty state in Story mode only shows text (`ui/src/components/StoryMode.tsx:57-67`), and FirstRunModal only sets search mode. The only scan trigger hides inside the command palette. New users with empty libraries have no obvious “scan library” CTA or path picker.
- **Redundant + inconsistent data fetches**: Hero Carousel calls `usePhotoSearch` separately (metadata mode) even though App already loads the photo set (`ui/src/components/HeroCarousel.tsx:6-20` vs `ui/src/App.tsx:34-169`). This doubles API calls and can show different images than the active search mode.

## User Flow & UX Audit
- **Search & browse**
  - Main search now debounces and feeds the grid, but there’s no filter/sort (date/type/location) or indicator of which mode is active beyond the toggle.
  - No visual cue for video items in `PhotoGrid` (all thumbnails treated as images, `ui/src/components/PhotoGrid.tsx:50-79`).
  - Fast typing can yield stale flashes because `usePhotoSearch` lacks request cancellation (`ui/src/hooks/usePhotoSearch.ts:17-45`).
- **Story mode**
  - Groups are random each render (shuffled arrays, `ui/src/components/StoryMode.tsx:28-44`), so the layout changes unpredictably when data refreshes instead of telling coherent “stories” (by date/location/people).
  - Empty state lacks a primary action to scan/import.
- **Photo detail**
  - Heavy metadata is great, but navigation buttons are absolutely positioned (`right-96` at `ui/src/components/PhotoDetail.tsx:121-127`) and risk falling off-screen on smaller widths. No “open in Finder/download/share” affordances.
- **Command palette**
  - Shows scan job status but offers no recent queries, saved searches, or quick filters. Results don’t open detail view (see high-risk).
- **Globe view**
  - No loading/empty state; entering Globe with zero photos shows an empty canvas (`ui/src/components/PhotoGlobe.tsx:201-277`).
  - Random GPS mocks (`generateMockGPS`, `ui/src/components/PhotoGlobe.tsx:18-42`) may mislead users; there’s no indicator of real vs. mocked locations.
  - Performance risk on low-end GPUs (Stars + 150 markers + DPR up to 2) without a “lite mode” toggle.
- **Timeline**
  - Purely decorative; bars aren’t clickable to filter the grid (`ui/src/components/SonicTimeline.tsx:23-61`) and aren’t keyboard-focusable.
- **Page metadata & brand**
  - `index.html` title is still “ui”; no meta description or sharing preview, so the app feels generic when bookmarked/shared.

## Technical UI Concerns
- **Theming architecture**: CSS variables are tied to `.dark` but the app forces dark at the component root; theme toggling should live on `html`/`body`.
- **State sharing**: Search mode and search results are not shared with Spotlight/Hero. Lacks a central context for search mode, results, and selection, leading to duplication and inconsistency.
- **Performance**: Masonry grid has no virtualization/pagination; large libraries will jank. Globe has no throttling or marker culling beyond a hard cap.
- **Accessibility**: Interactive divs lack keyboard handlers (PhotoGrid, StoryMode cards, timeline bars). Inputs have no labels/aria hints; command buttons need focus outlines.
- **Error/empty handling**: Globe and Hero have no loading fallback; grid error UI reloads the whole page instead of retrying the call.

## Recommendations (next steps)
1) Fix foundations: move theme control to document root and remove forced `dark`; persist search mode in localStorage and share it across App, Spotlight, and Hero via a context.  
2) Make command palette actionable: selecting a photo should open `PhotoDetail`; add saved/recent searches and mode indicator; expose “Scan library” with a path picker.  
3) Improve onboarding: add a prominent “Scan your photos” CTA in empty states with path input and a progress surface; let FirstRunModal optionally start a scan.  
4) Unify data fetching: reuse App-level photo data for Hero Carousel (or memoized slices) and respect active search mode; add cancellation in `usePhotoSearch`.  
5) Strengthen browse UX: deterministic groupings (by date/location), video badges in grid, filters/sorts, and timeline-click to filter by month.  
6) Add resilience/performance: globe loading/empty UI, “lite mode” toggle (disable stars/high DPR), virtualized grid or pagination for large libraries.  
7) Polish presentation: update `index.html` title/meta, fix navigation button positioning in detail view, add keyboard/focus states for grid and timeline.
