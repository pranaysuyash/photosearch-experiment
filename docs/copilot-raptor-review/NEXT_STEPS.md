# Next Steps — Where to focus next (non-coding)

We reviewed the extensive efforts from Claude and Gemini and the Copilot Raptor audit material. Below are practical options for where to focus next as non-coding activities (docs, prep, and planning), together with what I'll produce if you pick an option.

## Options

1. Convert backlog into GitHub Issues (Recommended)

   - Output: One `.md` per issue in `docs/copilot-raptor-review/issues/` ready to copy/paste or import.
   - What this helps: Clean tracking, ownership assignments, and start of tasks without coding.

2. Produce OpenAPI (`openapi.yaml`) spec and examples

   - Output: A complete `openapi.yaml` for `GET /search`, `GET /search/semantic` (or `mode` param), `POST /scan`, `GET /jobs/{id}`, `GET /image/thumbnail`, `GET /timeline`, `GET /stats`.
   - What this helps: UI-client generation, doc-driven development, Tauri sidecar integration, and automatic test scaffolding.

3. Prepare a PR / QA checklist & code review guidelines

   - Output: A `PR_CHECKLIST.md` with tests, logging, security checks, and sample acceptance criteria for critical issues.
   - What this helps: Reproducible code quality and consistent reviewer expectations.

4. Draft the first-run modal UX and settings page copy

   - Output: A `FIRST_RUN_MODAL.md` with wireframe conceptual steps, copy, and toggles for local vs cloud providers.
   - What this helps: UX clarity for privacy & onboarding.

5. Create issue templates and estimate + assign roadmap tasks
   - Output: A `ROADMAP_ISSUES.md` with a 1-week/2-week/1-month plan and suggested owners (or roles) and prioritization based on the consolidated review.
   - What this helps: Clear target for team sprints and planning.

## How this will integrate

- Everything will be saved under `docs/copilot-raptor-review`.
- The issues will be concise, include `why`, `how`, and `acceptance criteria` so implementing engineers can pick them up with minimal ramp.

Select one or multiple options — I'll produce the requested artifacts next.

If no selection, I recommend Option 1 (issue creation) + Option 2 (OpenAPI) as immediate best actions to move from docs to action.

End of NEXT_STEPS.md
