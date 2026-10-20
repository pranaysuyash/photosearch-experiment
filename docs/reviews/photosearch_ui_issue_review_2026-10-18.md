# PhotoSearch UI — Web Design Guidelines Audit (Issue Review)

- **Date:** 2026-10-18
- **Skill applied:** `web-design-guidelines` (Vercel Web Interface Guidelines, fetched fresh at audit time)
- **Why not `macos-app-design`:** the app is packaged with Tauri, but 100% of the UI surface is web tech (React 19 + Vite + Tailwind rendered in a webview). `macos-app-design` targets native SwiftUI/AppKit code, which does not exist in this repo. All native-shell checks (menu bar, windows, etc.) are out of scope; the auditable surface is the web UI.
- **Scope:** `ui/src/**` (156 `.tsx` components/pages/contexts + all `.css` + `index.html`) — every file read in full, no sampling.
- **State audited:** working tree at 2026-10-18 (master @ 390755d + staged security-fix changes; `ui/` itself unmodified).
- **Verification:** 12 high-impact claims re-checked by hand against source after the sweep; **all 12 confirmed** (listed in Appendix B).

---

## 1. Executive summary

**~600 guideline violations across ~125 of the ~170 audited files.** No XSS vectors found (zero `dangerouslySetInnerHTML`). The frontend build/tests are green, but the audit surfaced issues in three trust-critical classes that the test suite cannot see:

1. **Destructive actions without confirmation or undo** — deleting duplicate files, merging people, removing tags/faces, revoking privacy access, and "anonymize" all execute immediately.
2. **Simulated data presented as real** — at least 6 surfaces (Import progress, OCR extraction progress, Analytics, Provenance chips, AI Insights, Export progress) fabricate results client-side.
3. **A misleading undo promise** — the bulk-delete confirm dialog says "This action can be undone"; the undo handler is a `console.log` placeholder, and the API call goes out with `confirm: false`.

Severity distribution (findings, approximate):

| Tier | Definition | Count |
|---|---|---|
| P0 | Data loss, fake data shown as real, a11y blockers, functional bugs | ~70 |
| P1 | Modal/focus failures, unvirtualized grids, perf hazards | ~120 |
| P2 | Motion (`transition-all` ×98), interaction, keyboard-reveal gaps | ~180 |
| P3 | Copy ("…" ×60+), `tabular-nums`, dark-theme form controls, dead controls | ~230 |

---

## 2. P0 — Critical

### 2.1 Destructive actions without confirm/undo

| Location | Action taken immediately |
|---|---|
| `src/pages/Duplicates.tsx:466` | "Keep First, discard rest" deletes remaining files in group |
| `src/pages/Duplicates.tsx:478` | "Delete all (manual cleanup)" deletes every file in group |
| `src/components/people/MergeSuggestions.tsx:274` | Merge two people/clusters (`api.mergeClusters`) |
| `src/components/people/PeopleChips.tsx:86` | Strip person from photo |
| `src/components/people/ReviewQueue.tsx:205,218` | "Confirm All" / "Reject All" batch-mutate N faces (undo is single-shot) |
| `src/components/gallery/GestureActions.tsx:46` | Swipe-left fires `onAction('delete')` at threshold |
| `src/components/gallery/PhotoGrid.tsx:541` | Bulk "Unfavorite" (bulk *delete* does confirm at :187) |
| `src/components/gallery/PhotoFacePanel.tsx:88` | "Hide person" (`api.hideCluster`) |
| `src/components/gallery/tabs/EditTab.tsx:149` | "Reset All" discards all edits |
| `src/components/gallery/InlineEditMode.tsx:90,213` | Cancel/Reset discard unsaved edits |
| `src/components/notes/NotesEditor.tsx:101` | Delete note (buttons :163, :241) |
| `src/components/privacy/PrivacyControls.tsx:352,382` | Revoke user access / remove group member |
| `src/components/privacy/PrivacyDashboard.tsx:513` | Permanent anonymize — warning text but no typed confirmation |
| `src/components/features/JobMonitor.tsx:169` | "Clear" bulk-deletes recent jobs |
| `src/pages/PerformanceDashboard.tsx:198` + `src/components/performance/PerformanceDashboard.tsx:380` | "Clear Cache" |
| `src/components/advanced/OCRTextSearchPanel.tsx:1125` | "Clear OCR Cache" — destructive **and has no onClick** (silent no-op) |

Good practice already present (use as the template): `PhotoDetail` trash/unlink and `PhotoGrid` bulk delete use `window.confirm`; `Trash.tsx` empty-trash/bulk-delete confirm.

### 2.2 Misleading destructive affordance (worst single finding)

- `src/components/bulk/BulkActions.tsx:382` — dialog promises **"This action can be undone."**
- `src/components/bulk/BulkActions.tsx:153` — undo handler: `console.log('Undo delete – restore from trash:', …)` — a no-op placeholder.
- `src/components/bulk/BulkActions.tsx:69` — calls `api.deletePhotos(selectedPhotos)` without `confirm: true`.
- `src/api.ts:1264` — `deletePhotos(paths, confirm = false)` defaults to **unconfirmed** mode; no caller passes `true`.

### 2.3 Simulated / mocked data presented as real

| Location | What is fake |
|---|---|
| `src/components/import/ImportWizard.tsx:83` | Import progress + stats are a `setTimeout` loop (`scanned: i*12`, `imported: i*8`) |
| `src/components/features/OCRSearch.tsx:100` | OCR "extraction" progress ticks to 100% regardless of backend state |
| `src/components/export/ExportDialog.tsx:137` | Export progress bar is simulated |
| `src/components/advanced/AnalyticsDashboard.tsx:668,790-803,933-1013` | Hardcoded "New York — 1,234 photos", "+12%", mock charts |
| `src/components/ai/AIInsights.tsx:81` | "Patterns" tab renders hardcoded mock analysis |
| `src/components/provenance/ProvenanceChips.tsx:64` | Provenance always fabricated client-side |

Also trust-adjacent: `src/components/collaboration/CollaborativeSpaces.tsx:106` — API path hardcodes `user-placeholder-id`, so the list can never return real data.

### 2.4 Accessibility blockers

- `index.html:11` — `maximum-scale=1.0, user-scalable=no` blocks pinch-zoom (WCAG 1.4.4).
- `src/components/layout/DynamicNotchSearch.tsx:228-241` — the **primary search trigger** is a `motion.div` with onClick: no role, no tabIndex, no keyboard handler. Keyboard/screen-reader users cannot open search from the notch.
- `src/components/layout/ActionsPod.tsx:117-121` and `src/components/layout/ModeRail.tsx:75-78` — collapsed nav items are hidden with `max-w-0 opacity-0 overflow-hidden` but **stay in tab order** → keyboard users tab through ~15 invisible links.
- `src/components/actions/ContextMenu.tsx:310,125` — context menu has no `role="menu"`/`menuitem`, focus never moves into it, no arrow-key nav; "Open With" submenu opens on hover only.
- `src/components/accessibility/AccessibilityPanel.tsx:33` — `JSON.parse(localStorage…)` without try/catch in a `useState` initializer → corrupted value **crashes the accessibility panel**.
- `src/components/search/SearchToggle.tsx:13`, `src/components/advanced/AnalyticsDashboard.tsx:466`, `src/components/gallery/tabs/PhotoDetailTabs.tsx:32`, `src/components/ai/AIInsights.tsx:188`, `src/components/features/TauriIntegration.tsx:149` — tab/toggle groups convey selection by color only (no `role="tablist"`/`aria-selected`/`aria-pressed`).
- `src/components/rating/StarRating.tsx:69` — rating not conveyed to AT (no slider/radiogroup semantics); save failure silently swallowed (:54).
- `src/components/navigation/TopNavigation.tsx:100` — `aria-expanded="false"` hardcoded, never updates.
- Async results are **never announced anywhere**: zero `aria-live`/`role="status"`/`role="alert"` in the entire codebase (toasts, search counts, errors, offline banner, job progress — all silent to AT). Representative: `src/components/toast/ToastProvider.tsx:33`, `src/components/common/ApiStatusBanner.tsx:17`, `src/components/common/ErrorDisplay.tsx:98`.

### 2.5 Functional bugs (real-world breakage)

- `src/utils/safeAreaStyles.ts:13-26` — `ptSafe/prSafe/pbSafe/plSafe` all emit **all-sides** padding (`p-[…]` instead of `pt-`/`pr-`/…); `pSafe` applies the *top* inset to every side via four conflicting `p-[max()]` classes. Same for margins. Every directional safe-area utility is wrong.
- `src/components/gallery/PhotoGrid.tsx:606` — `Math.floor(Math.random() * 2) + 2` row-span computed **during render** → layout re-randomizes on every re-render (CLS + impure render).
- `src/components/video/VideoFacesPanel.tsx:78` — `btoa(videoPath)` executed in render → **throws on non-Latin-1 paths**.
- `src/components/privacy/PrivacyControls.tsx:114` — encryption key "hashed" with `btoa` (comment admits: "In a real app, use proper hashing").
- `src/components/editing/PhotoEditor.tsx:669` — crop presets write `window.cropRatio` but the crop math never reads it → ratio never enforced.
- `src/components/tags/AddToTagDialog.tsx:57` — new tag created via API **before** empty-selection validation → orphan tag created on failed submit.
- `src/components/timeline/StoryCreator.tsx:485` — `onBlur` cancels caption editing before the Save button's click can fire → clicking Save swallows the save.
- `src/components/editing/MobilePhotoEditor.tsx:401` and `src/components/people/PersonAnalytics.tsx:56` — save/load failures only `console.error`, zero user feedback.
- `src/components/layout/Layout.tsx:190-191` — `animate-pulse-slow` is not defined in `tailwind.config.js` (only `scroll-text` exists) → intended background pulse silently does nothing. Also `Layout.tsx:56,298-345`: `statusOpen` initialized `false` and only ever set `false` — the "Library status" popover is unreachable dead UI, including a "Scan a folder…" button whose handler was commented out.
- Dead controls shipped as active-looking UI: `AnalyticsDashboard.tsx:447,1053` (Export + optimization buttons, no onClick), `OCRTextSearchPanel.tsx:701,1121` (View Image, Export Settings), `AIInsights.tsx:309,439-474` ("More options" + 4 dead CTAs), `PlaceClustering.tsx:59` (View → `console.log`), `Duplicates.tsx:403` (icon button, no onClick).
- `src/components/navigation/MobileNavigation.tsx:47-61` — 7 nav targets (`/gallery`, `/collections`, `/places`, `/capture`, `/notes`, `/export`, `/share`) have **no route** in `MainRouter`; stale hardcoded `badge: 12` on Favorites (:49). `SidebarNavigation.tsx:43` — `/sources` also unrouted.
- `src/components/common/FirstRunModal.tsx:98-105` — "Connect a Source" uses `window.location.assign` (full page reload, bypasses router, never marks first-run seen).
- `src/hooks/usePhotoSearch.ts:111,124` — double initial search on mount.
- `src/components/video/VideoAnalysisPanel.tsx:174`, `VideoFacesPanel.tsx:127` — polling timers/`setTimeout` chains not cleaned up on unmount.
- `src/pages/Search.tsx` and `src/pages/Home.tsx` — clean.

---

## 3. P1 — High

### 3.1 Modal/overlay behavior (systemic: ~22 custom dialogs, all broken the same way)

**Pattern:** custom portal modals close on backdrop click and X, but have **no Escape handling, no focus trap, focus never moves into the dialog**. (Radix is a dependency but only `cmdk` uses it.)

`src/components/gallery/PhotoDetail.tsx:1002,1266` · `src/components/gallery/PhotoFacePanel.tsx:372` · `src/components/gallery/ResponsiveGallery.tsx:311` · `src/components/people/BooleanPeopleSearch.tsx:210` · `src/components/people/FaceAttributeSearch.tsx:286` · `src/components/people/MoveFaceModal.tsx:164` · `src/components/people/SplitClusterModal.tsx:181` · `src/components/people/SimilarFaceSearch.tsx:70` · `src/pages/People.tsx:1967,2020` · `src/pages/PersonDetail.tsx:1070,1120,1187` · `src/pages/UnassignedFaces.tsx:278` · `src/pages/UnidentifiedFaces.tsx:209` · `src/components/advanced/AdvancedFaceSearch.tsx:422` (path: `src/components/search/`) · `src/components/search/NaturalLanguageFaceSearch.tsx:168` · `src/components/search/MatchExplanation.tsx:205` · `src/components/common/FirstRunModal.tsx:36` · `src/components/albums/AddToAlbumDialog.tsx:94` · `src/components/albums/CreateAlbumDialog.tsx:83` · `src/components/collaboration/CollaborativeSpaces.tsx:314,401,590,652` · `src/components/collections/SmartCollections.tsx:276,367` · `src/components/export/ExportDialog.tsx:201` · `src/components/import/ImportWizard.tsx:415` (backdrop closes even **mid-import**) · `src/components/privacy/PrivacyDashboard.tsx:433,482` · `src/components/video/VideoAnalysisPanel.tsx:702` · `src/components/timeline/StoryCreator.tsx:128` · `src/components/sources/ConnectSourceModal.tsx:178` · `src/components/tags/AddToTagDialog.tsx:84` · `src/components/bulk/BulkActions.tsx:368` (confirm overlay isn't a dialog; background stays interactive)

Special cases: `src/components/search/Spotlight.tsx:206` — shows an "ESC" badge but Escape doesn't close (only ⌘K toggles); `src/components/search/CommandPalette.tsx:79` — Tab escapes the palette to the background; `src/components/features/PhotoGlobe.tsx:1486`, `src/components/search/SearchModeHelp.tsx:31`, `src/components/gallery/PhotoGrid.tsx:446`, `src/components/albums/AlbumDetail.tsx:188`, `src/components/versions/VersionStackViewer.tsx:331` — popovers/menus without Escape or outside-click dismissal.

**One fix kills ~30 findings:** a shared `useDialogAccessibility` (Escape, focus trap, initial focus, restore focus, `role="dialog"`/`aria-modal`) adopted by all custom modals.

### 3.2 Unvirtualized large lists (>50 items)

`react-window` was removed from deps; `react-virtualized-auto-sizer` is present but unused for these.

`src/components/gallery/PhotoGrid.tsx:604` (masonry, unbounded via infinite scroll) · `src/components/gallery/ResponsiveGallery.tsx:251,277` · `src/pages/People.tsx:1731` · `src/pages/PersonDetail.tsx:930` · `src/pages/Duplicates.tsx:363` (fetch limit 200) · `src/pages/Trash.tsx:135` · `src/pages/AllFacePhotos.tsx:103` · `src/pages/Singletons.tsx:79` · `src/pages/LowConfidence.tsx:86` · `src/pages/UnidentifiedFaces.tsx:182` (100) · `src/components/people/MoveFaceModal.tsx:267` · `src/components/people/SplitClusterModal.tsx:251` · `src/components/search/Spotlight.tsx:340` · `src/components/advanced/OCRTextSearchPanel.tsx:643` (100) · `src/components/features/OCRSearch.tsx:213` · `src/components/features/FaceClustering.tsx:233,355` · `src/components/features/StoryMode.tsx:87` (infinitely growing + per-item stagger) · `src/pages/PerformanceDashboard.tsx:279` · `src/components/versions/VersionStack.tsx:156` · `src/components/versions/VersionStackViewer.tsx:246` · `src/contexts/PhotoSearchContext.tsx:372,513` (accumulates all pages — unbounded DOM)

### 3.3 Performance hazards

- `src/components/gallery/SecureLazyImage.tsx:42` — `getServerConfig()` fetched **per image instance** (N photos = N config requests); `PhotoGrid.tsx:636` — signed-URL fetch per hovered item, no debounce/cancel; `PhotoGlobe.tsx:1383` same per hover.
- `src/components/search/IntentRecognition.tsx:110` / `IntentBasedSearch.tsx:84` — up to 3 intent fetches **per keystroke**, no debounce, unstable callback deps.
- `src/components/features/PhotoGlobe.tsx:1200` — 500ms `setInterval` + `getComputedStyle` poll for accent color though a `prefChange` event is already wired; `:962` — up to 220 per-frame `useFrame` lookAt callbacks; `:1152` — rotation uses fixed increment, not delta-time (speed scales with refresh rate).
- `src/components/gallery/LivePreviewCanvas.tsx:137` — full-res `getImageData`/`putImageData` loop synchronously on every slider change.
- `src/components/editing/MobilePhotoEditor.tsx:410` — controls defined as inner components → full remount every render; `:266` — haptic fires on every pan frame.
- `src/components/command palette`/`CommandPalette.tsx:59` — keydown listener re-bound every render (unstable deps).
- Images: only 4 `loading="lazy"` in the codebase; missing on below-fold grids in `Singletons.tsx:88`, `LowConfidence.tsx:93`, `UnidentifiedFaces.tsx:193`, `UnassignedFaces.tsx:252`, `CollaborativeSpaces.tsx:510`, `StoryCreator.tsx:247`, `VersionStack.tsx:121,167`, `VersionStackViewer.tsx:187,258`, `PhotoEditor.tsx:512`. `LazyImage.tsx:75` — no intrinsic sizing when `aspectRatio` omitted (CLS); `:78` — error state renders the loading spinner forever.

---

## 4. P2 — Motion, interaction, focus

### 4.1 `transition-all` — 98 occurrences (spec: never; animate transform/opacity only)

`src/index.css:159` (the **global `.btn-glass`** used by every button in the app) · `src/enhanced-animations.css:102,210,309` · `src/components/ModalSystem.css:33,96,167,311` (+ `src/components/common/ModalSystem.css` same file duplicated) · `src/components/layout/Layout.css:65,192` · `src/components/gallery/modern-gallery.css:158,169,199,293,428,468` · `src/components/features/{CodeSplitting,OCRSearch,FaceClustering,TauriIntegration,IntentRecognition}.css` (multiple each) · TSX: `DynamicNotchSearch.tsx:271,327,379,436` · `EnhancedSearchUI.tsx` ×12 · `ActionsPod.tsx:118` · `ModeRail.tsx:76` (+ `src/components/ModeRail.tsx:69`) · `SidebarNavigation.tsx:59` (animating sidebar **width**) · `FirstRunModal.tsx:63,79` · `ui/Toast.tsx:51` (+ `toast/Toast.tsx:83`) · `PhotoDetail.tsx:1073` · `PhotoDetailTabs.tsx:35` · `PersonDetail.tsx:942,983` · `Events.tsx:221` · `SonicTimeline.tsx:274` · `AIAnalysis.tsx:282` · `InlineEditMode.tsx:107` · `ModernGalleryDemo.tsx` · `AdvancedFaceSearch.tsx` · `AnalyticsDashboard.tsx:472` · `OCRTextSearchPanel.tsx:510,527` · `PerformanceDashboard.tsx:133,151,169` (page + component) · `StarRating.tsx:81` · `ActionButton.tsx:119` · `OpenWithSubmenu.tsx:161` · `AddToAlbumDialog.tsx:154` · `CreateAlbumDialog.tsx:130,148` · `ExportDialog.tsx:431` · `ImportWizard.tsx:362` · `VideoAnalysisPanel.tsx:433,477,721,731,741` · `VideoHighlights.tsx:237` · `StoryCreator.tsx` · `SplitClusterModal.tsx:256` · `AlbumCard.tsx:19` · `MobilePhotoEditor.tsx:428` · `PhotoEditor.tsx:520` (animates `filter` — paint-heavy) · `PersonAnalytics.tsx:194,233` (bar **width**, duration-1000) · `Events.tsx:194,233`

### 4.2 Reduced motion — almost entirely ignored

`MotionConfig reducedMotion="user"` is absent app-wide (`src/App.tsx:13` imports framer-motion globally). Guards exist in only 3 files: `App.css`, `enhanced-animations.css`, `modern-gallery.css` — and even those are incomplete (`modern-gallery.css:546` guard misses `.gallery-skeleton:568` and `.path-auto-scroll:613`).

Unguarded significant motion: `LoadingSpinner.tsx:25` · `HeroCarousel.tsx:30` (infinite 5s auto-rotation, no pause control; `:41` slide content never announced) · `ModernGalleryDemo.tsx:215,276,331,393,433` · `StoryMode.tsx:64,171` · `SonicTimeline.tsx:159` · `enhanced-animations.css:225,263,275,345` (infinite keyframes) · `Layout.css:247-269` · `IntentRecognition.css:122` · `ErrorDisplay.tsx:157` (height 0→auto) · `Layout.tsx:351` (page transitions) · `DynamicNotchSearch.tsx:174-192,292-312` (animates width/height/margin/padding) · `PhotoGlobe.tsx:1151` (three.js auto-rotation + Stars) · `AIAnalysis.tsx` width bars · `VideoHighlights`/`AIInsights` spin/pulse.

Also invalid CSS: `enhanced-animations.css:7-8` — malformed `--gallery-scroll-timeline` declaration.

### 4.3 Keyboard-invisible interactive elements (hover/opacity reveals + click-only divs)

Hover-only controls with no `focus-visible` reveal (invisible to keyboard users): `PhotoGrid.tsx:703` · `PhotoFacePanel.tsx:242` · `StoryMode.tsx:100` · `PhotoDetail.tsx` · `Gallery` hover overlays generally.

Click-only `div`s without role/tabIndex/keyboard: `People.tsx:1053-1150` (5 stat cards, two silently no-op at count 0) · `PersonDetail.tsx:938` · `Duplicates.tsx:369` · `AllFacePhotos.tsx:104` · `Singletons.tsx:81` · `UnidentifiedFaces.tsx:184` · `Import.tsx:100` · `MoveFaceModal.tsx:268` (acts as radio) · `SplitClusterModal.tsx:254` · `InteractiveFaceTagging.tsx:223` · `Events.tsx:219` · `LocationCorrection.tsx:543` · `PlaceClustering.tsx:110` · `CollaborativeSpaces.tsx:728` · `NotesEditor.tsx:140` · `VideoAnalysisPanel.tsx:430,475,598` · `AIAnalysis.tsx:96` · `PhotoRelationshipGraph.tsx:274` · `SonicTimeline.tsx:232` · `ContextualHoverZones.tsx:128` (six invisible click-only zones) · `ResponsiveGallery.tsx:253,278` · `StoryMode.tsx:89` · `FaceClustering.tsx:235` (has tabIndex but no role).

Gesture-only with no alternative: `GestureActions.tsx:163` (swipe = only affordance; `:171` no `select-none` during drag) · `SmartSelectionCanvas.tsx:257` (mouse-only) · `MobilePhotoEditor.tsx:465` · `SonicTimeline.tsx:243`.

Focus removal without replacement (`outline-none` / `outline: none`, 24+): `DynamicNotchSearch.tsx:209` · `EnhancedSearchUI.tsx:235,718` · `CommandPalette.tsx:104` · `Spotlight.tsx:253` · `InteractiveFaceTagging.tsx:313,362` · `ConnectSourceModal.tsx:250,284,292,301,310,318,327,335,363,371,382` · `Pages/Duplicates.tsx:312` · `People.tsx:1174` · CSS: `index.css:182`, `ModalSystem.css:150`, `OCRSearch.css:140`, `CodeSplitting.css:203` (+ `CodeSplitting.css:95` — checkbox `opacity:0` with no slider `:focus-visible` → toggle has no visible focus) · `PhotoEditor.tsx:793,842,891` (range inputs `opacity-0`).

### 4.4 Icon-only buttons relying on `title` only (no `aria-label`) — ~60 instances

Full lists live inline in the audit log; heaviest clusters: `People.tsx:1836-1943` (6 row actions) · `PersonDetail.tsx:598,641,655,757` · `ReviewQueue.tsx:187,256,302,311,320,232` · `Trash.tsx:186` · `AllFacePhotos.tsx:67` / `Singletons.tsx:47` (back buttons, no title either) · `DynamicNotchSearch.tsx:213,265` · `PhotoDetail.tsx:662,680,1294` · `EditTab.tsx:140,148,155` · `InlineEditMode.tsx:123,193-236` · `SmartSelectionCanvas.tsx:244-309` · `PhotoRelationshipGraph.tsx:196,231` · `BooleanPeopleSearch.tsx:228,274,303` · `MergeSuggestions.tsx:153` · `ReviewInbox.tsx:160` · `UnassignedFaces.tsx:184` · `InteractiveFaceTagging.tsx:256,315` · `ModalSystem.tsx:350` · `ui/Toast.tsx:57` · `AdvancedFaceSearch.tsx:440,495` · `NaturalLanguageFaceSearch.tsx:185` · `IntentBasedSearch.tsx:196,208` · `SavedSearchList.tsx:156,166,173` · `OCRTextSearchPanel.tsx:568,672` · `MobilePhotoEditor.tsx:697,708,781,801` · `ExportDialog.tsx:525,556` · `BulkActions.tsx:259,308,443,527` · `CollaborativeSpaces.tsx:321,415,597,659,780` · `SmartCollections.tsx:283,380,446` · `PrivacyControls.tsx:505` · `PrivacyDashboard` · `VideoAnalysisPanel.tsx:752,768` · `VideoHighlights.tsx:191` · `MultiTagFilter.tsx:234,397,434` · `LocationCorrection.tsx:243` · `FavoritesToggle.tsx:15` (also no `aria-pressed`) · `ActionButton.tsx:129` (systemic: when `showLabel=false`, no accessible name) · `VersionStackViewer.tsx:282` · `SimilarFaceSearch.tsx:88` · `MoveFaceModal.tsx:182` · `SplitClusterModal.tsx:199` · `FaceAttributeSearch.tsx:304`.

Also: `FavoritesToggle.tsx:15`, `ServerConfigPanel.tsx:109`, `AnalyticsDashboard.tsx:434`, `OCRTextSearchPanel.tsx:622`, `PersonDetail.tsx:598` — stateful toggles missing `aria-pressed`.

### 4.5 Unlabeled form controls — ~70 instances (pattern)

Labels present but not associated (no `htmlFor`/`id`) or placeholder-only inputs. Heaviest: `ConnectSourceModal.tsx` (11 inputs), `AdvancedFaceSearch.tsx` (19 controls), `FaceAttributeSearch.tsx` (10), `CollaborativeSpaces.tsx` (8), `OCRTextSearchPanel.tsx` (6 + 3 fake settings inputs at `:822,1084,1097,1110`), `PrivacyControls.tsx:326,448`, `LocationCorrection.tsx:258-335`, `People.tsx:1169,1264,1333,1385,1981`, `PersonDetail.tsx:1080,1131`, `ModalSystem.tsx:292-326`, `VideoAnalysisPanel.tsx:289,508,568`, `NotesEditor.tsx:222`, `BulkActions.tsx:296,322,344`, `StoryCreator.tsx:177-193`, `ServerConfigPanel.tsx:125,143`, `SmartCollections.tsx:294-338`, `MultiTagFilter.tsx:246-332`, `FaceClustering.tsx:310`, `Events.tsx:166,181`, `PeopleChips.tsx:149`, `MoveFaceModal.tsx:251,324`, `SplitClusterModal.tsx:240`, `UnidentifiedFaces.tsx:236`, `UnassignedFaces.tsx:314,330`, `BooleanPeopleSearch.tsx:256,325`, `SimilarFaceSearch.tsx:105`, `AddToTagDialog.tsx:122`, `PrivacyPanel.tsx:71`, `VideoHighlights.tsx:205`, `IntentBasedSearch.tsx:276-306`, `Search.tsx` inputs in `EnhancedSearchUI.tsx:233,537,716,982`, `CommandPalette.tsx:97`, `PhotoFacePanel.tsx:400`, `EditTab.tsx:200,208`, `InlineEditMode.tsx:146,161,176`, `MobilePhotoEditor.tsx:679`, `NaturalLanguageFaceSearch.tsx:201`, `Spotlight.tsx` ok.

Search inputs should be `type="search"`: `DynamicNotchSearch.tsx:203`, `EnhancedSearchUI.tsx:233,716`, `AdvancedFaceSearch.tsx:488`, `IntentBasedSearch.tsx:184`, `NaturalLanguageFaceSearch.tsx:205`, `OCRTextSearchPanel.tsx:557`, `OCRSearch.tsx:191`. Missing `autocomplete`: `CollaborativeSpaces.tsx:608` (email), `PrivacyControls.tsx:326` (email), personal-name fields throughout People/Move/Split modals; missing `spellCheck={false}` on paths/keys: `CollaborativeSpaces.tsx:670`, `BulkActions.tsx:326,348`, `ConnectSourceModal.tsx:324,368`, `People.tsx:1333`. `ConnectSourceModal.tsx:289` — S3 endpoint should be `type="url"`.

### 4.6 Hover states

Missing hover feedback: `MobileNavigation.tsx:241-266` (bottom-bar buttons), plus most click-only divs by definition. `ActionButton.tsx:159` — tooltip on hover only, never focus.

---

## 5. P3 — Polish

### 5.1 Copy: ASCII `...` instead of `…` (~60 strings) + "..." truncation

Everywhere: `DynamicNotchSearch.tsx:208` · `ModalSystem.tsx:216,201,299,310,325` · `PhotoGrid.tsx:510,558,770,788` · `PhotoDetail.tsx:981,982` · `EditTab.tsx:171` · `AIAnalysis.tsx:124` · `LivePreviewCanvas.tsx:177` · `People.tsx:462,845,884,1171,1665,1702,1985,2012,2056` · `PersonDetail.tsx:911,1087,1214` · `Duplicates.tsx:188,309,333` · `MergeSuggestions.tsx:112` · `ReviewQueue.tsx:155` · `AllFacePhotos.tsx:88` · `UnidentifiedFaces.tsx:163,240` · `BooleanPeopleSearch.tsx:462,327` · `FaceAttributeSearch.tsx:716` · `InteractiveFaceTagging.tsx:204,382,310` · `PeopleChips.tsx:182,151` · `MoveFaceModal.tsx:356,253,326` · `SplitClusterModal.tsx:219,337,244` · `Events.tsx:118` · `AdvancedFaceSearch.tsx:936` · `CommandPalette.tsx:98` · `EnhancedSearchUI.tsx:333,351,810,828` · `IntentBasedSearch.tsx:192,293,329` · `IntentRecognition.tsx:159` · `MatchExplanation.tsx:308` · `NaturalLanguageFaceSearch.tsx:345` · `Spotlight.tsx:103,130,252` · `PerformanceDashboard.tsx:202,246,254,267` (page + `:223,266` component) · `AnalyticsDashboard.tsx:460` · `OCRTextSearchPanel.tsx:300,866` · `CodeSplitting.tsx:188` · `FaceClustering.tsx:181,198` · `OCRSearch.tsx:153,195,203` · `PhotoGlobe.tsx:1349` · `StoryMode.tsx:52,157` · `TauriIntegration.tsx:130` · `MobilePhotoEditor.tsx:582,740` · `PhotoEditor.tsx:926` · `AlbumDetail.tsx:99` · `AlbumGrid.tsx:42` · `CreateAlbumDialog.tsx:145` · `AddToAlbumDialog.tsx:224` · `PlaceClustering.tsx:72` · `NotesEditor.tsx:133,226` · `BulkActions.tsx:300` · `PrivacyControls.tsx:183` · `PrivacyDashboard.tsx:242,474` · `VideoAnalysisPanel.tsx:309,572` · `VideoFacesPanel.tsx:164,205` · `VideoHighlights.tsx:140` · `StoryCreator.tsx:289,196,512` · `ContextMenu.tsx:335` · `VersionStack.tsx:73` · `ProvenanceChips.tsx:123` · `FirstRunModal` (`...your request...`).

### 5.2 `tabular-nums` — 1 occurrence in the whole app

Every stat row, count badge, and dashboard KPI animates widths as digits change: `People.tsx:1043-1150` · `PersonDetail.tsx:588,774-792` · `Duplicates.tsx:217-289` · `MergeSuggestions.tsx:212,229,259` · `ReviewQueue.tsx:196,288` · `UnidentifiedFaces.tsx:147` · `UnassignedFaces.tsx:177` · `PersonAnalytics.tsx:110-161` · `ReviewInbox.tsx:206` · `ModalSystem.tsx:238-246` · `PhotoDetail.tsx:750` · `PhotoFacePanel.tsx:410,430` · `EnhancedSearchUI.tsx:344,822` · `AnalyticsDashboard.tsx:500-1011` · `PerformanceDashboard.tsx:209-425` (both) · `FaceClustering.tsx:210-348` · `OCRSearch.tsx:176` · `SmartCollections.tsx:392` · `ImportWizard.tsx:367` · `VideoAnalysisPanel.tsx:393-693` · `ModernGalleryDemo.tsx:405` · `ExportDialog` progress.

### 5.3 Dark-theme / theming

No `color-scheme: dark` on `<html>` despite `class="dark"` (native selects/scrollbars render light). Hardcoded light palettes clashing with the dark glass UI: `ModalSystem.css` (whole file), `CodeSplitting.css`, `FaceClustering.css`, `OCRSearch.css`, `TauriIntegration.css`, `PerformanceDashboard.tsx:274-458` (component), `PrivacyDashboard.tsx:282-483`, `Events.tsx:154`, `VideoHighlights.tsx:136`. Native `<select>` without explicit colors in dark UI: `SortControls.tsx:23`, `ModalSystem.css:138-145`, `IntentBasedSearch.tsx:280-300`. `theme-color` meta is present ✓.

### 5.4 Navigation & state

Search/filter/tab/page state is never reflected in the URL anywhere — refresh/back/share lose everything. Core cases: `PhotoSearchContext.tsx:68-82` (query, mode, sort, filters, dates) · `People.tsx:143-144` · `Duplicates.tsx:49-50` · `PersonDetail.tsx:196` · `ResponsiveGallery.tsx:41` · `ReviewQueue.tsx:44` · `UnassignedFaces.tsx:62`. `MainRouter.tsx:84-160` — no scroll reset on route change. `TopNavigation.tsx:110-139` — mobile menu stays open after navigating. `SavedSearchList.tsx:51` — running a saved search doesn't deep-link.

### 5.5 Dead / inconsistent UI

`Layout.tsx` status popover (dead, §2.5) · `MobileNavigation`/`SidebarNavigation` unrouted targets (§2.5) · `App.css` not imported anywhere (dead file) · `ErrorBoundary` ✓ clean · `NotFound.tsx:13-16` renders "404" as divs — no heading · `FirstRunModal` full-reload nav (§2.5).

---

## 6. Clean files (read in full, no findings)

`src/main.tsx` · `src/pages/Search.tsx` · `src/pages/Home.tsx` · `src/pages/About.tsx` · `src/pages/Albums.tsx` · `src/pages/Favorites.tsx` · `src/pages/GlobePage.tsx` · `src/pages/SavedSearches.tsx` · `src/pages/Settings.tsx` · `src/pages/StoryModePage.tsx` · `src/pages/Videos.tsx` · `src/components/layout/NotchBar.tsx` · `src/components/layout/PageSearchWrapper.tsx` · `src/components/common/ErrorBoundary.tsx` · `src/components/gallery/{FavoritesFilter,MediaTypeFilter,MetadataSection,ZoomControls}.tsx` · `src/components/gallery/tabs/{DetailsTab,InfoTab}.tsx` · `src/components/toast/ToastContext.ts` + `useToast.ts` · `src/components/ui/useToast.tsx` + `TrafficLightButtons.tsx` · `src/contexts/{AmbientThemeContext,PhotoViewerContext}.tsx` · `src/lib/utils.ts` · `src/hooks/{useActionSystem,useAmbientTheme,useDebounce,useLiveMatchCount,useNotch,usePerformanceMonitor}.ts` · `src/utils/{pickDirectory,styleUtils}.ts` · `src/components/api.ts`

Notable good practice observed: `PhotoDetail`/`PhotoGrid`/`Trash` destructive flows that *do* confirm; `TrafficLightButtons` aria-labels; `LazyImage`/`SecureLazyImage` IntersectionObserver gating; `ErrorBoundary` present at root.

---

## 7. Recommended remediation order

1. **Stop the data-loss class first** (P0.1–P0.2): make `confirm: true` the only callable mode from UI, implement or remove the "can be undone" promise (a real restore-from-trash undo, or drop the claim), add confirm/undo to the 16 destructive handlers in §2.1.
2. **Kill the fake-data surfaces** (P0.3): wire Import/OCR/Export progress to real backend events or label as "estimated"; replace mocked Analytics/AIInsights/Provenance with real data or hide the tabs.
3. **One shared `<Dialog>` primitive** (§3.1): Escape + focus trap + restore + `role="dialog"` — replaces ~22 bespoke modals and erases ~30 findings at once. (Radix `Dialog` is already adjacent via `cmdk`.)
4. **A11y sweep in three passes:** (a) viewport meta + notch trigger + tab-order cleanup + `aria-live` in `ToastProvider`/`ErrorDisplay` (one provider-level region covers most announcements); (b) icon-button `aria-label`s (~60); (c) form label associations (~70) — mechanical, scriptable with eslint `jsx-a11y` rules added to `eslint.config.js`.
5. **Performance:** reintroduce windowing on `PhotoGrid` (react-window was just removed — its use belongs here), cap accumulated pages in `PhotoSearchContext`, fix per-hover/per-keystroke fetches.
6. **Motion:** add `MotionConfig reducedMotion="user"` in `App.tsx` (one line), then codemod `transition-all` → explicit properties (98 instances), add the 4 missing CSS guards.
7. **Bugs & dead UI** from §2.5, then the P3 polish pass (copy script can fix `…`/`tabular-nums` mechanically).

---

## Appendix A — Method & coverage

Five parallel read-only audit agents, disjoint file batches, each reading its files **in full** (no excerpt-skimming):

| Batch | Files | Lines ~ | Findings ~ |
|---|---|---|---|
| Shell / layout / nav / common / contexts | 30 | 6k | 71 |
| Gallery core | 30 | 9k | 97 |
| Search + features (OCR, Globe, Analytics) | 33 | 12k | 105 |
| People + pages | 30 | 10k | 158 |
| Editing / panels / dialogs / hooks | 40 | 11k | 187 |

Plus mechanical greps: `outline-none` (24), `transition-all` (98), `autoFocus` (7 — all in intentional overlays, not flagged except `EnhancedSearchUI.tsx:749` page-mount), `div/span onClick` (8, all modal backdrops = acceptable), `user-scalable` (1), `prefers-reduced-motion` (3 files), `tabular-nums` (1), `text-balance/pretty` (0), `loading="lazy"` (4), `aria-label` (105 — concentrated in few files).

## Appendix B — Spot-verifications (hand-checked post-sweep, all confirmed)

1. `index.html:11` viewport blocks zoom ✓ 2. `api.ts:1264` `confirm=false` default + `BulkActions.tsx:69` no confirm arg ✓ 3. `BulkActions.tsx:153` undo = `console.log` + `:382` "can be undone" copy ✓ 4. `PhotoGrid.tsx:606` `Math.random()` in render ✓ 5. `safeAreaStyles.ts` all-sides padding bug ✓ 6. `Duplicates.tsx:466,478` immediate delete_all/keep_selected ✓ 7. `tailwind.config.js` lacks `pulse-slow` ✓ (note: `delay-1000` is a valid core utility; only `pulse-slow` is dead) 8. `Layout.tsx:56,298` `statusOpen` never set true ✓ 9. `AnalyticsDashboard.tsx:668` hardcoded "New York 1,234 photos" ✓ 10. `ImportWizard.tsx:83` simulated progress loop ✓ 11. `index.css:159` `transition: all` on `.btn-glass` ✓ 12. `PrivacyControls.tsx:114` `btoa` "hash" with self-aware comment ✓

## Appendix D — Remediation log (same day, post-audit)

Verification: `tsc -b && vite build` ✓ · `vitest run` 29/29 ✓ · `eslint` on all touched files ✓.

### Fixed (P0 class)

**Data-loss / misleading-undo class (§2.1, §2.2):**
- `bulk/BulkActions.tsx` — delete now routes through `/trash/move` (recoverable) instead of the permanently-deleting `/bulk/delete`; undo is **real** (`trashRestore` with the recorded trash item IDs); dialog copy now says "Move to Trash… restore from the Trash page" instead of the false "can be undone"; Undo button hidden for `archive` (was a console.log no-op); invalid Tailwind classes (`bg-green/20` → `bg-green-500/20` etc.) fixed so badges actually colorize; aria-labels + label associations + `spellCheck=false` on path inputs added. *Discovery: the backend rejects `confirm: false` with 400 (`server/api/routers/bulk.py:66`), so bulk delete was silently broken before this fix.*
- Immediate destructive actions now confirm via the codebase's existing `window.confirm` pattern: `Duplicates.tsx` (delete_all + keep_selected discard, handler-level so all call sites are covered), `MergeSuggestions.tsx` (merge), `PeopleChips.tsx` (remove person), `ReviewQueue.tsx` (Confirm/Reject All), `GestureActions.tsx` (swipe-to-delete), `PhotoFacePanel.tsx` (hide person), `EditTab.tsx` (Reset All), `InlineEditMode.tsx` (cancel-with-changes + reset), `NotesEditor.tsx` (delete note), `PrivacyControls.tsx` (revoke access), `PrivacyDashboard.tsx` (anonymize — strong irreversible warning), `JobMonitor.tsx` (clear list), `PerformanceDashboard.tsx` ×2 (clear cache).

**A11y blockers (§2.4):**
- `index.html` — removed `maximum-scale=1.0, user-scalable=no` (pinch-zoom restored).
- `DynamicNotchSearch.tsx` — primary notch trigger now has `role="button"`, `tabIndex`, Enter/Space handler, `aria-expanded`/`aria-label`; search input `type="search"` + `aria-label`; clear button labeled.
- `ActionsPod.tsx`, `layout/ModeRail.tsx`, `components/ModeRail.tsx` — collapsed nav containers get `inert={!open}` → invisible links no longer tabbable.
- `ToastProvider.tsx` — toast region is now `role="status" aria-live="polite"` (all toasts announced, incl. undo offers).
- `ErrorDisplay.tsx` — `role="alert"`.
- `TopNavigation.tsx` — `aria-expanded` now bound to state; mobile menu closes on navigation.
- `AccessibilityPanel.tsx` — `JSON.parse`/`setItem` guarded; corrupted storage no longer crashes the panel.
- `PhotoGrid.tsx` — favorites toggle reveals on `group-focus-within` (keyboard users can reach it).

**Functional bugs (§2.5):**
- `PhotoGrid.tsx` — masonry row-span now derives from a stable hash of the path instead of `Math.random()` during render (no more layout re-shuffle); stray `console.log` removed.
- `safeAreaStyles.ts` — `ptSafe/prSafe/pbSafe/plSafe` (+ margins) apply the inset to the correct side; `pSafe` uses per-side `max()` instead of the top inset everywhere. (No current consumers — latent fix.)
- `VideoFacesPanel.tsx` — non-Latin-1 video paths no longer throw in render (Latin-1 paths keep identical derived IDs).
- `StoryCreator.tsx` — caption Save button no longer swallowed by blur-cancel (`onMouseDown` preventDefault); deprecated `onKeyPress` → `onKeyDown`; caption display is keyboard-operable.
- `AddToTagDialog.tsx` — validation runs **before** tag creation (no more orphan tags on empty submit).
- `FirstRunModal.tsx` — "Connect a Source" marks the intro seen and navigates without the dead `#sources` anchor. (Note: this component is currently rendered nowhere — latent fix.)

### Still open (unchanged from the audit)

Shared `<Dialog>` primitive (~22 modals), `aria-live` beyond toasts, the ~60 icon-button and ~70 form-label sweeps, `transition-all` codemod (98), `MotionConfig reducedMotion="user"`, unvirtualized grids, URL-state sync, `color-scheme: dark`, mock-data surfaces (Import/OCR/Export progress, Analytics, AIInsights, Provenance), `btoa` "hashing" in `PrivacyControls` (needs a backend contract decision — server key handling), and the OCR "Clear Cache" button (no backend endpoint exists yet).

### Remediation pass 2 — modal/focus infrastructure (same day)

Verification: build ✓ · vitest 29/29 ✓ · eslint on all touched files ✓.

- **`src/hooks/useModalBehavior.ts` (new)** — shared dialog behavior: Escape closes (capture-phase, wins over inner inputs), Tab is trapped inside the panel, focus moves to the first focusable on open and returns to the trigger on close. Callers pass the returned `panelRef` + `role="dialog" aria-modal="true"` + an accessible name — one import and one hook call per modal instead of a structural rewrite.
- **App-wide reduced motion** — `MotionConfig reducedMotion="user"` wraps the app in `App.tsx`; framer-motion animations now honor the OS `prefers-reduced-motion` setting globally.
- **11 modals migrated to the hook:** `MoveFaceModal`, `SplitClusterModal`, `SimilarFaceSearch`, `BooleanPeopleSearch`, `FaceAttributeSearch` (standalone) + `People.tsx` rename/delete modals, `PersonDetail.tsx` split/move/similar modals, `PhotoFacePanel.tsx` similar-faces modal (inline). All gained Escape, focus trap, focus restore, `role="dialog"`, and close-button `aria-label`s; People/PersonDetail modals also got label associations, `aria-label`s on placeholder-only inputs, and `…` copy fixes.

**Remaining modal migrations (~17):** PhotoDetail (2), ResponsiveGallery, AdvancedFaceSearch, NaturalLanguageFaceSearch, MatchExplanation, FirstRunModal, AddToAlbumDialog, CreateAlbumDialog, CollaborativeSpaces (4), SmartCollections (2), ExportDialog, ImportWizard, PrivacyDashboard (2), VideoAnalysisPanel, StoryCreator, ConnectSourceModal, AddToTagDialog — each is now a ~4-line change using the same hook.

### Remediation pass 3 — full remediation (2026-10-19)

Scope: every remaining audit class, executed wave-by-wave (investigation → modals → a11y → CSS → copy → real-data wiring → performance → codemod → lint gate). Three investigation agents ran first (modal inventory with ESC-layering/portal gotchas; mock-data↔endpoint mapping incl. git-archaeology on the Layout popover; per-occurrence `transition-all` classification). Findings reshaped the plan — see `docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md` for the full endpoint/dead-code map.

**Verification gate (final):** `tsc -b && vite build` ✓ · `vitest` 8 files / **35/35 tests** ✓ (6 new `useModalBehavior` regression tests incl. a jsdom layout stub) · `npx eslint .` → **0 errors** / 134 warnings (documented debt below) · `transition-all` in TSX: **0**.

**A11y institutionalized:** `eslint-plugin-jsx-a11y` added to `eslint.config.js` (recommended set; static-element interaction rules demoted to **warnings** as migration debt; `no-autofocus` off — intentional overlay pattern; `media-has-caption` warn — needs caption assets). The ~130 remaining warnings are the legacy click-only-div pattern (many in unmounted components), now impossible to miss.

- **Modals:** all **23** custom dialogs now run on `useModalBehavior` (Escape capture-phase, Tab trap, initial/restore focus). ESC layering solved for stacked modals (PhotoDetail lightbox detaches while its explanation modal is open; CollaborativeSpaces details modal won't close under its invite/add-photo children). OAuth-wait guard added to ConnectSourceModal. Mid-operation backdrop closes guarded (Export/Import/Story/OAuth). Popovers (SearchModeHelp, PhotoGrid select menu, PhotoGlobe help) got Escape + ARIA without modal semantics.
- **A11y sweeps:** ~100 icon-button `aria-label`s; ~70 label associations (57 in the final lint pass — the plugin now enforces these); `aria-live`/`role=status` on result counts + `role=alert` on errors across all live panels; toasts announced; tab groups get `role=tablist/tab/aria-selected`; switch semantics (`role=switch aria-checked`) on toggles; context menu gets `role=menu/menuitem` + keyboard-openable submenu; hover-only reveals got `group-focus-within`; click-only divs keyboard-operated; MultiTagFilter's `prompt()` replaced by an inline labelled input and its suggestions became a keyboard-navigable listbox.
- **Motion:** `<MotionConfig reducedMotion="user">` app-wide; **70 TSX `transition-all` codemodded** (55 → `transition`, 9 → `transition-[width]`, 3 → `transition-[max-width,opacity]`, plus `[right]`, `[filter,transform]`, `[width,background-color]`); all CSS `transition: all` → explicit property lists; reduced-motion guards added to every stylesheet with infinite keyframes (incl. closing the modern-gallery reduce-block gaps); a latent bug was found and fixed en route — `--ease-custom-1/2/3` were referenced but never defined (three transitions were silently invalid CSS).
- **Theming:** `color-scheme: dark` set; `h1–h4 { text-wrap: balance }`; the five light-palette studio stylesheets (CodeSplitting, FaceClustering, TauriIntegration, ModalSystem, +IntentRecognition verified TSX-side) converted to design tokens with documented mapping deviations; TauriIntegration's 37 unscoped selectors scoped under `.tauri-integration`.
- **Copy/typography:** 93 ASCII `...` → `…`; `tabular-nums` on 31 stat displays.
- **Mock data → real:** AnalyticsDashboard now renders real `/locations/clusters`, `/timeline` (aggregated to years client-side), tag state, `/api/faces/stats`, `/ocr/stats`, `/api/performance/{metrics,cache-stats}`; storage breakdown computed from the metadata sample (bug found: it read `metadata.file.size_bytes` but the extractor writes `filesystem.size_bytes` — the estimate was silently always 0); fake "+12%"/"87%"/"New York" copy deleted; Export button does a real JSON download; "Review Duplicates" navigates for real. ImportWizard now performs a **real import**: pickDirectory → `/sources/local-folder` → polls `/jobs/{id}` (real progress/message, jobs surfaced to JobMonitor), with backend-unbacked org options disabled and honestly labelled. OCR panel: "Clear OCR Data" wired to `DELETE /ocr/all` with confirm; backend-unbacked settings honestly disabled; per-result "View Image" now actually opens the image.
- **Performance/bugs:** IntentRecognition + IntentBasedSearch keystroke fetches debounced (300 ms); PhotoGlobe rotation is delta-time-based (was refresh-rate-dependent), accent-color 500 ms polling removed in favour of the existing `lm:prefChange` event, marker hover signed-URLs cached; PhotoGrid hover fetches cached + stagger capped (`min(i,12)`); SecureLazyImage no longer fetches server config per image; Spotlight pauses polling when closed and caps rendered results; VideoFacesPanel/VideoAnalysisPanel polling cleaned up on unmount; usePhotoSearch double initial fetch fixed; LazyImage shows an error state instead of an infinite spinner; dead OCR/analytics controls made honestly disabled.

**Remaining documented debt (warnings + open items):** ~130 static-element interaction warnings (legacy click-div pattern; many in unmounted components), 3 pre-existing exhaustive-deps, `media-has-caption` (needs caption assets). Backend gaps discovered and NOT papered over: no `GET /jobs` list endpoint (client method 404s), no provenance/C2PA API, `ai_insights` patterns endpoint returns placeholder server-side, no OCR settings/cache-config endpoints, search-history is not recorded, `/locations/clusters` + `/locations/nearby` have duplicate route registrations (first shadows the richer second).

### Remediation pass 4 — mount pass (2026-10-20, decision: "obv. mount")

Investigation (git archaeology + import graph + endpoint mapping) applied the mount decision per component rather than blanket — the no-duplicate-systems doctrine overrides a literal mount where a component is superseded. Full evidence in `docs/UI_AUDIT_REMEDIATION_EXPLORATION_2026-10-19.md` §0.

**Mounted:** FirstRunModal (restoring the pre-`a33e786` App mount that a file relocation dropped; wired to `setSearchMode(mode, {source:'manual'})`) · ExportDialog as the single export flow from PhotoGrid selection (both buttons), gaining the previously-missing real zip download and an honest indeterminate state (the dialog fetched the blob and never saved it; PhotoGrid's inline quick-export was consolidated into the dialog) · `/collaboration` (CollaborativeSpaces) and `/places` (PlaceClustering) routes with ActionsPod links; PlaceClustering's dead "View" console.log now really loads `/locations/places/{name}` thumbnails (new `api.getPlacePhotos`) · studio routes `/studio/video-analysis` (VideoAnalysisPanel), `/studio/ai-insights` (AIInsights), `/studio/modern-gallery` (ModernGalleryDemo), `/studio/responsive-gallery` (ResponsiveGallery, context-fed wrapper).

**Backend completions:** `GET /jobs` list (canonical `EnhancedJobStore.list_jobs`; persistent rows normalized `job_type`→`type`) — the client's `api.listJobs` no longer points at a 404; removed the two provably unreachable shadow registrations of `/locations/nearby` and `/locations/clusters` in `locations.py` (second registrations against the other DB module; FastAPI first-match-wins; frontend consumes the first shapes).

**Not mounted, with evidence:** OCRSearch (duplicate of live OCRTextSearchPanel, same endpoint), Mobile/Sidebar/TopNavigation (Layout was explicitly rebuilt around ModeRail+ActionsPod — `Layout.tsx:24`; all three navs are unmounted, TopNavigation included), ProvenanceChips (no backend; would fabricate data). These become delete-or-build decisions with the evidence recorded.

**Verification:** build ✓ · vitest 35/35 ✓ · eslint 0 errors ✓ · backend smoke via TestClient: `/locations/clusters` + `/locations/nearby` 200 after dedup, zero duplicate paths in the route table, new `list_jobs` route handler executes and returns `{jobs, count}`; `pytest tests/test_integration.py tests/test_new_features.py` 21/21 ✓. Mounting also caught dead-code rot: ModernGalleryDemo's CSS imports had always-wrong relative paths (never bundled before) — fixed. Known pre-existing TestClient artifact (not a regression): the untouched `/jobs/{job_id}` route 500s under TestClient because `PersistentJobStore`'s shared SQLite connection is main-thread-bound; hardening that (per-thread connections or `check_same_thread=False` + lock) is a backend follow-up.

## Appendix C — Related docs

- Decision: `docs/decisions/2026-10-14-boundary-contract-chain.md` (generated types — API contracts are green; this audit covers the presentation layer)
- Operating doctrine: `OPERATING_DOCTRINE.md`
