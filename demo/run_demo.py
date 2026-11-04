#!/usr/bin/env python3
"""run_demo.py -- end-to-end SYNTHETIC demonstration of Track (ii) increment 1.2 (ORCA-ED-MAX-PROGRESS-20261030).

PIPELINE TEST - NOT A RESULT. Every rule number is HYPOTHETICAL; the rater is a SIMULATED heuristic, never the founder; the
rosters are generated; nothing here is clinical policy or a study outcome. It shows that the pipeline runs end to end, that it
refuses what it should, and how open founder choices change outputs, so the founder can see consequences before deciding.

Steps: (0) the founder template gives NOT_RUN (no rule is guessed); for each scenario branch: make-set -> seal -> label-sheet ->
SIMULATED labels -> lock-labels -> agreement --pipeline-test under unsure=exclude and unsure=disagree; refusals are exercised.
Usage: python -B run_demo.py <build root> <new scratch dir> <report.md>"""
import csv, hashlib, json, os, subprocess, sys

ROOT, SCR, REPORT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
PY = sys.executable
KIT = os.path.join(ROOT, "measure", "ii_measure.py")
DET = os.path.join(ROOT, "detector", "gapcheck.py")
BASE = {"H1": {"status": "HIGH", "params": {"min_rn_by_band": {"low": 2, "normal": 3, "high": 4, "surge": 4},
                                            "charge_counts_toward_h1": True, "missing_band_policy": "skip"}},
        "H2": {"status": "HIGH", "params": {}}, "H4": {"status": "HIGH", "params": {"allowed_exceptions": []}},
        "H5": {"status": "HIGH", "params": {"min_rest_hours": 12, "boundary_inclusive": True, "day_after_night_forbidden": False}},
        "H6": {"status": "HIGH", "params": {"max_consecutive_shifts": 3}},
        "H9": {"status": "HIGH", "params": {"not_separate_places": []}}}
BRANCHES = {
    "A-inclusive-calendar-day": {},
    "B-exclusive-shift-count": {"H5": {"boundary_inclusive": False}, "H6": {"count_unit": "shift"}},
}
log = []


def run(args, cwd=None, expect_fail=False):
    p = subprocess.run([PY, "-B"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout + p.stderr).strip()
    log.append({"cmd": " ".join(os.path.basename(a) if os.path.isabs(a) else a for a in args), "exit": p.returncode, "out": out[-600:]})
    if (p.returncode != 0) != expect_fail:
        raise SystemExit("unexpected exit %s for %s:\n%s" % (p.returncode, args, out[-1500:]))
    return out


def simulated_labels(sheet, out_csv, seed):
    """SIMULATED HEURISTIC RATER (never the founder): 'gap' when the facts show no charge nurse or a 0 h rest; 'unsure' for about
    1 in 12 units chosen by a seeded hash; otherwise 'no-gap'."""
    rows = list(csv.DictReader(open(sheet, encoding="utf-8", newline="")))
    col = [k for k in rows[0] if k.startswith("label")][0]
    counts = {"gap": 0, "no-gap": 0, "unsure": 0}
    for r in rows:
        f = r["facts"]
        h = int(hashlib.sha256((seed + r["unit_id"]).encode()).hexdigest(), 16)
        lab = "unsure" if h % 12 == 0 else ("gap" if "(charge)" not in f or "rest 0 h" in f else "no-gap")
        r[col] = lab
        counts[lab] += 1
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return counts


def main():
    if os.path.exists(SCR):
        raise SystemExit("HALT: scratch exists")
    os.makedirs(SCR)
    results = {}
    tmpl = run([DET, "--rules", os.path.join(ROOT, "rules", "RULES.founder-template.json"), "--input",
                os.path.join(ROOT, "fixtures", "LEGAL-PC-01.json")], expect_fail=True)
    results["founder_template"] = json.loads(tmpl)["run_status"]
    for name, over in BRANCHES.items():
        d = os.path.join(SCR, name)
        os.makedirs(d)
        rules = {"source": "HYPOTHETICAL SCENARIO BRANCH %s (run_demo.py). Example values only; not founder rules." % name,
                 "rules": json.loads(json.dumps(BASE))}
        for rid, p in over.items():
            rules["rules"][rid]["params"].update(p)
        rp = os.path.join(d, "RULES.hypothetical.json")
        json.dump(rules, open(rp, "w", encoding="utf-8", newline="\n"), indent=1)
        st = os.path.join(d, "set")
        run([KIT, "make-set", "--out", st, "--n", "12", "--days", "7", "--seed", "demo-seed-1030", "--unit", "both"])
        run([KIT, "seal", "--set", st, "--rules", rp])
        run([KIT, "label-sheet", "--set", st, "--out", os.path.join(d, "SHEET.csv")])
        run([KIT, "agreement", "--set", st, "--labels", os.path.join(d, "SHEET.csv"), "--unsure", "exclude"], expect_fail=True)
        counts = simulated_labels(os.path.join(d, "SHEET.csv"), os.path.join(d, "LABELS.csv"), "sim-demo")   # same labels in every branch
        run([KIT, "lock-labels", "--set", st, "--labels", os.path.join(d, "LABELS.csv"), "--rater", "SIMULATED"])
        run([KIT, "agreement", "--set", st, "--labels", os.path.join(d, "LABELS.csv"), "--unsure", "exclude"], expect_fail=True)
        res = {"labels": counts}
        for pol in ("exclude", "disagree"):
            out = run([KIT, "agreement", "--set", st, "--labels", os.path.join(d, "LABELS.csv"), "--unsure", pol, "--pipeline-test"])
            body = out[out.index("{"):]
            try:
                res[pol] = json.loads(body)
            except ValueError:
                res[pol] = __import__("ast").literal_eval(body)
        results[name] = res
    md = ["# Track (ii) increment 1.2 - end-to-end SYNTHETIC demonstration", "",
          "**PIPELINE TEST - NOT A RESULT.** Hypothetical rules, generated rosters (seed `demo-seed-1030`, 12 rosters x 7 days x 2 "
          "shifts = 168 units), a SIMULATED heuristic rater. These numbers show mechanics and how open choices move outputs; they say "
          "nothing about real staffing, the founder's judgment or the detector's validity.", "",
          "- Founder template (every rule LOW): `%s` - the detector guesses no rule." % results["founder_template"], "",
          "| Branch | Choice under test | unsure policy | n scored | agreement | 95% roster-bootstrap CI | kappa | detector-only gaps |",
          "|---|---|---|---|---|---|---|---|"]
    for name in BRANCHES:
        for pol in ("exclude", "disagree"):
            r = results[name][pol]
            ci = r.get("agreement_95ci_roster_bootstrap") or [None, None]
            md.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, json.dumps(BRANCHES[name]) if BRANCHES[name] else "H5 inclusive, H6 calendar day (1.1 defaults)", pol, r.get("n"),
                round(r["agreement"], 3) if r.get("agreement") is not None else None,
                "%.3f-%.3f" % tuple(ci) if None not in ci else "n/a", round(r["kappa"], 3) if r.get("kappa") is not None else None,
                r.get("detector_only")))
    md += ["", "Simulated label counts: " + "; ".join("%s %s" % (k, v["labels"]) for k, v in results.items() if k != "founder_template"), "",
           "Refusals exercised: agreement before the lock; agreement on a SIMULATED rater without --pipeline-test; the founder template "
           "returns NOT_RUN (exit 3).", "", "## Command log", ""]
    md += ["- `%s` -> exit %s" % (l["cmd"], l["exit"]) for l in log]
    open(REPORT, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
    json.dump({"results": results, "log": log}, open(os.path.splitext(REPORT)[0] + ".json", "w", encoding="utf-8"), indent=1)
    print("\n".join(md[:16]))


if __name__ == "__main__":
    main()
