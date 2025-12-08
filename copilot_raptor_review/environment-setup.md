Environment & Setup Notes

Summary of actions performed during review:

1. Found `uv` CLI installed on the system: `which uv` -> `/Users/pranay/.local/bin/uv`, `uv --version` -> `uv 0.7.8`.
2. The `.venv/pyvenv.cfg` contains `uv = 0.7.8`, indicating the venv was created by `uv`.
3. The venv initially did not have pip installed (observed `No module named pip` when trying to check pip). This is common when uv-managed virtual environments don't seed with pip by default.
4. Seeded pip, setuptools, wheel into the existing venv using:

   uv venv --seed --allow-existing .venv

   This added `pip`, `setuptools`, and `wheel` to `.venv`.

5. After seeding, installed requirements and test tool using pip inside the venv:

   source .venv/bin/activate
   python -m pip install -r requirements.txt pytest

Best-practice recommendations:

- If you want a reproducible project with `uv`, add `pyproject.toml` or run `uv init` and then `uv lock` to create a lockfile.
- If you prefer `requirements.txt`, include a `dev-requirements.txt` or a concise list of test-related packages (pytest) in the repository and document the steps to use pip or uv in the README.
- Document your preferred environment setup and commands for new contributors; example README snippet is provided below.

Example README snippet:

```
# Development environment setup (pip + venv)
python3 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade  # if pip missing
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

# Run tests
pytest -q
```

or with `uv`:

```
uv init  # optional, creates pyproject if you'd like
uv venv --seed --allow-existing .venv
uv add -r requirements.txt  # or add explicit packages
uv add pytest --dev
uv lock  # create uv.lock
uv sync  # sync the environment
```
