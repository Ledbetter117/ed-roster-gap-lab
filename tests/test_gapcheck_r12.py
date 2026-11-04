#!/usr/bin/env python3
"""test_gapcheck_r12.py -- increment 1.2 regressions (ORCA-ED-MAX-PROGRESS-20261030). Each check states the CORRECT behaviour and
fails on increment 1.1 (failing-first evidence: run it against the 1.1 build root). Offline; CONSTRUCTED synthetic rosters; every
rule number is HYPOTHETICAL.
    python3 -B test_gapcheck_r12.py <build root> [--json out.json]
"""
import copy, json, os, subprocess, sys, tempfile, time
from unittest import mock

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
sys.path.insert(0, os.path.join(ROOT, "detector"))
sys.dont_write_bytecode = True
import gapcheck as G  # noqa: E402

RES = []


def check(cid, name, ok, observed):
    RES.append({"id": cid, "check": name, "result": "PASS" if ok else "FAIL", "observed": observed})
    print(f"{'PASS' if ok else 'FAIL'} {cid} {name}  [{json.dumps(observed, default=str)[:200]}]")


SHIFTS = [{"shift": "DAY", "start_hour": 7, "end_hour": 19}, {"shift": "NIGHT", "start_hour": 19, "end_hour": 7}]


def roster(assign, dates=("D01", "D02", "D03"), staff=None, shifts=None, **extra):
    r = {"provenance": {"synthetic": True, "generator": "test_gapcheck_r12 (CONSTRUCTED)"},
         "staff": staff or [{"staff_id": "S01", "role": "RN", "qualifications": ["charge"]},
                            {"staff_id": "S02", "role": "RN", "qualifications": []}],
         "shifts": SHIFTS if shifts is None else shifts, "dates": list(dates), "assignments": [], "availability": [], "context": []}
    for a in assign:
        sid, rest = a.split("@")
        d, s = rest.split("/")
        r["assignments"].append({"staff_id": sid, "date": d, "shift": s, "place": "ed"})
    r.update(extra)
    return r


def rules(**ratified):
    base = {"source": "TEST-ONLY HYPOTHETICAL (test_gapcheck_r12)", "rules": {}}
    for rid, params in ratified.items():
        base["rules"][rid] = {"status": "HIGH", "params": params}
    return base


H5 = dict(min_rest_hours=12, boundary_inclusive=True, day_after_night_forbidden=False)
H6 = dict(max_consecutive_shifts=3)

# ---- R1 impossible or mistyped ratified parameters are refused (1.1 accepted them)
for cid, rs in (("R1-h6-max0", rules(H6=dict(max_consecutive_shifts=0))),
                ("R1-h5-negative", rules(H5=dict(min_rest_hours=-4, boundary_inclusive=True, day_after_night_forbidden=False))),
                ("R1-h1-negative", rules(H1=dict(min_rn_by_band={"normal": -1}, charge_counts_toward_h1=True, missing_band_policy="normal"))),
                ("R1-h1-policy", rules(H1=dict(min_rn_by_band={"normal": 2}, charge_counts_toward_h1=True, missing_band_policy="guess"))),
                ("R1-h5-bool-as-text", rules(H5=dict(min_rest_hours=12, boundary_inclusive="yes", day_after_night_forbidden=False)))):
    e = G.detect(roster(["S01@D01/DAY"]), rs)
    check(cid, "an impossible or mistyped ratified parameter is ERROR with the reason, never evaluated",
          e["run_status"] == "ERROR" and "rule parameter invalid" in (e.get("reason") or "") and e["findings"] == [],
          {"status": e["run_status"], "reason": (e.get("reason") or "")[:120]})
e = G.detect(roster(["S01@D01/DAY"]), rules(H6=dict(max_consecutive_shifts=None)))
check("R1-unset", "an unset parameter still means 'not runnable', not ERROR (1.1 behaviour kept)",
      e["run_status"] == "NOT_RUN", {"status": e["run_status"]})

# ---- R2 duplicate assignment is reported, not silent
e = G.detect(roster(["S01@D01/DAY", "S01@D01/DAY"]), rules(H6=H6))
check("R2", "the same assignment listed twice gives a DUPLICATE_ASSIGNMENT note (counted once by every rule)",
      [n["type"] for n in e["input_notes"]] == ["DUPLICATE_ASSIGNMENT"] and e["run_status"] == "COMPLETED", e["input_notes"])

# ---- R3 empty roster is NOT_RUN
for cid, r in (("R3-no-dates", roster([], dates=())), ("R3-no-shifts", roster([], shifts=[]))):
    e = G.detect(r, rules(H2={}, H6=H6))
    check(cid, "a roster with no date or no shift is NOT_RUN 'empty roster' (1.1: COMPLETED, no findings)",
          e["run_status"] == "NOT_RUN" and "empty roster" in (e.get("reason") or ""), {"status": e["run_status"], "reason": e.get("reason")})
e = G.detect(roster([], dates=("D01",)), rules(H2={}))
check("R3-dates-no-assignments", "dates with nobody assigned is still evaluated (a fully unstaffed roster has H2 gaps)",
      e["run_status"] == "COMPLETED" and sorted(f["rule_id"] for f in e["findings"]) == ["H2", "H2"], {"findings": len(e["findings"])})

# ---- R4 overlapping assignments in different blocks are reported
mid = SHIFTS + [{"shift": "MID", "start_hour": 11, "end_hour": 23}]
e = G.detect(roster(["S01@D01/DAY", "S01@D01/MID"], dates=("D01",), shifts=mid), rules(H9=dict(not_separate_places=[])))
check("R4", "one nurse on DAY 07-19 and MID 11-23 gets an OVERLAPPING_ASSIGNMENT note even when H5 is not ratified",
      any(n["type"] == "OVERLAPPING_ASSIGNMENT" and "8 h" in n["explanation"] for n in e["input_notes"]), e["input_notes"])
e = G.detect(roster(["S01@D01/DAY", "S01@D01/NIGHT"], dates=("D01",)), rules(H9=dict(not_separate_places=[])))
check("R4-adjacent", "DAY 07-19 then NIGHT 19-07 touch but do not overlap: no note", e["input_notes"] == [], e["input_notes"])

# ---- R5 H6 count unit
dn = ["S01@D01/DAY", "S01@D01/NIGHT", "S01@D02/DAY"]
e_day = G.detect(roster(dn), rules(H6=H6))
e_shift = G.detect(roster(dn), rules(H6=dict(H6, count_unit="shift")))
check("R5", "count_unit 'shift' counts a DAY+NIGHT date as two (3 shifts over 2 days: no finding at max 3; 'calendar_day' 2 days)",
      e_day["findings"] == [] and e_shift["findings"] == [] and e_day.get("h6_count_unit", "").startswith("calendar_day (default")
      and e_shift.get("h6_count_unit") == "shift", {"day": e_day.get("h6_count_unit"), "shift": e_shift.get("h6_count_unit")})
dn4 = dn + ["S01@D03/DAY"]
e_shift = G.detect(roster(dn4), rules(H6=dict(H6, count_unit="shift")))
e_day = G.detect(roster(dn4), rules(H6=H6))
check("R5-exceed", "4 shifts on 3 consecutive days exceed max 3 under 'shift' but not under 'calendar_day'",
      [f["locator"]["date"] for f in e_shift["findings"]] == ["D03"] and e_day["findings"] == [],
      {"shift": [f["explanation"] for f in e_shift["findings"]], "day": len(e_day["findings"])})

# ---- R6 carry-in across a period boundary
cr = roster(["S01@D01/NIGHT", "S01@D02/DAY"], dates=("D01", "D02"), evaluate_from="D02")
e = G.detect(cr, rules(H5=H5, H2={}))
check("R6-h5", "a NIGHT on the carry-in date D01 then DAY on D02 is an H5 finding on D02; no block rule runs on D01",
      sorted((f["rule_id"], f["locator"]["date"]) for f in e["findings"]) == [("H2", "D02"), ("H5", "D02")] and e.get("carry_in_dates") == ["D01"],
      [(f["rule_id"], f["locator"]["date"], f["locator"]["shift"]) for f in e["findings"]])
cr6 = roster(["S01@D01/DAY", "S01@D02/DAY", "S01@D03/DAY", "S01@D04/DAY", "S01@D05/DAY"], dates=("D01", "D02", "D03", "D04", "D05"),
             evaluate_from="D05")
e = G.detect(cr6, rules(H6=H6))
check("R6-h6", "a run that exceeds the maximum inside the carry-in period is reported on the first evaluated date (D05)",
      [f["locator"]["date"] for f in e["findings"]] == ["D05"], [f["explanation"] for f in e["findings"]])
e = G.detect(roster(["S01@D01/DAY"], evaluate_from="D09"), rules(H6=H6))
check("R6-bad", "evaluate_from naming a date outside the roster is ERROR", e["run_status"] == "ERROR", e.get("reason"))

# ---- R7 interfaces and the HYPOTHETICAL H8 branch
e = G.detect(roster(["S01@D01/DAY"]), rules(H3=dict(min_by_competency={"trauma": 1}), H6=H6))
sk = [s for s in e["rules_skipped"] if s["rule_id"] == "H3"]
check("R7-h3", "a ratified interface-only rule is skipped and names the data it needs (never guessed)",
      bool(sk) and "interface only" in sk[0]["reason"] and "competencies" in sk[0]["reason"], sk)
staff = [{"staff_id": "S01", "role": "RN", "qualifications": ["charge"]}, {"staff_id": "S02", "role": "RN", "qualifications": [],
                                                                            "orientee": True, "preceptor": "S03"},
         {"staff_id": "S03", "role": "RN", "qualifications": []}]
e = G.detect(roster(["S01@D01/DAY", "S02@D01/DAY"], staff=staff), rules(H8=dict(pairing_required=True)))
check("R7-h8", "HYPOTHETICAL H8 branch: an orientee on a block without the named preceptor is an H8 finding",
      [(f["rule_id"], f["locator"]["staff_ids"]) for f in e["findings"]] == [("H8", ["S02"])] and "H8" in e["rules_evaluated"],
      [f["explanation"] for f in e["findings"]])
h1 = dict(min_rn_by_band={"normal": 3}, charge_counts_toward_h1=True, missing_band_policy="normal")
r8 = roster(["S01@D01/DAY", "S02@D01/DAY", "S03@D01/DAY"], dates=("D01",), staff=staff)
e_with = G.detect(r8, rules(H1=h1, H8=dict(pairing_required=True)))
e_without = G.detect(r8, rules(H1=h1))
check("R7-h8-h1", "with H8 ratified an orientee does not count toward H1 (2 of 3 counted, below 3); without H8, 3 count",
      "H1" in [f["rule_id"] for f in e_with["findings"] if f["locator"]["shift"] == "DAY"] and
      "H1" not in [f["rule_id"] for f in e_without["findings"] if f["locator"]["shift"] == "DAY"],
      {"with_h8_day": [f["rule_id"] for f in e_with["findings"] if f["locator"]["shift"] == "DAY"]})

# ---- T2-W02 the determinism check cannot be fooled by a coarse clock
r = roster(["S01@D01/DAY"])
a = G.detect(r, rules(H6=H6))
with mock.patch("time.time", return_value=time.time() + 3600), mock.patch("time.time_ns", return_value=time.time_ns() + 3600 * 10 ** 9):
    b = G.detect(r, rules(H6=H6))
check("DET-clock", "same input and rules give byte-identical output even when the clock moves by an hour between runs",
      G.canonical(a) == G.canonical(b), {"sha": G.sha(a)[:12]})

# ---- T2-W01 fixture regeneration is byte-identical on every OS
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, "-B", os.path.join(ROOT, "detector", "make_fixtures.py"), tmp], check=True, capture_output=True)
    diffs = []
    for sub in ("rules", "fixtures"):
        for n in sorted(os.listdir(os.path.join(ROOT, sub))):
            if open(os.path.join(ROOT, sub, n), "rb").read() != open(os.path.join(tmp, sub, n), "rb").read():
                diffs.append(sub + "/" + n)
    check("W01-regen", "make_fixtures.py rewrites every shipped rule and fixture file byte for byte (LF), on this OS",
          diffs == [], {"differs": diffs[:5], "n_diff": len(diffs)})

n_fail = sum(r["result"] == "FAIL" for r in RES)
print(f"\n{len(RES) - n_fail} PASS · {n_fail} FAIL")
if OUT:
    json.dump({"results": RES, "pass": len(RES) - n_fail, "fail": n_fail}, open(OUT, "w"), indent=1)
sys.exit(1 if n_fail else 0)
