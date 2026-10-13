# Granular Ideas & Technical Nuances from Old Project

> **Source**: `old_project_docs/`
> **Purpose**: A deep-dive supplement to `IDEAS_FROM_OLD_PROJECT.md`, capturing specific configurations, "minute" details, and technical implementation planning that might be missed in a high-level overview.

---

## 1. Electron & Desktop Specifics (Hardening & UX)

These are specific technical configurations found in `DESKTOP_APP_AUDIT.md` and `OFFLINE_MODE_IMPLEMENTATION.md`.

- **Security Hardening**:
    - **Context Isolation**: Must be `true` in `webPreferences`.
    - **CSP Injection**: Use `session.defaultSession.webRequest.onHeadersReceived` to inject a strict CSP:
      ```
      default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self' data:
      ```
    - **OpenExternal Protection**: Whitelist only `['https:']` protocols to prevent arbitrary command execution.
    - **IPC Validation**: Validate *every* IPC message from the renderer using Zod schemas.

- **Offline configuration**:
    - **Environment Variable**: `OFFLINE_MODE=1` triggers the offline behavior.
    - **Model Paths**: Automate detection of:
        - macOS: `~/Library/Caches/photo-search/models`
        - Linux: `~/.cache/photo-search/models`
        - Windows: `%LOCALAPPDATA%\photo-search\models`
    - **Bundled Models**: Specifically `clip-vit-base-patch32` and `clip-vit-b-32` in `electron/models/`.

- **UX "Minute" Details**:
    - **Window Management**: Remember window position/size state in `electron-store`.
    - **Native Menu**: "Refresh Bundled Models" action in the menu bar.
    - **First Run**: < 90 seconds setup time target.

## 2. Visual Testing & Quality Standards

Specific numbers and tolerances from `VISUAL_TESTING_GUIDE.md`.

- **Visual Diff Tolerance**:
    - `maxDiffPixelRatio: 0.02` (2%) is the gold standard used.
    - **Masking**: Always mask timestamps, counters, and dynamic user IDs before snapshotting.
- **Helper Functions**:
    - `dismissOverlays(page)`: Specific utility to kill welcome modals before testing.
    - `safeClick(page, selector)`: Robust click with retry logic for flaky UI.
- **Performance Thresholds**:
    - **Load Time**: < 3.0s (DOM + Paint).
    - **Search Response**: < 2.0s (End-to-end).
    - **Memory Usage**: < 100MB heap size for long-running sessions.
    - **Scroll FPS**: > 55fps at 10k items.

## 3. Performance & Architecture Specifics

From `PERFORMANCE_OPTIMIZATIONS.md` and `DESKTOP_APP_AUDIT.md`.

- **Virtualization Library**: The old project recommended migrating *from* `react-window` *to* `@tanstack/react-virtual` for better handling of dynamic heights and modern React 18 patterns.
- **State De-coupling**: Extract `search`, `selection`, and `filters` into *separate* small Zustand stores to avoid `App.tsx` re-render cascades. This was a specific "Quick Win" identified.
- **Debounce**: 150ms for search input keypresses.
- **Offline Guard**: Central `isOnline()` utility checking `navigator.onLine` *plus* a feature flag.

## 4. Error Handling & Reliability

From `ERROR_HANDLING_BEST_PRACTICES.md`.

- **Specific Error Types**: Implement these exact enums for consistent handling:
    - `NETWORK`, `VALIDATION`, `PERMISSION`, `NOT_FOUND`, `TIMEOUT`, `RATE_LIMIT`, `SERVER`, `UNKNOWN`.
- **Context Structure**: Every error log *must* include:
    ```typescript
    {
      component: "ComponentName",
      action: "function_name_or_user_action",
      userId: "...", // masked
      ...metadata
    }
    ```
- **Job Queue**: A file-backed `jobs.json` with checkpointing for long-running offline tasks (dedupe, index).

## 5. "Missing" Features (Ready-to-Build Ideas)

From `MISSING_FEATURES_ANALYSIS.md` - specific features that were fully planned but never built. These are "low hanging fruit" ideas.

- **Collections**:
    - **Smart Collections Builder**: A UI specifically for creating rule-based albums (e.g., "Date > 2024 AND Rating > 4").
    - **Trips Visualization**: Auto-grouping photos by GPS + Time into "Trips".
- **AI/ML**:
    - **Face Name Assignment**: The UI to actually *name* the clusters found by InsightFace.
    - **OCR Text Search**: The UI to search for text *inside* images (`apiOcrSnippets` endpoint).
    - **Similarity Search**: A "Find Similar" button that calls `/search_like`.
- **Image Editing**:
    - **Crop/Rotate**: Basic non-destructive edits using the `/editing/apply` endpoint.

## 6. Minute UX Trivia & "Small Merit"

- **Mobile Limits**: The old project specifically limited mobile bottom nav to **4 tabs** (Home, Search, Favorites, Settings) for simplicity.
- **Keyboard Navigation**:
    - `/` to focus search.
    - `ESC` to clear/close.
    - `j`/`k` (Vim style) navigation was planned/partially implemented.
- **Badge Colors**:
    - **Blue**: AI Intent.
    - **Amber**: Spelling correction.
    - **Green**: Synonym/Related.
    - **Purple**: Popular/Trending.
- **Font Strategy**: **Bundle fonts locally** (`assets/fonts/Inter.woff2`) to avoid *any* external requests (privacy + offline).
