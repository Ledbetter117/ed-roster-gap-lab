#!/usr/bin/env python3
"""mutation_gapcheck_r12.py -- planted defects for the increment 1.2 guards. Each mutant reverts one guard in a scratch copy; the
named checks in tests/test_gapcheck_r12.py must then FAIL. D12 is the original timestamp mutant: the clock-independent DET-clock
check must catch it on every interpreter (the 1.1 DET check missed it on Windows + Python 3.12, whose clock ticks every 15.6 ms).
    python3 -B mutation_gapcheck_r12.py <build root> <scratch dir> <out json>
"""
import json, os, shutil, subprocess, sys

ROOT, SCR, OUT = sys.argv[1:4]
F = "detector/gapcheck.py"
M = [
    ("M-R1 parameter validation disabled", '    bad = validate_rules(rules)\n', '    bad = []\n',
     ["R1-h6-max0", "R1-h5-negative", "R1-h1-negative", "R1-h1-policy", "R1-h5-bool-as-text"]),
    ("M-R2 duplicate note removed", '        if n > 1:\n            env["input_notes"].append({"type": "DUPLICATE_ASSIGNMENT"',
     '        if False:\n            env["input_notes"].append({"type": "DUPLICATE_ASSIGNMENT"', ["R2"]),
    ("M-R3 empty roster evaluated again", '    if not roster["dates"] or not shifts:   # R3', '    if False:   # R3', ["R3-no-dates", "R3-no-shifts"]),
    ("M-R4 overlap note removed", '            if b0 < a1:\n', '            if False:\n', ["R4"]),
    ("M-R5 count unit ignored", '        unit = P("H6").get("count_unit") or "calendar_day"', '        unit = "calendar_day"', ["R5", "R5-exceed"]),
    ("M-R6a carry-in findings reported", '        if date in carry:   # R6: a carry-in date is context only\n            return\n', '', ["R6-h5"]),
    ("M-R6b H6 run on a carry-in date not re-reported", 'and not reported and d_tok not in carry:', 'and not reported:', ["R6-h6"]),
    ("M-R7 H8 pairing check disabled", 'if P("H8").get("pairing_required") and pre[sid] not in on:', 'if False:', ["R7-h8"]),
    ("D9b H6 off by one (the 1.1 mutant D9 is void on 1.2: its line was rewritten)", 'if run_len > mx and not reported and',
     'if run_len > mx + 1 and not reported and', ["R5-exceed"]),   # R6-h6 (5 days, max 3) still exceeds max+1; H6-a in test_gapcheck.py also catches it
    ("D12 a timestamp in the output",'    env["run_status"] = "COMPLETED"\n',
     '    env["run_status"] = "COMPLETED"\n    env["generated"] = __import__("time").time_ns()\n', ["DET-clock"]),
]
res = []
for name, old, new, expect in M:
    d = os.path.join(SCR, name.split()[0])
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns("__pycache__"))
    p = os.path.join(d, F)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        res.append({"mutant": name, "void": True, "count": s.count(old)})
        print(f"{name} -> VOID (pattern found {s.count(old)} times)")
        continue
    open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new))
    js = os.path.join(d, "r12.json")
    subprocess.run([sys.executable, "-B", os.path.join(d, "tests", "test_gapcheck_r12.py"), d, "--json", js], capture_output=True)
    failed = sorted(r["id"] for r in json.load(open(js))["results"] if r["result"] == "FAIL") if os.path.exists(js) else ["(no json: crash)"]
    caught = all(e in failed for e in expect)
    res.append({"mutant": name, "caught": caught, "expected": expect, "failed": failed})
    print(f"{name} -> {'CAUGHT' if caught else 'MISSED'} {failed}")
n = sum(1 for r in res if r.get("caught"))
print(f"{n}/{len(M)} caught, {sum(1 for r in res if r.get('void'))} void")
json.dump(res, open(OUT, "w"), indent=1)
sys.exit(0 if n == len(M) else 1)
