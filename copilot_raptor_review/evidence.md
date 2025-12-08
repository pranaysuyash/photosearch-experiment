Evidence & Logs

Command outputs captured during review:

1. Check uv path and version
   $ which uv
   /Users/pranay/.local/bin/uv

$ uv --version
uv 0.7.8 (0ddcc1905 2025-05-23)

2. pyvenv.cfg excerpt
   home = /Users/pranay/.local/share/uv/python/cpython-3.11.9-macos-aarch64-none/bin
   implementation = CPython
   uv = 0.7.8
   version_info = 3.11.9
   include-system-site-packages = false
   prompt = photosearch_experiment

3. pip seeded via uv
   $ uv venv --seed --allow-existing .venv
   Using CPython 3.11.9
   Creating virtual environment with seed packages at: .venv

- pip==25.3
- setuptools==80.9.0
- wheel==0.45.1
  Activate with: source .venv/bin/activate

4. Installed requirements and pytest
   $ source .venv/bin/activate
   $ python -m pip install -r requirements.txt pytest
   (install output suppressed for brevity)

5. Pytest results
   $ pytest -q --maxfail=1
   ... [100%]
   3 passed in 6.74s

6. pip list (partial)
   Pillow 12.0.0
   pip 25.3
   pytest 9.0.2
   sentence-transformers 5.1.2
