#!/usr/bin/env python3
"""
Mechanical checks that help a judge score suite v1.2 responses. They don't
produce scores; they report facts (word counts, test-case pass/fail, JSON
validity) so the judge doesn't have to trust the model's own claims.

    python auto_checks.py results/pending_nvidia_run19.json
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROMAN_VALID = {"I": 1, "IV": 4, "IX": 9, "XIV": 14, "XL": 40, "XCIX": 99, "CDXLIV": 444,
               "MCMXCIV": 1994, "MMMCMXCIX": 3999}
ROMAN_INVALID = ["", "IIII", "VV", "IIV", "IC", "IL", "XM", "VX", "XCX", "CMC", "MMMM",
                 "iv", "XIV ", "ABC"]
CPM_KEY = {"project_days": 20, "critical_path": ["A", "B", "E", "H", "I"],
           "slack": {"A": 0, "B": 0, "C": 2, "D": 2, "E": 0, "F": 2, "G": 4, "H": 0, "I": 0}}


def check_poem(text):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    out = [f"non-empty lines: {len(lines)}"]
    for i, l in enumerate(lines, 1):
        words = l.split()
        out.append(f"  L{i}: first={l[:1]!r} words={len(words)} has_e={'e' in l.lower()} "
                   f"last={re.sub(r'[^A-Za-z-]', '', words[-1]) if words else ''!r} | {l}")
    return "\n".join(out)


def check_roman(text):
    m = re.search(r"```(?:python|py)?\n(.*?)```", text, re.DOTALL)
    if not m:
        return "no python code block"
    harness = m.group(1) + f"""

_valid = {ROMAN_VALID!r}
_invalid = {ROMAN_INVALID!r}
for s, v in _valid.items():
    try:
        r = roman_to_int(s)
        print(("OK  " if r == v else "BAD ") + f"valid {{s!r}} -> {{r}}")
    except Exception as e:
        print(f"BAD valid {{s!r}} raised {{type(e).__name__}}")
for s in _invalid:
    try:
        r = roman_to_int(s)
        print(f"BAD invalid {{s!r}} accepted -> {{r}}")
    except ValueError:
        print(f"OK  invalid {{s!r}} rejected")
    except Exception as e:
        print(f"BAD invalid {{s!r}} raised {{type(e).__name__}} (not ValueError)")
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(harness)
    try:
        p = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return "timed out"
    lines = (p.stdout + p.stderr).strip().splitlines()
    bad = [l for l in lines if not l.startswith("OK")]
    return f"{len(lines) - len(bad)} OK, {len(bad)} not OK\n" + "\n".join("  " + b for b in bad)


def check_cpm(text):
    stripped = text.strip()
    fenced = stripped.startswith("```")
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return f"not valid JSON ({e}); fenced={fenced}"
    diffs = []
    for k in ("project_days", "critical_path"):
        if data.get(k) != CPM_KEY[k]:
            diffs.append(f"{k}={data.get(k)!r}")
    for t, v in CPM_KEY["slack"].items():
        if (data.get("slack") or {}).get(t) != v:
            diffs.append(f"slack[{t}]={(data.get('slack') or {}).get(t)!r} (want {v})")
    return f"valid JSON, raw-only={not fenced and body == stripped}; " + ("all correct" if not diffs else "; ".join(diffs))


CHECKS = {1: check_poem, 2: check_roman, 8: check_cpm}


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    for r in data["responses"]:
        if r["number"] in CHECKS and r["response"]:
            print(f"--- [{r['number']}] {r['name']}")
            print(CHECKS[r["number"]](r["response"]))


if __name__ == "__main__":
    main()
