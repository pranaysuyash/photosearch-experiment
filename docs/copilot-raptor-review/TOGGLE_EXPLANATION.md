# Toggle Explanation — Semantic vs Metadata vs Hybrid

This doc provides copy, UX patterns, accessibility recommendations, and testing scenarios for the main search toggle.

## Toggle Purpose

The toggle allows users to choose between different search strategies:

- Metadata: Fast, precise queries based on EXIF, filename, date, and exact fields.
- Semantic: Natural-language, image-content-based search powered by embeddings (CLIP or similar).
- Hybrid (optional): Combines both semantic similarity and metadata boosting for best-of-both-worlds.

## UI Pattern Recommendation

1. Control Type: Use a segmented control or small radio toggle with three states: `Metadata`, `Hybrid`, `Semantic`.
2. Placement: Place the toggle adjacent to the search field; this keeps it discoverable and relevant.
3. Tooltip: Provide a short inline tooltip (30–60 chars) below the control with an example for each mode.
4. Secondary Info: When a mode is selected, show a small hint bar below the search box explaining how to craft queries and what to expect.

## Suggested Default Behavior

- Default to `Metadata` in the initial release (faster, lower resource cost). For Mac-first desktop users with small-to-moderate collections (<= 10k), consider a small popup during first-run that suggests: "Try Semantic Search for more creative results — works best with local models or cloud providers enabled." and allow enabling.
- If `Hybrid` is provided, keep it as an intermediate option with an advanced slider to control weights (e.g., 70% metadata + 30% semantic).

## Tooltips / Help Copy

- Metadata: "Search by exact fields like filename, date, camera or format. Use this for precise queries and quick results." (Tooltip emoji: 🔎)
- Semantic: "Search by what the image looks like—describe it naturally (e.g., 'dog on beach at sunset'). Uses AI-based embeddings." (Tooltip emoji: 🤖)
- Hybrid: "Combines exact metadata matches with similarity results for balanced output." (Tooltip emoji: ⚖️)

## Query Examples to Display

Place example queries in the placeholder or an inline suggestion popover, tailored to each mode:

- Metadata: "camera=Canon AND image.width>=1920" or "filename contains 'vacation'"
- Semantic: "woman in red dress" or "sunset over the ocean"
- Hybrid: "sunset + camera=Sony"

## Copy & Icons

- Metadata icon: `filter` or `tag` icon
- Semantic icon: `sparkles`, `brain`, or `star` icon
- Hybrid icon: `layers` or `balance` icon

## Accessibility

- Use a labelled `aria` group for the segmented control.
- Provide accessible descriptions and state announcements for screen readers.
- Make sure keyboard toggles (left/right arrow) switch state.

## Fallbacks & Error States

- If the semantic model or the embedding service is unavailable, gray out `Semantic` and show a tooltip: "Semantic search unavailable — fallback to metadata enabled." (Provide a CTA to retry or run a quick test to re-connect.)
- If the user toggles `Hybrid` but embeddings aren't loaded: fallback to metadata and show a small toast message.

## Testing Scenarios

1. Default state tests: app opens in `Metadata`; search is accurate.
2. Semantic works: queries return visually similar images, and duplicate exact metadata mismatches are not included.
3. Hybrid: confirm results contain metadata-filtered items boosted by semantic similarity.
4. Unavailable provider: toggle is disabled and the tooltip shows an error solution.

## Metrics to Track

- Toggle usage % (which mode users choose)
- Query latency per mode
- Click-through rate from results by mode
- Semantic mode fallback rates (how often model failed)

## Open Questions / Suggestions

- Would you like a single default mode per user that can be set in settings? (Yes: remembers preference)
- Should we add a quick "Try Semantic" button that rewrites the user's query into a semantic search? (Nice-to-have)

End of Toggle Guide
