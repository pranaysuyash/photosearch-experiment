# Critical Audit: Phase 1 – First Run Experience

**Goal:** Analyze the user's journey from "Download" to "First Value" (Aha Moment).

## 1. What do we expect? (The Ideal Flow)
When a user opens "Living Museum" for the first time, they should feel:
1.  **Welcomed**: Acknowledged as a new user.
2.  **Oriented**: Briefly told what the app *does* (it's not just a gallery, it's a semantic search engine).
3.  **Empowered**: given an immediate, obvious action to **import their own life** into the app.
4.  **Reward**: Immediate feedback (a progress bar, spinning globe, or "Scanning...") leading to their photos appearing.

**The "Aha Moment"** is seeing their own memories mapped on the Globe or discoverable by "vibes" (semantic search).

## 2. What is Current? (The Reality)
1.  **Welcome**: `FirstRunModal` appears. It asks "Semantic vs Metadata?"
    *   *Critique*: A cognitive load too early. A new user might not know the difference or care yet. They have 0 photos indexed, so search mode is irrelevant.
2.  **Action**: User selects a mode -> Modal closes.
3.  **Result**: 
    *   **Scenario A (Has `media/` files)**: If the user manually copied files *before* launching, they might see them (if auto-scan ran).
    *   **Scenario B (Empty)**: Most likely scenario. The user sees an empty "Story Mode" grid.
    *   **Empty State UI**: "Your Museum is Empty. Add photos to the `media/` folder or run a scan."
4.  **Friction**: 
    *   The user is told to "Add photos to `media/`" (requires file system access, moving files).
    *   The user is told to "run a scan" but there is **no button to do so**. It's a dead end.

## 3. The Gap (Critique)
*   **Non-Actionable Empty State**: The app tells the user to do something ("run a scan") but provides no UI to perform that action. The "Scan" command is hidden in the Command Palette (Cmd+K), which isn't taught.
*   **Premature Configuration**: Asking about "Semantic vs Metadata" before the user has even imported a single photo is solving a problem they don't have yet.
*   **Missing "Import"**: The app assumes files effectively "magically appear" in a specific folder. A proper desktop app should let users **pick a folder** to index.

## 4. The "Better" Plan (Immediate Improvements)
1.  **Revamp `FirstRunModal`**:
    *   Instead of "Mode Selection", make the primary CTA **"Setup Library"**.
    *   If that's too complex for now, at least add a **"Scan default folder"** button.
2.  **Actionable Empty State**:
    *   In `StoryMode.tsx` (and `PhotoGrid`), replace the text instruction with a big blue button: **"Scan Library"**.
    *   Wire this button to trigger the `/scan` API `POST`.
3.  **Simplify Mode**: Default to "Hybrid" or "Semantic" (the "magic" one) and hide the technical choice until they are advanced users.

## 5. Next Steps (Action Items)
*   **IMMEDIATE**: Add a "Scan Library" button to the Empty State in `StoryMode.tsx`. 
*   **IMMEDIATE**: Add a "Scan Now" button in the `FirstRunModal` (or replace the modal with a "Welcome wizard").
