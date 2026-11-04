#!/usr/bin/env python3
"""test_gapcheck.py -- acceptance tests for the track (ii) detector, increment 1. Expected results are written here
before the detector is run against them (brief §4 and the 2026-10-30 annex). Offline; synthetic CONSTRUCTED fixtures.
    python3 -B test_gapcheck.py <build root> [--json out.json]
"""
import json, os, subprocess, sys

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
sys.path.insert(0, os.path.join(ROOT, "detector"))
sys.dont_write_bytecode = True
import gapcheck as G  # noqa: E402

RES = []


def check(cid, name, ok, observed):
    RES.append({"id": cid, "check": name, "result": "PASS" if ok else "FAIL", "observed": observed})
    print(f"{'PASS' if ok else 'FAIL'} {cid} {name}  [{json.dumps(observed)[:200]}]")


fx = lambda n: json.load(open(os.path.join(ROOT, "fixtures", n + ".json"), encoding="utf-8"))
rl = lambda n: json.load(open(os.path.join(ROOT, "rules", "RULES." + n + ".json"), encoding="utf-8"))
run = lambda f, r: G.detect(fx(f) if f else None, rl(r))
loc = lambda env: [(x["rule_id"], x["locator"]["date"], x["locator"]["shift"], tuple(x["locator"]["staff_ids"])) for x in env["findings"]]

# ---- brief §4 positive controls
e = run("LEGAL-PC-01", "test-H2-only")
check("PC-1", "LEGAL-PC-01, H2 only: COMPLETED, rules_evaluated [H2], findings []",
      e["run_status"] == "COMPLETED" and e["rules_evaluated"] == ["H2"] and e["findings"] == [], {"status": e["run_status"], "f": loc(e)})
e = run("CONSTRUCTED-ILLEGAL-PC-01", "test-H2-only")
want = [{"rule_id": "H2", "locator": {"staff_ids": ["S03", "S05"], "date": "D01", "shift": "NIGHT"}, "severity": "HARD",
         "explanation": "No charge-qualified RN on D01 NIGHT; assigned S03, S05; neither holds charge."}]
check("PC-2", "CONSTRUCTED-ILLEGAL-PC-01: exactly the one finding written in the brief, word for word",
      e["run_status"] == "COMPLETED" and e["findings"] == want, {"findings": e["findings"]})
e = G.detect(None, rl("test-H2-only"))
check("PC-3", "no input -> NOT_RUN, never an empty COMPLETED", e["run_status"] == "NOT_RUN" and e["findings"] == [], {"status": e["run_status"]})

# ---- founder template: nothing is guessed
e = run("CONSTRUCTED-ILLEGAL-PC-01", "founder-template")
skipped = {s["rule_id"]: s["reason"] for s in e["rules_skipped"]}
check("T-1", "founder template (every rule LOW): NOT_RUN, nothing evaluated, every rule listed as skipped with its reason",
      e["run_status"] == "NOT_RUN" and e["rules_evaluated"] == [] and e["findings"] == []
      and all(r in skipped and "unratified" in skipped[r] for r in ("H1", "H2", "H4", "H5", "H6", "H9"))
      and all(r in skipped for r in ("H3", "H7", "H8", "H10")), {"status": e["run_status"], "skipped": sorted(skipped)})
tpl = rl("founder-template")
check("T-2", "the founder template carries no numbers or answers", all(
    v is None or (isinstance(v, dict) and all(x is None for x in v.values()))
    for rr in tpl["rules"].values() for v in rr["params"].values()) and all(rr["status"] == "LOW" for rr in tpl["rules"].values()),
      {"statuses": sorted({rr["status"] for rr in tpl["rules"].values()})})
half = rl("test-H5-P12-incl"); half["rules"]["H5"]["params"]["boundary_inclusive"] = None
e = G.detect(fx("A1-H5-BOUNDARY"), half)
check("T-3", "a ratified rule with an unset parameter is skipped with the parameter named",
      e["run_status"] == "NOT_RUN" and any(s["rule_id"] == "H5" and "boundary_inclusive" in s["reason"] for s in e["rules_skipped"]),
      {"status": e["run_status"], "skipped": [s for s in e["rules_skipped"] if s["rule_id"] == "H5"]})

# ---- annex A1: threshold boundary (rest = 12 h for S02; HYPOTHETICAL P varied)
res_a1 = {}
for P in (11, 12, 13):
    for inc in ("incl", "excl"):
        res_a1[f"P{P}-{inc}"] = loc(run("A1-H5-BOUNDARY", f"test-H5-P{P}-{inc}"))
one = [("H5", "D02", "DAY", ("S02",))]
check("A1", "boundary: rest P-1 -> one finding at S02 D02 DAY; rest = P -> none if inclusive, one if exclusive; P+1 -> none",
      res_a1["P13-incl"] == one and res_a1["P13-excl"] == one and res_a1["P12-incl"] == [] and res_a1["P12-excl"] == one
      and res_a1["P11-incl"] == [] and res_a1["P11-excl"] == [], res_a1)

# ---- annex A2: missing / unknown band
for fxn in ("A2-BAND-MISSING", "A2-BAND-UNKNOWN"):
    e = run(fxn, "test-H1-H2-skip")
    sk = [s for s in e["rules_skipped"] if s["rule_id"] == "H1" and s["scope"] != "all"]
    check(f"A2-{fxn[-7:].lower()}", f"{fxn}: H1 skipped for D01 NIGHT with the reason; H2 still runs; COMPLETED; no H1 finding there",
          e["run_status"] == "COMPLETED" and "H2" in e["rules_evaluated"] and len(sk) == 1 and sk[0]["scope"] == {"date": "D01", "shift": "NIGHT"}
          and not any(f[0] == "H1" and f[2] == "NIGHT" for f in loc(e)), {"skipped": sk, "findings": loc(e)})
e = run("A2-BAND-MISSING", "test-H1-H2-refuse")
check("A2-refuse", "policy 'refuse': a missing band refuses the run (ERROR) and reports no findings",
      e["run_status"] == "ERROR" and "census band" in e.get("reason", "") and e["findings"] == [], {"status": e["run_status"], "reason": e.get("reason")})
e = run("A2-BAND-MISSING", "test-H1-H2-default-normal")
check("A2-named", "policy naming a band: the missing band is treated as that band (no skip), as configured",
      e["run_status"] == "COMPLETED" and not [s for s in e["rules_skipped"] if s["rule_id"] == "H1" and s["scope"] != "all"], {"findings": loc(e)})

# ---- annex A3: contradictory constraint
for fxn, rule in (("A3-CONTRA-NONCHARGE", "H2"), ("A3-CONTRA-UNAVAILABLE-CHARGE", "H4")):
    e = run(fxn, "test-H2-H4")
    notes = [(n["type"], n["date"], n["shift"]) for n in e["input_notes"]]
    check(f"A3-{rule}", f"{fxn}: a {rule} finding on D03 NIGHT, the UNSATISFIABLE note, and never findings []",
          e["findings"] != [] and any(f[0] == rule and f[1] == "D03" and f[2] == "NIGHT" for f in loc(e))
          and ("UNSATISFIABLE", "D03", "NIGHT") in notes, {"findings": loc(e), "notes": notes})

# ---- single rules, positive and negative
check("H1-a", "H1 (charge counted): DAY with one RN is short; NIGHT with two is not",
      [f for f in loc(run("H1-SHORT", "test-H1-H2-skip")) if f[0] == "H1"] == [("H1", "D01", "DAY", ("S01",))],
      loc(run("H1-SHORT", "test-H1-H2-skip")))
check("H1-b", "H1 (charge not counted): both shifts are short",
      [(f[1], f[2]) for f in loc(run("H1-SHORT", "test-H1-charge-not-counted"))] == [("D01", "DAY"), ("D01", "NIGHT")],
      loc(run("H1-SHORT", "test-H1-charge-not-counted")))
check("H4-a", "H4 with no exceptions: the unavailable nurse scheduled is flagged",
      loc(run("H4-VIOLATION", "test-H4-none")) == [("H4", "D01", "DAY", ("S02",))], loc(run("H4-VIOLATION", "test-H4-none")))
check("H4-b", "H4 with 'mandation' allowed: the tagged assignment is not flagged; an untagged one still is",
      loc(run("H4-EXCEPTION", "test-H4-mandation")) == [] and loc(run("H4-VIOLATION", "test-H4-mandation")) == [("H4", "D01", "DAY", ("S02",))],
      [loc(run("H4-EXCEPTION", "test-H4-mandation")), loc(run("H4-VIOLATION", "test-H4-mandation"))])
check("H6-a", "H6 max 3: four days in a row flagged once per nurse, at the fourth day",
      loc(run("H6-FOUR-IN-A-ROW", "test-H6-max3")) == [("H6", "D04", None, ("S01",)), ("H6", "D04", None, ("S02",))],
      loc(run("H6-FOUR-IN-A-ROW", "test-H6-max3")))
check("H6-b", "H6 max 5: no finding", loc(run("H6-FOUR-IN-A-ROW", "test-H6-max5")) == [], loc(run("H6-FOUR-IN-A-ROW", "test-H6-max5")))
check("H9-a", "H9: one nurse in ED and triage in the same block is flagged when every place counts",
      loc(run("H9-TWO-PLACES", "test-H9-all-count")) == [("H9", "D01", "DAY", ("S02",))], loc(run("H9-TWO-PLACES", "test-H9-all-count")))
check("H9-b", "H9: not flagged when triage is configured as not a separate place",
      loc(run("H9-TWO-PLACES", "test-H9-triage-not-separate")) == [], loc(run("H9-TWO-PLACES", "test-H9-triage-not-separate")))

# ---- refused inputs (fence F1) and determinism
for fxn in ("REFUSE-NOT-SYNTHETIC", "REFUSE-NAME", "REFUSE-CALENDAR-DATE", "REFUSE-LONG-STAFF-ID", "REFUSE-LONG-DATE"):
    e = run(fxn, "test-H2-only")
    check(f"F1-{fxn[7:].lower()}", f"{fxn}: run_status ERROR with a reason, no findings", e["run_status"] == "ERROR" and e["findings"] == []
          and e.get("reason"), {"reason": e.get("reason")})
e = run("NO-CHARGE-STAFF", "test-H2-H4")
check("U-1", "nobody on the staff list holds charge (H2, H4): both shifts flagged, plus one run-level UNSATISFIABLE note for H2",
      [(f[0], f[2]) for f in loc(e)] == [("H2", "DAY"), ("H2", "NIGHT")]
      and [(n["type"], n["rules"], n["date"]) for n in e["input_notes"]] == [("UNSATISFIABLE", ["H2"], None)],
      {"findings": loc(e), "notes": e["input_notes"]})
a, b = run("A3-CONTRA-NONCHARGE", "test-H2-H4"), run("A3-CONTRA-NONCHARGE", "test-H2-H4")
check("DET", "the same input and rules give byte-identical output (no timestamps)", G.canonical(a) == G.canonical(b), {"sha": G.sha(a)[:12]})

# ---- the CLI and its exit codes
cli = os.path.join(ROOT, "detector", "gapcheck.py")
codes = {}
for tag, args in (("completed", ["--rules", os.path.join(ROOT, "rules", "RULES.test-H2-only.json"), "--input", os.path.join(ROOT, "fixtures", "LEGAL-PC-01.json")]),
                  ("not_run", ["--rules", os.path.join(ROOT, "rules", "RULES.founder-template.json"), "--input", os.path.join(ROOT, "fixtures", "LEGAL-PC-01.json")]),
                  ("no_input", ["--rules", os.path.join(ROOT, "rules", "RULES.test-H2-only.json")]),
                  ("error", ["--rules", os.path.join(ROOT, "rules", "RULES.test-H2-only.json"), "--input", os.path.join(ROOT, "fixtures", "REFUSE-NAME.json")]),
                  ("missing_file", ["--rules", os.path.join(ROOT, "rules", "RULES.test-H2-only.json"), "--input", os.path.join(ROOT, "fixtures", "NO-SUCH-ROSTER.json")])):
    codes[tag] = subprocess.run([sys.executable, "-B", cli] + args, capture_output=True, text=True).returncode
check("CLI", "exit codes: COMPLETED 0 · NOT_RUN 3 (template, or no --input) · ERROR 2 (refused input, or a named file that is missing)",
      codes == {"completed": 0, "not_run": 3, "no_input": 3, "error": 2, "missing_file": 2}, codes)

n_fail = sum(1 for r in RES if r["result"] == "FAIL")
print(f"\n{len(RES) - n_fail} PASS · {n_fail} FAIL")
if OUT:
    json.dump({"root": ROOT, "python": sys.version.split()[0], "results": RES}, open(OUT, "w"), indent=1)
sys.exit(1 if n_fail else 0)
