#!/usr/bin/env python3
"""mutation_gapcheck.py -- planted defects for the track (ii) detector. D1 is the brief's required control: an H2 check
that always passes must make the illegal positive control FAIL. Usage:
    python3 -B mutation_gapcheck.py <build root> <scratch dir> <out json>
"""
import json, os, re, shutil, subprocess, sys

ROOT, SCR, OUT = sys.argv[1:4]
M = [
    ("D1 an H2 check that always passes (brief §4 control)", 'if not any(x in charge for x in sids):', 'if False:', ["PC-2", "A3-H2"]),
    ("D2 no input reported as an empty COMPLETED", 'env.update(run_status="NOT_RUN", reason="no input")',
     'env.update(run_status="COMPLETED", reason="no input")', ["PC-3"]),
    ("D3 LOW lines treated as ratified", 'RATIFIED = {"MED", "HIGH"}', 'RATIFIED = {"MED", "HIGH", "LOW"}', ["T-1"]),
    ("D4 the inclusive/exclusive boundary ignored", '(rest == p["min_rest_hours"] and not p["boundary_inclusive"])', 'False', ["A1"]),
    ("D5 a missing band guessed as 'normal'", '            if b not in BANDS:\n                pol = p["missing_band_policy"]',
     '            if b not in BANDS:\n                pol = "normal"', ["A2-missing", "A2-unknown"]),
    ("D6 the synthetic-only fence removed", 'if (r.get("provenance") or {}).get("synthetic") is not True:', 'if False:', ["F1-not-synthetic"]),
    ("D7 H4 exceptions ignored", 'and a.get("exception") not in allowed:', ':', ["H4-b"]),
    ("D8 the UNSATISFIABLE note removed", 'if charge and all((c, d, s) in unavail for c in charge):', 'if False:', ["A3-H2", "A3-H4"]),
    ("D10 H9 ignore list ignored", 'if a.get("place") not in ignore:', 'if True:', ["H9-b"]),
    ("D11 the charge-counting choice ignored", '(1 if (not p["charge_counts_toward_h1"] and any(x in charge for x in rns)) else 0)', '0', ["H1-b"]),
    # colour review 2026-10-30 (CR-T1..CR-T3): each fix must have a check that can fail
    ("D13 the staff-token digit cap removed", r're.compile(r"^S\d{2,3}$")', r're.compile(r"^S\d{2,}$")', ["F1-long-staff-id"]),
    ("D14 the date-token digit cap removed", r're.compile(r"^D\d{2,3}$")', r're.compile(r"^D\d{2,}$")', ["F1-long-date"]),
    ("D15 a missing named input reported as no input", 'roster = {"__missing__": __import__("os").path.basename(a.input)}', 'roster = None', ["CLI"]),
    ("D16 the no-charge-staff note removed", 'if runnable["H2"] and not charge:', 'if False:', ["U-1"]),
]
res = []
for name, old, new, expect in M:
    d = os.path.join(SCR, name.split()[0])
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(ROOT, d)
    p = os.path.join(d, "detector", "gapcheck.py")
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        res.append({"mutant": name, "void": True}); continue
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    r = subprocess.run([sys.executable, "-B", os.path.join(d, "tests", "test_gapcheck.py"), d], capture_output=True, text=True, timeout=300)
    failed = sorted(set(re.findall(r"^FAIL (\S+)", r.stdout, re.M)))
    res.append({"mutant": name, "expected": expect, "failed": failed, "caught": all(x in failed for x in expect)})
    shutil.rmtree(d, ignore_errors=True)
json.dump(res, open(OUT, "w"), indent=1)
for x in res:
    print(x["mutant"], "->", "VOID" if x.get("void") else ("CAUGHT" if x["caught"] else "MISSED"), x.get("failed"))
print(f"{sum(1 for x in res if x.get('caught'))}/{len(res)} caught, {sum(1 for x in res if x.get('void'))} void")

sys.exit(0 if all(x.get("caught") for x in res) else 1)
