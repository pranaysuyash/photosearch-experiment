# First-Run Modal & Onboarding UX — PhotoSearch

## Purpose

This document provides the copy, wireframe, behavior, and acceptance criteria for the "First-Run" onboarding modal. The goal is to offer a frictionless initial setup that explains privacy, lets the user pick a first scan folder, explains search modes (Metadata vs Semantic vs Hybrid), and offers a demo dataset for new users who don’t want to scan their own files yet.

## Wireframe (Text-Based)

Modal Title: Welcome to PhotoSearch

Body:

- Intro: "Find any photo instantly using powerful search — local-first, private, and fast."
- Three-step onboarding bullets:
  1. "Choose the folder to scan (e.g., your Photos directory)." (CTA: Choose Folder)
  2. "Choose how to search: Metadata (fast) or Semantic (AI-powered)." (Toggle: Metadata | Hybrid | Semantic) + small tooltip next to each
  3. "Keep your photos private — local-first by default; enable cloud for advanced models (optional)." (Link to privacy doc)

Buttons: [Scan My Folder] [Try Demo Photos] [Skip & Explore UI]

Footer (Smaller text): "You can change these settings later under Settings > Data & AI Providers." (Link)

## Detailed Copy & Tooltips

- Intro: `“PhotoSearch helps you find photos using exact metadata or natural language. We don’t upload your images by default — local-only mode protects your privacy.”`

- Choose Folder:

  - Label: "Scan this folder" (file chooser)
  - Copy below: "We will scan this folder and build a local index for search. This may take time based on folder size. You can pause or cancel anytime."
  - If permission required: "This app needs access to the specified folder; you’ll be prompted by the OS to grant permission."

- Mode Toggle: (default: [Metadata])

  - Metadata tooltip: "Search by camera, date, filename, and exact fields. Use this when you need precise filters."
  - Semantic tooltip: "Search by describing the photo in natural language (e.g., 'child running on beach'). Uses AI-based embeddings — faster with local or cloud models enabled."
  - Hybrid tooltip: "Combine keywords and image similarity for balanced results. This uses metadata + semantic ranking."
  - Small help text: "Semantic search may use more compute. Enable cloud provider for improved models (optional)."

- Cloud Provider Consent: (checkbox)

  - Copy: "Enable cloud AI (optional) - this allows us to use provider models to speed up or improve semantic search. Data usage depends on your chosen provider and their policy."
  - Link: "Provider privacy policy" + "More details"

- Advanced: "Index location: [~/Library/Application Support/PhotoSearch] — change location" (for advanced users)

## Behavior & Flows

- If user chooses "Scan My Folder": Ask for OS permission, run a quick metadata-only scan to list files and show estimate, then ask if they want to index embeddings for semantic search (separate step or toggle). If `async` scan set: run as job.
- If user chooses "Try Demo Photos" - load a small demo dataset from `data/test_media` and seed the UI with example queries for the user.
- "Skip & Explore UI" - return to main app, show demo data or empty state with a prominent CTA to scan.

## Edge Cases & Error Handling

- If OS denies permissions: show a toast with manual instructions and an ability to choose a different folder.
- If path invalid or inaccessible: Show error with reason (e.g., no access, network disk not supported) and options to retry.
- If folder too large (>100k files): Show a warning: "Large library detected — indexing may take a while. We recommend starting with metadata-only and enabling semantic on-demand."

## Accessibility

- Ensure keyboard focus is trapped in the modal until the user chooses an option.
- All controls should have `aria-label` and `aria-describedby` attributes for screen readers.
- Modal should respond to `ESC` as cancel (with unobtrusive confirmation if a scan is running).

## Persistence

- Remember the user's initial choices (folder, mode, cloud opt-in) in local settings (persistent store or `localStorage`).
- Provide a `Reset` option in `Settings` to clear these choices and start-over.

## Acceptance Criteria

- [ ] Modal is shown on first app launch (or until canceled/full scan is completed).
- [ ] The toggle is present and mode is explained via tooltip and example placeholders.
- [ ] If user chooses `Scan`, a scan job is created (async) and user is shown a job tray with progress.
- [ ] If user chooses `Try Demo Photos`, a demo dataset is loaded locally and relevant example queries are shown.
- [ ] Cloud opt-in must be explicit; clear text indicates data to be sent and to whom.
- [ ] The modal is keyboard and screen reader accessible.

## Notes for the Implementing Team

- The modal is non-blocking — users can skip and try the UI with demo data.
- For the `Scan` path, run a quick metadata-only scan for the initial estimate and then ask to start embedding indexing (so users can choose to defer computationally heavy operations).

End of FIRST_RUN_MODAL.md
