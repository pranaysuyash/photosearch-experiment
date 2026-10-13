# SAST Remediation - 2026-03-12

- Replaced unsafe `eval()`-based FPS parsing in `src/video_analysis.py` with `fractions.Fraction`.
- Swapped standard XML parsers for `defusedxml.ElementTree` in:
  - `src/metadata_extractor.py`
  - `server/api/routers/sources.py`

Verification:
- `python -m py_compile src/video_analysis.py src/metadata_extractor.py server/api/routers/sources.py`
  - Result: success
