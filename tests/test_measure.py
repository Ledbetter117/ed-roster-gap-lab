#!/usr/bin/env python3
"""test_measure.py -- pipeline tests for the II-8b measurement kit, with SIMULATED raters only (never founder labels).
    python3 -B test_measure.py <build root> [--json out.json]
"""
import csv, json, os, shutil, sys, tempfile

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
sys.path.insert(0, os.path.join(ROOT, "measure"))
sys.dont_write_bytecode = True
import ii_measure as M  # noqa: E402

TMP = tempfile.mkdtemp(prefix="ii-measure-")
RES = []
RULES = os.path.join(ROOT, "rules", "RULES.test-H2-H4.json")


def check(cid, name, ok, observed):
    RES.append({"id": cid, "check": name, "result": "PASS" if ok else "FAIL", "observed": observed})
    print(f"{'PASS' if ok else 'FAIL'} {cid} {name}  [{json.dumps(observed)[:200]}]")


def refused(fn):
    """The refusal message, None if fn succeeded, or 'CRASH ...' (a crash is not a clean refusal and fails the check)."""
    try:
        fn(); return None
    except SystemExit as ex:
        return str(ex)
    except Exception as ex:
        return f"CRASH {type(ex).__name__}: {ex}"


def fill(sheet, out, labeller):
    with open(sheet, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["label (gap / no-gap / unsure)"] = labeller(r)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return rows


S = os.path.join(TMP, "set")
m1 = M.make_set(S, 6, 3, "test", "both")
m2 = M.make_set(os.path.join(TMP, "same"), 6, 3, "test", "both")
m3 = M.make_set(os.path.join(TMP, "other"), 6, 3, "other", "both")
check("M1", "the roster set is frozen and reproducible: same seed, same set hash; another seed differs",
      m1["set_sha256"] == m2["set_sha256"] != m3["set_sha256"] and m1["n_units"] == 36, {"n_units": m1["n_units"]})
early = os.path.join(TMP, "early"); M.make_set(early, 2, 2, "early", "nights")
check("M2", "a label sheet cannot exist before the detector outputs are sealed (blinding order)",
      "seal the detector outputs" in (refused(lambda: M.label_sheet(early, os.path.join(TMP, "x.csv"))) or ""), {})
seal = M.seal(S, RULES)
sheet = os.path.join(TMP, "sheet.csv"); n = M.label_sheet(S, sheet)
txt = open(sheet, encoding="utf-8").read()
check("M3", "the label sheet is blinded: no detector output, rule ids or generator intent appear in it",
      n == 36 and not any(w in txt for w in ("finding", "H2", "H4", "charge removed", "one short", "double booking", "back-to-back",
                                             "no rested charge", "generator target", "UNSATISFIABLE")),
      {"units": n})
det = M.verdicts(S, M.load_set(S), seal)
agree = os.path.join(TMP, "agree.csv"); fill(sheet, agree, lambda r: det[r["unit_id"]])
check("M4", "simulated labels are refused for a real result", "only founder labels" in (refused(lambda: (M.lock_labels(S, agree, "SIMULATED"),
      M.agreement(S, agree, "exclude", pipeline_test=False, reps=200))) or ""), {})
res = M.agreement(S, agree, "exclude", pipeline_test=True, reps=500)
check("M5", "pipeline test, a rater who always agrees: agreement 1.0, labelled PIPELINE TEST",
      res["agreement"] == 1.0 and res["label"].startswith("PIPELINE TEST") and res["n"] == 36, {k: res[k] for k in ("agreement", "kappa", "n", "label")})
ed = os.path.join(TMP, "edited.csv"); shutil.copyfile(agree, ed)
with open(ed, "a", encoding="utf-8") as f:
    f.write("\n")
shutil.copyfile(ed, agree)
check("M6", "labels edited after the lock are refused (recorded, not scored)",
      "differs from the locked labels" in (refused(lambda: M.agreement(S, agree, "exclude", pipeline_test=True, reps=200)) or ""), {})
check("M7", "sealing again after the labels are locked is refused", "already locked" in (refused(lambda: M.seal(S, RULES)) or ""), {})

S2 = os.path.join(TMP, "set2"); M.make_set(S2, 6, 3, "test", "both"); M.seal(S2, RULES); sh2 = os.path.join(TMP, "sheet2.csv"); M.label_sheet(S2, sh2)
det2 = M.verdicts(S2, M.load_set(S2), json.load(open(os.path.join(S2, "DETECTOR-SEAL.json"))))
flip_ids = sorted(det2)[:6]
lab2 = os.path.join(TMP, "lab2.csv")
fill(sh2, lab2, lambda r: ("no-gap" if det2[r["unit_id"]] == "gap" else "gap") if r["unit_id"] in flip_ids else det2[r["unit_id"]])
M.lock_labels(S2, lab2, "SIMULATED")
r2 = M.agreement(S2, lab2, "exclude", pipeline_test=True, reps=500)
check("M8", "pipeline test, 6 of 36 labels flipped: agreement 30/36, with a roster-clustered interval that contains it",
      abs(r2["agreement"] - 30 / 36) < 1e-12 and r2["agreement_95ci_roster_bootstrap"][0] <= r2["agreement"] <= r2["agreement_95ci_roster_bootstrap"][1],
      {k: r2[k] for k in ("agreement", "agreement_95ci_roster_bootstrap", "kappa")})

S3 = os.path.join(TMP, "set3"); M.make_set(S3, 6, 3, "test", "both"); M.seal(S3, RULES); sh3 = os.path.join(TMP, "sheet3.csv"); M.label_sheet(S3, sh3)
det3 = M.verdicts(S3, M.load_set(S3), json.load(open(os.path.join(S3, "DETECTOR-SEAL.json"))))
uns = sorted(det3)[:3]
lab3 = os.path.join(TMP, "lab3.csv"); fill(sh3, lab3, lambda r: "unsure" if r["unit_id"] in uns else det3[r["unit_id"]])
M.lock_labels(S3, lab3, "SIMULATED")
ex = M.agreement(S3, lab3, "exclude", pipeline_test=True, reps=200); dis = M.agreement(S3, lab3, "disagree", pipeline_test=True, reps=200)
check("M9", "'unsure' policy is explicit: exclude -> n 33, agreement 1.0; disagree -> n 36, agreement 33/36",
      ex["n"] == 33 and ex["agreement"] == 1.0 and dis["n"] == 36 and abs(dis["agreement"] - 33 / 36) < 1e-12,
      {"exclude": [ex["n"], ex["agreement"]], "disagree": [dis["n"], dis["agreement"]]})
first = sorted(json.load(open(os.path.join(S3, "DETECTOR-SEAL.json")))["outputs"])[0]
p = os.path.join(S3, "SEALED", "detector", first + ".json")
open(p, "a", encoding="utf-8").write(" ")
check("M10", "a sealed detector output changed after sealing is refused",
      "changed after sealing" in (refused(lambda: M.agreement(S3, lab3, "exclude", pipeline_test=True, reps=200)) or ""), {})
S4 = os.path.join(TMP, "set4"); M.make_set(S4, 2, 2, "test4", "nights"); M.seal(S4, RULES); sh4 = os.path.join(TMP, "sheet4.csv"); M.label_sheet(S4, sh4)
lab4 = os.path.join(TMP, "lab4.csv"); fill(sh4, lab4, lambda r: "")
check("M11", "locking with an unlabelled unit is refused", "unlabelled" in (refused(lambda: M.lock_labels(S4, lab4, "founder")) or ""), {})
rp = os.path.join(S4, "rosters", "R001.json"); open(rp, "a", encoding="utf-8").write(" ")
check("M12", "a roster changed after the set was frozen is refused", "changed after the set was frozen" in (refused(lambda: M.load_set(S4)) or ""), {})
tmpl = os.path.join(ROOT, "rules", "RULES.founder-template.json")
S5 = os.path.join(TMP, "set5"); M.make_set(S5, 2, 2, "test5", "nights"); M.seal(S5, tmpl)
check("M13", "with the unratified founder template the detector does not run, so no verdict can be scored",
      "did not run" in (refused(lambda: M.verdicts(S5, M.load_set(S5), json.load(open(os.path.join(S5, "DETECTOR-SEAL.json"))))) or ""), {})
check("M8b", "the interval is clustered by roster: with all 6 disagreements in one roster its lower bound is <= 0.6 "
      "(a unit-level bootstrap would give about 0.7)", r2["agreement_95ci_roster_bootstrap"][0] <= 0.6, r2["agreement_95ci_roster_bootstrap"])

# ---- colour review 2026-10-30: CR-M1..CR-M7 (each check failed on the pre-review kit; see review/)
S6 = os.path.join(TMP, "set6"); M.make_set(S6, 4, 2, "t6", "both"); M.seal(S6, RULES); M.label_sheet(S6, os.path.join(TMP, "sheet6.csv"))
check("M15", "sealing again after the label sheet was issued (before any lock) is refused",
      "already issued" in (refused(lambda: M.seal(S6, os.path.join(ROOT, "rules", "RULES.test-H2-only.json"))) or ""), {})
S7 = os.path.join(TMP, "set7"); M.make_set(S7, 4, 2, "t7", "both"); M.seal(S7, RULES)
hand = os.path.join(TMP, "hand7.csv")
with open(hand, "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f); wr.writerow(["unit_id", "label (gap / no-gap / unsure)"])
    wr.writerows([[f"{a}/{b}/{c}", "no-gap"] for a, b, c in M.units_of(M.load_set(S7), S7)])
check("M16", "a lock with no issued label sheet is refused", "LABEL-SHEET.json is missing" in (refused(lambda: M.lock_labels(S7, hand, "SIMULATED")) or ""), {})
check("M17", "agreement before the lock is refused with the next step named, not a traceback",
      "run lock-labels first" in (refused(lambda: M.agreement(S7, hand, "exclude", pipeline_test=True, reps=50)) or ""), {})
S8 = os.path.join(TMP, "set8"); M.make_set(S8, 4, 2, "t8", "both"); M.seal(S8, RULES); sh8 = os.path.join(TMP, "sheet8.csv"); M.label_sheet(S8, sh8)
lab8 = os.path.join(TMP, "lab8.csv"); rows8 = fill(sh8, lab8, lambda r: "no-gap")
with open(lab8, "a", newline="", encoding="utf-8") as f:
    csv.DictWriter(f, fieldnames=list(rows8[0])).writerow(dict(rows8[0], unit_id="R999/D01/DAY", roster="R999"))
check("M18", "a labels file naming a unit that is not in the set is refused at the lock",
      "not in this set" in (refused(lambda: M.lock_labels(S8, lab8, "SIMULATED")) or ""), {})
S9 = os.path.join(TMP, "set9"); M.make_set(S9, 4, 2, "t9", "both"); M.seal(S9, RULES); sh9 = os.path.join(TMP, "sheet9.csv"); M.label_sheet(S9, sh9)
det9 = M.verdicts(S9, M.load_set(S9), json.load(open(os.path.join(S9, "DETECTOR-SEAL.json"))))
lab9 = os.path.join(TMP, "lab9.csv"); fill(sh9, lab9, lambda r: det9[r["unit_id"]]); M.lock_labels(S9, lab9, "SIMULATED")
alt = os.path.join(TMP, "alt9"); os.makedirs(os.path.join(alt, "SEALED"))
shutil.copytree(os.path.join(S9, "rosters"), os.path.join(alt, "rosters"))
for n_ in ("SET-MANIFEST.json", os.path.join("SEALED", "generator-intent.json")):
    shutil.copyfile(os.path.join(S9, n_), os.path.join(alt, n_))
M.seal(alt, os.path.join(ROOT, "rules", "RULES.test-H2-only.json"))
for f_ in os.listdir(os.path.join(alt, "SEALED", "detector")):
    shutil.copyfile(os.path.join(alt, "SEALED", "detector", f_), os.path.join(S9, "SEALED", "detector", f_))
shutil.copyfile(os.path.join(alt, "DETECTOR-SEAL.json"), os.path.join(S9, "DETECTOR-SEAL.json"))
check("M19", "a consistent swap of the seal and its outputs after the lock is refused",
      "differs from the seal recorded at the lock" in (refused(lambda: M.agreement(S9, lab9, "exclude", pipeline_test=True, reps=50)) or ""), {})
h1 = json.load(open(os.path.join(ROOT, "rules", "RULES.test-H1-H2-skip.json"), encoding="utf-8"))
h1["rules"]["H1"]["params"]["min_rn_by_band"]["surge"] = None
h1["source"] = "TEST-ONLY: HYPOTHETICAL band minimums with surge unset"
rp = os.path.join(TMP, "RULES.h1-surge-unset.json"); json.dump(h1, open(rp, "w", encoding="utf-8"))
S10 = os.path.join(TMP, "set10"); M.make_set(S10, 10, 3, "probe-r6", "both"); M.seal(S10, rp); sh10 = os.path.join(TMP, "sheet10.csv"); M.label_sheet(S10, sh10)
det10 = M.verdicts(S10, M.load_set(S10), json.load(open(os.path.join(S10, "DETECTOR-SEAL.json"))))
ne = sorted(u for u, x in det10.items() if x == "not-evaluated")
lab10 = os.path.join(TMP, "lab10.csv"); fill(sh10, lab10, lambda r: "no-gap"); M.lock_labels(S10, lab10, "SIMULATED")
r10 = M.agreement(S10, lab10, "exclude", pipeline_test=True, reps=50)
check("M20", "a unit where a ratified rule was skipped and nothing fired is 'not-evaluated' and is not scored",
      len(ne) >= 1 and r10["not_evaluated_excluded"] == len(ne) and r10["n"] == len(det10) - len(ne), {"not_evaluated": ne, "n": r10["n"]})
S11 = os.path.join(TMP, "set11"); M.make_set(S11, 10, 3, "probe-r8", "both"); M.seal(S11, RULES); sh11 = os.path.join(TMP, "sheet11.csv"); M.label_sheet(S11, sh11)
det11 = M.verdicts(S11, M.load_set(S11), json.load(open(os.path.join(S11, "DETECTOR-SEAL.json"))))
g11 = sorted(u for u, x in det11.items() if x == "gap")[:3]
lab11 = os.path.join(TMP, "lab11.csv"); fill(sh11, lab11, lambda r: "unsure" if r["unit_id"] in g11 else det11[r["unit_id"]]); M.lock_labels(S11, lab11, "SIMULATED")
dis11 = M.agreement(S11, lab11, "disagree", pipeline_test=True, reps=50)
check("M21", "--unsure disagree: agreement counts the unsure units against the detector, but sensitivity and specificity use only "
      "the labels given (here both 1.0)", len(g11) == 3 and abs(dis11["agreement"] - (len(det11) - 3) / len(det11)) < 1e-12
      and dis11["detector_sensitivity_vs_rater"] == 1.0 and dis11["detector_specificity_vs_rater"] == 1.0,
      {k: dis11[k] for k in ("agreement", "detector_sensitivity_vs_rater", "detector_specificity_vs_rater")})
dbl = {"staff": [{"staff_id": "S01", "role": "RN", "qualifications": ["charge"]}, {"staff_id": "S02", "role": "RN", "qualifications": []}],
       "shifts": [{"shift": "DAY", "start_hour": 7, "end_hour": 19}, {"shift": "NIGHT", "start_hour": 19, "end_hour": 7}], "dates": ["D01", "D02"],
       "assignments": [{"staff_id": "S01", "date": "D01", "shift": "DAY", "place": "ED"}, {"staff_id": "S01", "date": "D01", "shift": "NIGHT", "place": "ED"},
                       {"staff_id": "S02", "date": "D01", "shift": "NIGHT", "place": "ED"}, {"staff_id": "S02", "date": "D02", "shift": "DAY", "place": "ED"}],
       "availability": [], "context": [{"date": "D01", "shift": "NIGHT", "census_band": "normal"}]}
fn, fd = M.render(dbl, "D01", "NIGHT"), M.render(dbl, "D02", "DAY")
check("M22", "the facts show each nurse's rest and run: a DAY-then-NIGHT double shows 0 h; a NIGHT then DAY shows 0 h and day 2",
      "S01 (charge) @ ED, rest 0 h since D01 DAY, day 1 in a row" in fn and "S02 @ ED, first shift in the roster" in fn
      and "S02 @ ED, rest 0 h since D01 NIGHT, day 2 in a row" in fd, {"D01 NIGHT": fn, "D02 DAY": fd})

S12 = os.path.join(TMP, "set12"); man12 = M.make_set(S12, 20, 7, "t12", "both")
b2b, deliberate = 0, 0
intent12 = json.load(open(os.path.join(S12, "SEALED", "generator-intent.json")))
for rid in man12["rosters"]:
    r = json.load(open(os.path.join(S12, "rosters", rid + ".json")))
    order = [(d, s["shift"]) for d in r["dates"] for s in r["shifts"]]
    who = {b: {a["staff_id"] for a in r["assignments"] if (a["date"], a["shift"]) == b} for b in order}
    for i in range(1, len(order)):
        if who[order[i]] & who[order[i - 1]]:
            b2b += 1
            deliberate += any(e["date"] == order[i][0] and e["shift"] == order[i][1] and "back-to-back shift" in e["events"] for e in intent12[rid])
check("M23", "the generator puts nobody on two blocks back to back except by its recorded 'back-to-back shift' perturbation (CR-M8)",
      b2b > 0 and b2b == deliberate, {"blocks_with_a_back_to_back_nurse": b2b, "of_which_recorded_perturbations": deliberate})

SA, SB = os.path.join(TMP, "setA"), os.path.join(TMP, "setB")
for s_, seed_ in ((SA, "seed-A"), (SB, "seed-B")):
    M.make_set(s_, 3, 2, seed_, "both"); M.seal(s_, RULES); M.label_sheet(s_, s_ + ".csv")
labA = os.path.join(TMP, "labA.csv"); fill(SA + ".csv", labA, lambda r: "no-gap")
check("M25", "a filled sheet from another set (same unit ids) is refused at the lock (CR-M9)",
      "belongs to another set" in (refused(lambda: M.lock_labels(SB, labA, "SIMULATED")) or ""), {})

rch = M.reachability()
w = {r["units"]: r["wilson_95"][1] - r["wilson_95"][0] for r in rch if r.get("agreement") == 0.8}
check("M14", "reachability table: the interval narrows as units grow (Wilson, clustering ignored)", w[60] > w[100] > w[140] > w[200], w)
pl = {(r["units"], r["hypothetical_threshold_for_the_lower_bound"]): r["smallest_observed_agreement_that_clears_it"] for r in rch if "units" in r and "hypothetical_threshold_for_the_lower_bound" in r}
ok24 = all(k in pl for k in ((60, 0.8), (100, 0.8), (200, 0.8)))
check("M24", "pass line: with 100 units, a lower bound of at least 0.80 needs at least 88/100 agreement (hand check: 87/100 gives 0.790, "
      "88/100 gives 0.802)", ok24 and pl[(100, 0.8)] == 0.88 and pl[(60, 0.8)] > pl[(100, 0.8)] > pl[(200, 0.8)],
      {"(100, 0.8)": pl.get((100, 0.8)), "pass_line_present": ok24})

shutil.rmtree(TMP, ignore_errors=True)
nf = sum(1 for r in RES if r["result"] == "FAIL")
print(f"\n{len(RES) - nf} PASS · {nf} FAIL")
if OUT:
    json.dump({"root": ROOT, "results": RES}, open(OUT, "w"), indent=1)
sys.exit(1 if nf else 0)
