# UI Styling Notes (Responsiveness + Glass)

## Why styling regressions happened

The UI imports page/feature CSS files (example: `ui/src/modern-gallery.css`) from components. In a single-page app, once a route/component is visited, its CSS stays loaded, so any **global selector** (like `.btn-glass`) in a feature stylesheet can unintentionally override styles across the entire app.

## Glass button source of truth

All shared glass button styles live in:

- `ui/src/index.css` under `@layer components`

Conventions:

- Use `.btn-glass` for the base appearance.
- Use modifiers for variants: `.btn-glass--primary`, `.btn-glass--muted`, `.btn-glass--danger`.
- Don’t redefine `.btn-glass` in feature CSS files (it will leak across routes).

> STATUS UPDATE (2025-12-13): Global CSS leakage and inconsistent glass styling were addressed by scoping feature CSS to component roots and making studio/utility routes lazy-loaded. Relevant frontend files modified include several `ui/src/components/*` CSS files and `ui/src/router/MainRouter.tsx` to reduce style bleed and improve load-time. This fixes the primary regression where global selectors (e.g., `.header`, `.controls`) leaked into the main layout.

## Legacy button class support

Some older components still use button classes like:

- `.refresh-btn`, `.save-btn`, `.cancel-btn`, `.details-btn`, `.create-btn`, `.record-btn`, `.copy-btn`

These are styled alongside `.btn-glass` in `ui/src/index.css` so older UIs still match the newer glass system.

## Responsive action/toolbars

For sticky toolbars (selection bars, filters, etc.), prefer layouts that wrap on small screens:

- Use Tailwind `flex flex-wrap` + `w-full sm:w-auto` patterns.
- Keep “right aligned” controls using `sm:ml-auto`, but allow them to become full-width on mobile.

## Home page states

- **Empty / loading (no photos yet):** show a hero search with welcome copy.
- **Results present:** collapse to a compact sticky toolbar (search is the primary CTA) and keep the grid dense.

## Navigation + focus mode

- **Mode switching:** Grid/Globe/Story are treated as viewing modes and exposed via the top-left mode rail (`ui/src/components/ModeRail.tsx`). It collapses to the active mode icon and expands on hover/click.
- **Tasks:** Background work (scan/index/etc.) is tracked under “Tasks” (`/tasks`), backed by job IDs.
- **Focus mode:** Toggle focus mode (eye icon) to hide header/nav/timeline for pure browsing (`localStorage` key `lm:minimalMode`).

## Environment-reactive tint

The app has a subtle “ambient” tint that adapts to what you’re looking at (thumbnail hover + photo details):

- CSS variable: `--lm-accent-rgb` (default blue) in `ui/src/index.css`
- Controller: `ui/src/contexts/AmbientThemeContext.tsx`
- Color extraction: `ui/src/hooks/useAmbientTheme.ts` (averages a small downscaled image via canvas)

Usage:

- Grid sets a base tint from the first visible photo and overrides it on hover (`ui/src/components/ModernPhotoGrid.tsx`).
- Photo details override tint while the viewer is open (`ui/src/components/PhotoDetail.tsx`).
