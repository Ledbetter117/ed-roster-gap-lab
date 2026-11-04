#!/usr/bin/env python3
"""mutation_measure.py -- planted defects for the track (ii) measurement kit. Each mutant removes one guard; the named
checks in tests/test_measure.py must FAIL. Usage:
    python3 -B mutation_measure.py <build root> <scratch dir> <out json>
"""
import json, os, re, shutil, subprocess, sys

ROOT, SCR, OUT = sys.argv[1:4]
M = [
    ("K1 the label sheet allowed before the seal", 'if not os.path.exists(os.path.join(d, "DETECTOR-SEAL.json")):', 'if False:', ["M2"]),
    ("K2 a re-seal allowed after the sheet was issued", 'if os.path.exists(os.path.join(d, "LABEL-SHEET.json")):', 'if False:', ["M15"]),
    ("K3 labels edited after the lock accepted", 'if h_file(labels_csv) != lock["labels_sha256"]:', 'if False:', ["M6"]),
    ("K4 simulated labels accepted as a result", 'if lock["rater"] != "founder" and not pipeline_test:', 'if False:', ["M4"]),
    ("K5 a changed sealed output accepted", 'if h_file(p) != seal_rec["outputs"][rid]:', 'if False:', ["M10"]),
    ("K6 a changed roster accepted", 'if h_file(os.path.join(d, "rosters", rid + ".json")) != hv:', 'if False:', ["M12"]),
    ("K7 the unsure=exclude policy ignored", 'if unsure == "exclude":', 'if False:', ["M9"]),
    ("K8 the bootstrap resamples units, not rosters",
     'smp = [p for k in (keys[rng.randrange(len(keys))] for _ in keys) for p in by_roster[k]]',
     'smp = (lambda a: [a[rng.randrange(len(a))] for _ in a])([p for k in keys for p in by_roster[k]])', ["M8b"]),
    ("K9 a swapped seal accepted after the lock", 'if h_file(seal_path) != lock["seal_sha256"]:', 'if False:', ["M19"]),
    ("K10 unknown unit ids accepted at the lock", 'if unknown:', 'if False:', ["M18"]),
    ("K11 a lock without an issued sheet accepted",
     'sheet = json.load(open(_need(d, "LABEL-SHEET.json", "label-sheet"), encoding="utf-8"))',
     'sheet = (json.load(open(os.path.join(d, "LABEL-SHEET.json"), encoding="utf-8")) if os.path.exists(os.path.join(d, "LABEL-SHEET.json")) '
     'else {"seal_sha256": h_file(os.path.join(d, "DETECTOR-SEAL.json")), "sheet_sha256": None})', ["M16"]),
    ("K12 a not-evaluated unit scored as no-gap", 'else "not-evaluated" if incomplete or b in skipped else "no-gap"', 'else "no-gap"', ["M20"]),
    ("K13 kappa/sens/spec from invented labels under disagree", 'if unsure == "disagree":   # CR-M6', 'if False:   # CR-M6', ["M21"]),
    ("K14 the facts lose the rest hours", 'rest = f"rest {start - end} h since {pd} {ps}" if start >= end else f"overlaps {pd} {ps}"',
     'rest = "rest unknown"', ["M22"]),
    ("K15 the label sheet leaks the detector findings", '"facts": render(r, date, sh),',
     '"facts": render(r, date, sh) + " | finding: " + json.dumps(json.load(open(os.path.join(d, "SEALED", "detector", rid + ".json")))["findings"]),',
     ["M3"]),
    ("K16 agreement before the lock crashes instead of refusing", 'lock = json.load(open(_need(d, "LABELS-LOCK.json", "lock-labels"), encoding="utf-8"))',
     'lock = json.load(open(os.path.join(d, "LABELS-LOCK.json"), encoding="utf-8"))', ["M17"]),
    ("K17 the generator draws blocks independently again (accidental back-to-backs)",
     'rested = [x for x in ok if last.get(x) != bi - 1]', 'rested = list(ok)', ["M23"]),
    ("K18 a sheet from another set accepted at the lock", 'if sets != {man["set_sha256"][:12]}:', 'if False:', ["M25"]),
]
res = []
for name, old, new, expect in M:
    d = os.path.join(SCR, name.split()[0])
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns("preimages"))
    p = os.path.join(d, "measure", "ii_measure.py")
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        res.append({"mutant": name, "void": True, "anchor_count": s.count(old)}); continue
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    r = subprocess.run([sys.executable, "-B", os.path.join(d, "tests", "test_measure.py"), d], capture_output=True, text=True, timeout=900)
    failed = sorted(set(re.findall(r"^FAIL (\S+)", r.stdout, re.M)))
    res.append({"mutant": name, "expected": expect, "failed": failed, "crashed": "Traceback" in r.stderr,
                "caught": all(x in failed for x in expect)})
    shutil.rmtree(d, ignore_errors=True)
json.dump(res, open(OUT, "w"), indent=1)
for x in res:
    print(x["mutant"], "->", "VOID" if x.get("void") else ("CAUGHT" if x["caught"] else "MISSED"), x.get("failed"), "CRASHED" if x.get("crashed") else "")
print(f"{sum(1 for x in res if x.get('caught'))}/{len(res)} caught, {sum(1 for x in res if x.get('void'))} void")

sys.exit(0 if all(x.get("caught") for x in res) else 1)
