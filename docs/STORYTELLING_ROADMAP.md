# Multimodal Storytelling Roadmap – “Living Museum” Narratives

## 1. Vision & Value

**Goal**: Turn a user’s photo/video library into “living stories” – AI‑generated narratives, timelines, and maps that make it easy to relive and share meaningful sequences (trips, seasons, years, themes).

**Why now**:

- You already have: rich metadata (time/place), semantic search (embeddings), timelines, globe, and a Story Mode surface.
- A thin narrative layer on top can differentiate this app from “just another viewer” and create shareable, emotional output.

**High‑level outcomes**:

- “Generate a story from this trip / selection / time range.”
- See a structured outline (chapters, key moments) plus an optional AI‑written narrative.
- Share or export stories as text/HTML/PDF, and revisit saved stories later.

This roadmap assumes a **hybrid architecture**: cloud LLMs are first‑class for narrative quality, while local/cheap options can be added later for privacy or offline needs.

> STATUS UPDATE (2025-12-13): Implementation progress
>
> - The Story Mode UI surface exists (`ui/src/components/StoryMode.tsx` and `ui/src/pages/StoryModePage.tsx`) and supports outline/preview and basic controls.
> - Phase 0/Phase 1 backend pieces are currently proposed and not yet implemented: `StoryBuilder` server code and `/api/story/*` endpoints remain TODO.
> - LLM integration (server-side narrative generation) has not been implemented; it remains an experimental objective for subsequent sprints.

---

## 2. Scope & Non‑Goals

**In scope (over phases)**:

- Story skeletons from metadata, embeddings, and attention (chapters → events → photos).
- Cloud‑backed narrative generation with pluggable providers (OpenAI, Groq, etc.).
- Story Mode UX with:
  - Outline view.
  - Narrative view (experimental toggle).
  - Visual timeline + map context.
- “Generate story” entry points from selection, trips/timeline, and recents.
- Basic export/sharing of stories.

**Out of scope (for now)**:

- Full genealogy / family‑tree integrations.
- Rich multi‑user collaborative editing of stories.
- Heavy desktop publishing and print‑on‑demand flows (can be explored later as premium).

---

## 3. Milestones & Phases

### Phase 0 – Foundation: Story Object Model & Selection Integration

**Outcome**: A neutral, implementation‑agnostic “story skeleton” plus the ability to call it from the UI.

- Backend:
  - Define a `Story` schema (chapters, events, themes, photo IDs).
  - Implement a `StoryBuilder` that:
    - Takes a list of photo IDs.
    - Fetches metadata (timestamps, GPS, tags, embeddings as needed).
    - Produces a minimal `Story` object (even if all chapters are “Untitled” at this stage).
- Frontend:
  - Add an internal API client for `/api/story/build` (or similar).
  - Wire Story Mode to accept:
    - An explicit selection (photos selected in grid).
    - A time range (from timeline/trip view).
  - Show raw `Story` structure in a simple debug UI (e.g. JSON inspector panel in an “Experimental” section).

**Success criteria**:

- You can consistently produce a `Story` object for any selection of 10–200 photos.
- No LLM dependency yet; cheap to run and easy to debug.

---

### Phase 1 – Outline‑Only Storytelling (No LLM)

**Outcome**: Users can generate a _useful_ outline/storyboard from their photos based purely on metadata and basic clustering.

- Backend:
  - Extend `StoryBuilder` with:
    - Temporal clustering:
      - Group photos into sessions/days (e.g. break when gaps > 4–6 hours).
    - Spatial clustering:
      - Cluster GPS coordinates within a session into locations (city/region scale).
    - Theme extraction:
      - Use existing tags/collections/smart collections and light CLIP‑based labels to identify 2–4 keywords per cluster.
    - Generate factual summaries per event/chapter:
      - Example: “Morning in Lisbon; 12 photos near Alfama showing streets and viewpoints.”
  - API:
    - `POST /api/story/build`:
      - Input: `{ photoIds: string[] }`
      - Output: `{ story: Story }`
- Frontend:
  - Story Mode:
    - “Generate Story Outline” button.
    - Render:
      - Story title + timeframe (“Summer 2023 in Portugal”).
      - Chapters as vertical sections (title + short description + photo strip).
  - Entry points:
    - Grid: `Generate story from selection`.
    - Timeline/trip view: `Generate story for this trip / date range`.

**Success criteria**:

- Users can see a coherent, time‑ordered outline that mirrors their memories without any AI text.
- Building a story for ~50–100 photos completes within a few seconds.

---

### Phase 2 – Cloud LLM Narratives (Experimental)

**Outcome**: On top of the outline, users can optionally request an AI‑written narrative.

- Backend:
  - Implement `StoryNarrator`:
    - Accepts a `Story` object + options (tone, length, language).
    - Calls a pluggable LLM client (e.g., `LLMProvider` with adapters for Groq, OpenAI, etc.).
    - Uses a robust prompt:
      - Provides structured chapters/events, dates, locations, and themes.
      - Explicitly instructs: “Do **not** invent new locations or concrete facts; build narrative from the provided structure only.”
    - Returns a `StoryNarrative` object:
      ```json
      {
        "title": "Summer in Lisbon",
        "intro": "…",
        "chapters": [{ "title": "Arrival", "narrative": "…" }],
        "outro": "…"
      }
      ```
  - APIs:
    - `POST /api/story/narrate`:
      - Input: `{ story: Story, options: { tone, length, provider } }`
      - Output: `{ narrative: StoryNarrative }`
    - Convenience:
      - `POST /api/story/generate` that runs build + narrate in one call for UX simplicity.
- Frontend:
  - Story Mode:
    - Add an “AI Narrative (Experimental)” button or toggle:
      - Options: “Outline only” vs “Outline + AI story”.
      - Provider dropdown (if multiple LLMs are configured).
    - Show states:
      - Building outline → Generating narrative → Ready.
      - Clear error state with fallback to outline.
    - Render:
      - Narrative intro/outro.
      - Narrative per chapter alongside its photos.
  - Settings:
    - “AI storytelling” section for:
      - Selecting provider(s) and keys.
      - Toggling AI narrative on/off.
      - Brief privacy note (“Sends derived metadata (time/place/themes), not raw image data, to the selected AI provider.”).

**Success criteria**:

- For typical trips (20–100 photos), the narrative is coherent, stays faithful to locations/time, and feels engaging.
- Users can easily distinguish experimental AI content from factual outline.
- Failures (API errors, bad JSON) fall back gracefully to the outline view.

---

### Phase 3 – Visual, Interactive Storytelling

**Outcome**: Stories feel like interactive exhibits: timelines, maps, and simple editing on top of AI text.

- Frontend:
  - Enhance Story Mode with:
    - Visual timeline strip:
      - Chapters mapped to time segments; clicking a chapter highlights its range.
    - Map panel:
      - Mark chapter/event locations; click to scroll to corresponding section.
    - Light editing:
      - Allow users to tweak chapter titles and descriptions.
      - Simple toggle to show/hide chapters in the final narrative.
  - Persistence:
    - Save stories as first‑class objects:
      - “My Stories” list with created/updated timestamps.
      - Ability to reopen, edit, and re‑narrate with a different tone.
- Backend:
  - Add story persistence (e.g., SQLite table):
    - Schema storing:
      - `story` (outline), `narrative`, metadata (owner, created_at, etc.).
  - Optional:
    - Track basic metrics (how often users generate, edit, export stories).

**Success criteria**:

- Users can revisit and refine stories, not just generate one‑off outputs.
- Navigation between story, timeline, and map feels integrated.

---

### Phase 4 – Sharing, Export & Premium Options

**Outcome**: Turn stories into artifacts users can share and potentially pay for.

- Sharing:
  - Export:
    - “Copy story as Markdown/HTML”.
    - “Export as printable PDF” (simple template).
  - Optional:
    - Lightweight share pages (hosted HTML) if you later add a cloud backend for story publishing.
- Premium (exploratory, not required immediately):
  - More advanced narrative styles and deeper analysis (e.g., cross‑year retrospectives, “best of decade”).
  - Higher story generation quotas or additional providers.
  - Richer export formats (photo books, layouts).

**Success criteria**:

- Users can easily take stories out of the app and use them in their own workflows (blogs, emails, slides).
- You have clear hooks for future monetization if desired.

---

## 4. Technical Architecture Highlights

Key design decisions to keep this flexible:

- **Separation of concerns**:
  - `StoryBuilder` (metadata/embeddings → structured outline).
  - `StoryNarrator` (outline → AI narrative).
  - Story persistence (DB/JSON), separate from raw media indexes.
- **Pluggable LLM providers**:
  - A small `LLMProvider` abstraction so you can:
    - Swap Groq/OpenAI/others.
    - Add local models later without rewriting Story Mode.
- **Async UX where helpful**:
  - For large selections or long stories, treat generation as a job:
    - Integrate with your jobs/progress UI if/when needed.
    - Let users continue browsing while the story builds.

---

## 5. Story Object Model & Data Structures

To keep the system inspectable and not overly dependent on any single LLM, the backend should standardize on a few core data structures.

### 5.1 Outline Structures

```python
class StoryEvent(BaseModel):
    start_time: datetime
    end_time: datetime | None
    location_label: str | None      # e.g. "Alfama, Lisbon"
    photo_ids: list[str]
    summary: str | None             # short factual description
    tags: list[str] = []


class StoryChapter(BaseModel):
    title: str                       # e.g. "Day 1 – Arrival"
    description: str | None          # optional prose summary
    events: list[StoryEvent]


class Story(BaseModel):
    id: str
    title: str
    timeframe: str                   # "June 2024", "Summer 2023", etc.
    main_locations: list[str]        # city/region labels
    themes: list[str]                # "beach", "family", "museum"
    chapters: list[StoryChapter]
```

`StoryBuilder` is responsible for constructing this structure from photo IDs, timestamps, GPS, tags, and embeddings.

### 5.2 Narrative Structure

The LLM should not return arbitrary free‑form text, but a structured narrative we can render safely:

```python
class StoryNarrativeChapter(BaseModel):
    title: str
    narrative: str                   # human‑readable text for this chapter


class StoryNarrative(BaseModel):
    title: str
    intro: str | None
    chapters: list[StoryNarrativeChapter]
    outro: str | None
```

`StoryNarrator` takes a `Story` + options and returns a `StoryNarrative`. The frontend can then:

- Show outline only.
- Show narrative only.
- Or show both side‑by‑side (outline with chapters and the AI text for each).

### 5.3 API Contracts (Summary)

- `POST /api/story/build`
  - Input: `{ "photoIds": string[] }`
  - Output: `{ "story": Story }`
- `POST /api/story/narrate`
  - Input: `{ "story": Story, "options": { "tone"?: string, "length"?: "short"|"medium"|"long", "language"?: string, "provider"?: string } }`
  - Output: `{ "narrative": StoryNarrative }`
- `POST /api/story/generate` (optional convenience)
  - Runs build + narrate and returns both `story` and `narrative`.

These structures give you:

- A clear separation between factual outline and generated prose.
- The ability to debug and iterate on clustering and theming independently of narrative style.

---

## 6. Risks & Mitigations

- **Hallucinations / incorrect facts**:
  - Mitigation:
    - Keep all factual structure in `Story` and clearly tell the LLM not to invent new locations/names.
    - Expose the outline alongside the narrative so inconsistencies are visible.
- **Latency & cost of LLM calls**:
  - Mitigation:
    - Start with outline‑only Phase 1.
    - Use concise, summarized story outline as input rather than raw photo lists.
    - Add settings for provider and quotas.
- **User trust**:
  - Mitigation:
    - Always show when a story is AI‑generated and that it may contain mistakes.
    - Make it easy to fall back to outline or edit text.

---

## 7. Next Steps

Short‑term concrete actions:

1. Define and implement the `Story` object model in the backend.
2. Implement `StoryBuilder` Phase 1 (time/place/themes → outline) and expose `/api/story/build`.
3. Wire Story Mode to:
   - Generate and render outline from a selection or trip.
4. Introduce `StoryNarrator` and `/api/story/narrate` behind an “AI Story (Experimental)” toggle.

Once this is working end‑to‑end, you can iterate on:

- Better clustering heuristics.
- Tone controls and multi‑provider support.
- Story persistence and export surfaces.
