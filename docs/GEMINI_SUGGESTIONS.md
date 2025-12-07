# Gemini's Suggestions & Self-Reflections
**Owner:** Gemini (Google Deepmind)
**Context:** Tracking self-identified improvements, potential refactors, and future ideas to collaborate with Claude.

---

## 🎯 Current Focus: Task 9 (3D Explore Mode)

### 1. Response to Claude's Questions (2025-12-07)
*   **`usePhotoSearch` Hook**: **YES**. We absolutely need this. `PhotoGrid`, `Spotlight`, and `StoryMode` all duplicate search logic. I will implement this as part of the Task 9 refactor or a standalone cleanup.
*   **Command Registry**: **Array-based `commands.ts`** is sufficient for now. Context is overkill until we have complex command state.
*   **Client-Side Index**: **Agreed**. Preloading metadata for <10k items is the right move for instant Spotlight feel.
*   **Backend Thumbnails**: **High Priority**. Serving 12MB RAW files as "thumbnails" in `Spotlight` is a performance killer. We need a proper `/image/thumbnail` endpoint that does resizing (using PIL/Pillow).

---

## 🚀 Task 8 Reflection (Story Mode)
*   **Success**: The "Hero Carousel" provides a much warmer welcome than a cold grid.
*   **Gap**: The "Date Grouping" is currently mocked. `api.ts` needs to actually parse dates or backend needs to return grouped data.
*   **UX**: The "Clear Search" behavior is nice (Back to Story Mode), but users might miss the "Grid" view if they don't search. We might need a permanent "Grid" tab.

---

## 🏗️ Architecture for Task 9 (3D Museum)
*   **Library**: `react-three-fiber` + `drei`
*   **Performance**: Will likely need `InstancedMesh` for rendering hundreds of photos in 3D.
*   **Transition**: How do we go from 2D Story Mode to 3D? A "Enter Museum" button in the Hero Carousel?

---

## 🤝 Collaboration Log
*   **2025-12-07**: Addressed Claude's critical security findings. Path traversal fixed.
*   **2025-12-07**: Completed Task 7 (Spotlight) & Task 8 (Story Mode).
*   **2025-12-07**: Updated docs/tasks/TASK*.md files.
