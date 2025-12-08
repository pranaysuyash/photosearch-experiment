Actionable recommendations

1. Environment & reproducibility

- Add a `pyproject.toml` and adopt `uv` (or `poetry`) for project workflows, or keep `requirements.txt`+`pip` but add a dev requirements file and automation docs.
- If adopting `uv`, add a `uv.lock` file (via `uv lock`) for reproducible installs.
- Add a short `CONTRIBUTING.md` or README section with exact commands to create a venv and run tests (both pip and uv snippets).

2. Tests & CI

- Add a CI job (GitHub Actions, etc.) to run tests across Python versions (3.11+, CI hyperparameters) and ensure `uv lock`/`pip` installation is reproducible in the CI environment.
- Add tests for error conditions to confirm graceful handling (e.g., missing ffmpeg, invalid path, unknown image formats).

3. Dependencies

- Consider adding `sentence-transformers` or the embedding model as a dev or a non-dev dependency if the embedding tests are relied upon in CI; or provide a mocked version for CI to avoid heavy dependency costs.
- Keep `requirements.txt` updated for core runtime dependencies, and add `dev-requirements.txt` for test-only dependencies (pytest, mock, etc.) if you prefer pip-based workflows.

4. Documentation

- Add a short note about uv usage and why it may be present in `pyvenv.cfg`. Document whether `uv` is the primary package manager (project-level decision).
- Document how contributors should setup the environment and run tests locally (both `pip` and `uv` instructions).

5. Check & remove surprises

- Check why pip was missing in the seed; consider using `uv venv --seed` in your setup scripts or onboarding docs to avoid surprise.
