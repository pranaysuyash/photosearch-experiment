# Design & Copy Guidance — Toggles, Hints, and Error Messages

This document provides ready-to-use copy snippets for UI elements: toggles, tooltips, inline reminders, and error messages for different contexts.

## Toggle Copy

- Metadata: "Metadata (fast)" — short hint: "Use filters & fields"
- Semantic: "Visual & natural language (AI)" — short hint: "Describe what you want"
- Hybrid: "Combined (Hybrid)" — short hint: "Best of both"

## Tooltips & Inline Hints

- Metadata Tooltip: "Quick, exact matches. Use to search by camera, date, filename, or format."
- Semantic Tooltip: "Search by image content (visual similarity). Describe the photo using natural language."
- Hybrid Tooltip: "Combine both — exact filters plus visual similarity."

## Empty State Messaging

When there are no results, display contextual tips:

- Metadata mode: "No matches. Try less specific terms or remove metadata filters."
- Semantic mode: "No visually similar images found. Try different words (e.g., 'sunset beach' or 'mountain landscape')."
- Hybrid mode: "No combined matches. Try only semantic or metadata search to see different results."

## Error Messages & Copy

- Model Failure: "Semantic search is temporarily unavailable. Defaulting to metadata search. You can retry or enable a cloud provider for improved performance." (CTA: Retry)
- Permission/Error Loading Images: "Cannot read files in the selected directory. Check permissions or try another folder." (CTA: Choose another folder)
- Scan Failure: "Scan failed at step X due to Y. Continue with partial results or retry." (CTA: Retry)

## Microcopy (Settings & Buttons)

- "Toggle 'Semantic Search' may incur CPU use; enable only for large models or smaller datasets." Today: show as `Settings -> Search > Mode`.
- First-run: "Welcome! Do you want to scan your Photos now?" (Buttons: "Scan Now" / "Later")

## Example Prompts Display (Search Input Placeholder)

- Metadata: "Try: filename contains 'vacation' or camera=Sony"
- Semantic: "Try: 'child running in a park' or 'mountain sunset with lake'"
- Hybrid: "Try: 'sunset + camera=Sony'"

End of Design & Copy Guidance
