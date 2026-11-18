#!/usr/bin/env python3
"""
Re-check the answer keys in suite_v1.2.md by recomputing them from the
prompt text itself. Run after editing any v1.2 prompt.

    python verify_suite_v1_2.py
"""
import contextlib
import io
import ipaddress
import itertools
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import evalcore as ec

SUITE = ec.EVAL_DIR / "suite_v1.2.md"
failures = []


def check(name, got, expected):
    ok = got == expected
    print(f"{'OK  ' if ok else 'FAIL'} {name}: {got!r}" + ("" if ok else f" (key says {expected!r})"))
    if not ok:
        failures.append(name)


def code_block(text: str) -> str:
    return re.search(r'```(?:python)?\n(.*?)```', text, re.DOTALL).group(1)


def roman_reference(s: str) -> int:
    if not re.fullmatch(r'M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', s) or not s:
        raise ValueError(s)
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for a, b in zip(s, s[1:] + " "):
        total += -vals[a] if b != " " and vals[a] < vals[b] else vals[a]
    return total


def main():
    p = {t.number: t for t in ec.parse_suite(SUITE)}
    check("prompt count", len(p), 8)

    # 2. Roman numerals: valid/invalid lists in the scoring guide
    guide = p[2].scoring_guide
    valid_line = re.search(r'Must return: (.*)', guide).group(1)
    for s, n in re.findall(r'"([^"]*)"→(\d+)', valid_line):
        check(f"#2 roman {s}", roman_reference(s), int(n))
    invalid_line = re.search(r'Must raise ValueError for: (.*)', guide).group(1)
    for s in re.findall(r'"([^"]*)"', invalid_line):
        try:
            roman_reference(s)
            check(f"#2 rejects {s!r}", "accepted", "ValueError")
        except (ValueError, KeyError):
            pass
    print("OK   #2 all invalid cases rejected by reference implementation")

    # 3. Logic grid: brute force with the 9 clues
    people = ["Ana", "Ben", "Cy", "Dee"]
    sols = []
    for seats in itertools.permutations(range(1, 5)):
        s = dict(zip(people, seats))
        for pets in itertools.permutations(["cat", "dog", "fish", "bird"]):
            pt = dict(zip(people, pets))
            for drinks in itertools.permutations(["tea", "coffee", "juice", "milk"]):
                d = dict(zip(people, drinks))
                who = lambda attr, v: next(x for x in people if attr[x] == v)
                if (s[who(pt, "dog")] == s[who(d, "tea")] + 1 and s["Ana"] not in (1, 4)
                        and abs(s["Ben"] - s[who(pt, "fish")]) == 2 and d["Cy"] == "milk"
                        and s[who(d, "coffee")] == 4 and pt["Dee"] not in ("cat", "dog")
                        and s[who(pt, "bird")] < s[who(pt, "cat")] and d["Ana"] != "juice"
                        and abs(s["Cy"] - s["Dee"]) != 1):
                    sols.append(sorted(f"{n}: seat {s[n]}, {pt[n]}, {d[n]}" for n in people))
    check("#3 number of solutions", len(sols), 1)
    key = re.findall(r'`(\w+: seat \d, \w+, \w+)`', p[3].scoring_guide)
    check("#3 solution", sols[0] if sols else None, sorted(key))

    # 4. Log analysis
    ten = ipaddress.ip_network("10.0.0.0/8")
    counts = Counter()
    for line in code_block(p[4].prompt).splitlines():
        t, ev, user, ip = line.split()
        if "02:00:00" <= t <= "03:59:59" and ev == "LOGIN_FAIL" and ipaddress.ip_address(ip[3:]) not in ten:
            counts[user[5:]] += 1
    (top, n), (_, second) = counts.most_common(2)
    check("#4 top user is unique", n > second, True)
    check("#4 answer", f"top: {top} {n} / total: {sum(counts.values())}",
          "top: {} {} / total: {}".format(*re.search(r'`top: (\w+) (\d+)` and `total: (\d+)`', p[4].scoring_guide).groups()))

    # 5. Tank: phases from the prompt (hard-coded; edit together with the prompt)
    level, rate_a, rate_b, rate_c = Fraction(300), 200, 300, -150
    phases = [(9, 10, rate_a + rate_b), (10, Fraction(21, 2), rate_a + rate_b + rate_c), (Fraction(21, 2), 99, rate_a + rate_c)]
    full_at = None
    for start, end, rate in phases:
        if level + rate * (end - start) >= 1200:
            full_at = start + (1200 - level) / rate
            break
        level += rate * (end - start)
    hh, mm = int(full_at), round((full_at - int(full_at)) * 60)
    check("#5 full at", f"Full at {hh:02d}:{mm:02d}", re.search(r'`(Full at \d\d:\d\d)`', p[5].scoring_guide).group(1))

    # 6. Exact output
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(code_block(p[6].prompt), {})
    check("#6 output", out.getvalue().strip(), re.search(r'Exact output: `([^`]*)`', p[6].scoring_guide).group(1))

    # 7. Debugging: buggy result and caller-list mutation
    ns = {}
    exec(code_block(p[7].prompt), ns)
    caller = [2, 3]
    check("#7 buggy result", ns["total_scaled"]([1, 2, 3], caller), [14, 0, 0])
    check("#7 buggy mutates caller list", caller, [2, 3, 1])
    fixed = (code_block(p[7].prompt)
             .replace("def make_multipliers(factors=[]):", "def make_multipliers(factors=None):")
             .replace("factors.append(1)", "factors = list(factors or []) + [1]")
             .replace("lambda x: x * f", "lambda x, f=f: x * f")
             .replace("squared = (v * v for v in values)", "squared = [v * v for v in values]"))
    ns = {}
    exec(fixed, ns)
    caller = [2, 3]
    check("#7 fixed result", ns["total_scaled"]([1, 2, 3], caller), [28, 42, 14])
    check("#7 fixed leaves caller list alone", caller, [2, 3])

    # 8. Critical path from the task line in the prompt
    tasks = {}
    for name, dur, deps in re.findall(r'([A-I]) (\d+) \(([^)]*)\)', p[8].prompt):
        tasks[name] = (int(dur), [] if deps == "none" else [x.strip() for x in deps.split(",")])
    order = list(tasks)
    es, ef = {}, {}
    for k in order:
        es[k] = max((ef[x] for x in tasks[k][1]), default=0)
        ef[k] = es[k] + tasks[k][0]
    end = max(ef.values())
    ls = {}
    for k in reversed(order):
        succ = [s for s in order if k in tasks[s][1]]
        ls[k] = min((ls[s] for s in succ), default=end) - tasks[k][0]
    slack = {k: ls[k] - es[k] for k in order}
    path = [k for k in order if slack[k] == 0]
    key = re.search(r'Correct answer: `(\{.*\})`', p[8].scoring_guide).group(1)
    import json
    key = json.loads(key)
    check("#8 project_days", end, key["project_days"])
    check("#8 critical_path", path, key["critical_path"])
    check("#8 slack", slack, key["slack"])

    print(f"\n{'All answer keys verified.' if not failures else f'{len(failures)} check(s) FAILED: {failures}'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
