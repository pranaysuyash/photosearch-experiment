#!/usr/bin/env python3
"""Operator-side acceptance baseline for Mimosa gate findings.

Mimosa 1.0.4 has no per-finding suppression surface: the git gate hard-denies
on `high` findings under the default `graded` mode, its hook logic is sealed,
and its finding ledger intentionally never closes a deny on behalf of the
operator. The sanctioned control the operator has is `MIMOSA_GIT_GATE_MODE`
(see docs/decisions/2026-10-19-mimosa-gate-policy.md).

This tool makes that operator decision auditable instead of decorative:

  verify                  validate the baseline file (schema, evidence links,
                          expired reviews) — exits non-zero on any defect
  parse <file|->          parse a captured gate denial message and emit ready-
                          to-review baseline entry stubs (with code hashes)
  diff <findings.json>    split a findings array into BASELINED vs NEW;
                          exits non-zero when unaccepted blocking findings exist

Baseline identity follows Mimosa's own scheme: (file, rule, sha256 of the
flagged source line). If the code at a site changes, the hash changes, the
entry stops matching, and the finding surfaces as NEW — re-review is forced.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "docs/security/findings-baseline.json"

RULE_ALIASES = {
    "ssrf 服务端请求伪造": "ssrf",
    "路径穿越": "path-traversal",
    "硬编码凭据": "hardcoded-credentials",
    "sql 注入": "sql-injection",
}

# Gate denial format: /abs/path [high] <rule name>；... (；-separated, high first)
SITE_RE = re.compile(r"(?P<file>/[^\s:]+):(?P<line>\d+)\s+\[(?P<sev>high|medium|low)\]\s+(?P<rule>[^；;]+)")


def _repo_file(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def line_hash(path: str, line: int) -> str | None:
    """sha256 of the current stripped content of the flagged line (Mimosa-style identity)."""
    f = _repo_file(path)
    if not f.is_file():
        return None
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    if not 1 <= line <= len(lines):
        return None
    return hashlib.sha256(lines[line - 1].strip().encode("utf-8")).hexdigest()


def load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def cmd_verify() -> int:
    defects: list[str] = []
    try:
        base = load_baseline()
    except Exception as exc:  # noqa: BLE001 - report any defect, never crash
        print(f"FAIL: baseline unreadable: {exc}")
        return 1
    if base.get("version") != 1:
        defects.append(f"unsupported version: {base.get('version')!r}")
    for i, entry in enumerate(base.get("accepted", [])):
        where = f"accepted[{i}] {entry.get('file')}:{entry.get('line')}"
        for field in ("file", "line", "rule", "code_hash", "rationale", "evidence", "accepted_by", "review_by"):
            if not entry.get(field):
                defects.append(f"{where}: missing {field}")
        if entry.get("class") not in ("sanitizer-not-modeled", "test-fixture", "accepted-risk"):
            defects.append(f"{where}: unknown class {entry.get('class')!r}")
        ev = entry.get("evidence", "")
        if ev.startswith("docs/") and not (REPO_ROOT / ev.split("#")[0]).is_file():
            defects.append(f"{where}: evidence doc missing: {ev}")
        review_by = entry.get("review_by", "")
        try:
            if date.fromisoformat(review_by) < date.today():
                defects.append(f"{where}: review expired on {review_by}")
        except ValueError:
            defects.append(f"{where}: bad review_by {review_by!r}")
        h = line_hash(entry["file"], int(entry["line"]))
        if h is None:
            defects.append(f"{where}: file/line no longer resolvable")
        elif h != entry.get("code_hash"):
            defects.append(f"{where}: code changed since acceptance (hash drift) — re-review required")

    if defects:
        print(f"BASELINE INVALID — {len(defects)} defect(s):")
        for d in defects:
            print(f"  - {d}")
        return 1
    n = len(base.get("accepted", []))
    print(f"baseline OK: {n} accepted finding(s), all reviews current, all hashes match")
    return 0


def cmd_parse(source: str) -> int:
    text = Path(source).read_text(encoding="utf-8") if source != "-" else sys.stdin.read()
    sites = []
    for m in SITE_RE.finditer(text):
        rule = m.group("rule").strip().rstrip("。.,;；").strip().lower()
        rule = RULE_ALIASES.get(rule, rule)
        sites.append(
            {
                "file": str(Path(m.group("file")).relative_to(REPO_ROOT)),
                "line": int(m.group("line")),
                "sev": m.group("sev"),
                "rule": rule,
            }
        )
    seen, stubs = set(), []
    for s in sites:
        key = (s["file"], s["line"], s["rule"])
        if key in seen:
            continue
        seen.add(key)
        stubs.append(
            {
                "file": s["file"],
                "line": s["line"],
                "rule": s["rule"],
                "severity": s["sev"],
                "code_hash": line_hash(s["file"], s["line"]) or "RESOLVE-MANUALLY",
                "class": "FILL: sanitizer-not-modeled | test-fixture | accepted-risk",
                "rationale": "FILL",
                "evidence": "docs/decisions/2026-10-19-mimosa-gate-policy.md",
                "accepted_by": "operator",
                "accepted_at": date.today().isoformat(),
                "review_by": "FILL (>= accepted_at)",
            }
        )
    json.dump(stubs, sys.stdout, ensure_ascii=False, indent=2)
    print(
        f"\n# {len(stubs)} stub(s); review each, fill class/rationale/review_by, then merge into {BASELINE_PATH.relative_to(REPO_ROOT)}",
        file=sys.stderr,
    )
    return 0


def _match(entry: dict, finding: dict) -> bool:
    f_file = finding.get("file") or finding.get("path") or ""
    f_file = str(f_file)
    if f_file.startswith(str(REPO_ROOT)):
        f_file = str(Path(f_file).relative_to(REPO_ROOT))
    f_line = int(finding.get("line") or 0)
    f_rule = (finding.get("rule") or finding.get("ruleId") or "").lower()
    if entry["file"] != f_file or entry["rule"].lower() != f_rule:
        return False
    f_hash = finding.get("code_hash") or finding.get("codeEvidenceHash")
    if f_hash:
        return f_hash == entry["code_hash"]
    # No hash in the findings payload: fall back to line identity.
    return f_line == int(entry["line"])


def cmd_diff(findings_path: str) -> int:
    payload = json.loads(Path(findings_path).read_text(encoding="utf-8"))
    findings = payload.get("findings", payload) if isinstance(payload, dict) else payload
    base = load_baseline()
    accepted = base.get("accepted", [])
    new = [f for f in findings if not any(_match(e, f) for e in accepted)]
    blocking = [f for f in new if (f.get("severity") or f.get("sev") or "high") in ("high", "medium")]
    print(
        f"{len(findings)} finding(s): {len(findings) - len(new)} baselined, {len(new)} new "
        f"({len(blocking)} new blocking)"
    )
    for f in new:
        print(
            f"  NEW [{f.get('severity') or f.get('sev')}] {f.get('file') or f.get('path')}:"
            f"{f.get('line')} {f.get('rule') or f.get('ruleId')}"
        )
    if blocking:
        print("FAIL: unaccepted blocking findings — fix them or record acceptance first")
        return 1
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {"verify", "parse", "diff"}:
        print(__doc__)
        return 2
    if argv[1] == "verify":
        return cmd_verify()
    if argv[1] == "parse":
        return cmd_parse(argv[2] if len(argv) > 2 else "-")
    return cmd_diff(argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
