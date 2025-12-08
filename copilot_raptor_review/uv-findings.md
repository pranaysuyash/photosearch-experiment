UV (uv) - Project Manager Findings

Summary:

- `uv` is a modern, Rust-based Python package and project manager (https://github.com/astral-sh/uv). It provides a single CLI for venv management, dependency resolution, package installation, and other workflows (init, add, remove, sync, lock, etc.).
- Commands include `uv init`, `uv add`, `uv venv`, `uv sync`, `uv lock`, and more. `uv add` accepts package names or `-r/--requirements` to add from a requirements.txt.

Evidence in the codebase:

- The repository's `.venv/pyvenv.cfg` contains a `uv = 0.7.8` field, indicating that `uv` created the venv and managed the environment.
- Several packages in the venv `site-packages` directory have `INSTALLER: uv`, indicating installs performed by `uv`.

Notes about `uv add` usage:

- `uv add pytest --dev` will add pytest to the dev group and sync the project's venv.
- `uv add -r requirements.txt` adds packages from existing pip plain `requirements.txt` if the project uses that format, but `uv` typically expects a project file (`pyproject.toml` or `uv.toml`) and will create/modify config.
- If no Python project exists when calling `uv add`, use `uv init` to create a minimal project structure or use `uv venv` to create a virtual environment without adding a project file.

When to prefer `uv` over pip:

- Prefer `uv` when you want unified project management (Python version pinning, lock file, reproducibility) and faster dependency operations.
- `uv add` automatically creates and manages virtual environments; it will install seed packages (like pip) in the venv by default only if you pass `--seed`.

Compatibility with this repo:

- This repository currently uses `requirements.txt` rather than `pyproject.toml`.
- Running `uv add` without a `pyproject.toml` will fail; you can either call `uv init` first or use pip to install `requirements.txt`.

Recommendation:

- Decide whether to adopt `uv` as the project manager (preferred for modern tooling):
  - If you choose `uv`, create `pyproject.toml` or run `uv init` to initialize the project, then run `uv add -r requirements.txt` followed by `uv lock` to populate `uv.lock`.
  - If you prefer to stick with requirements.txt / pip, add documentation and a workflow to `README.md` showing commands to create a venv and seed pip (examples in environment-setup.md).

References & further reading:

- UV project: https://github.com/astral-sh/uv
- Sample guides and user posts: Dev.to and Medium articles about using `uv` for development workflows
