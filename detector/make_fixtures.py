#!/usr/bin/env python3
"""make_fixtures.py -- writes the founder rule template, the TEST-ONLY rule sets and the CONSTRUCTED fixtures.
    python3 -B make_fixtures.py <output root>      (writes <root>/rules/ and <root>/fixtures/)
Every fixture is synthetic, token-only, and labelled CONSTRUCTED. Every number in a TEST rule set is a HYPOTHETICAL
example parameter used only to exercise the code; none is a clinical rule. The founder template carries no numbers.
"""
import copy, json, os, sys

ROOT = sys.argv[1]
os.makedirs(os.path.join(ROOT, "rules"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "fixtures"), exist_ok=True)


def dump(rel, obj):
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="\n") as f:   # 1.2 (T2-W01): LF on every OS
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


QUESTIONS = {  # from II-CONSTRAINTS-v0.md Part 1 and the 2026-10-30 annex; the founder answers them
    "H1": "Minimum RN count by census band (low, normal, high, surge). Is charge ever also counted in the H1 number? "
          "What happens when the band is missing or unknown: skip, refuse, or use a named band?",
    "H2": "A charge-qualified RN is present on every shift. Keep, fix or kill.",
    "H4": "A nurse marked UNAVAILABLE is never scheduled. Any exception (mandation, holiday rotation, disaster)? "
          "List the allowed exception tags, or [] for none.",
    "H5": "Minimum rest between shifts, in hours. Is a rest exactly equal to the minimum legal (inclusive)? "
          "Is day-after-night forbidden outright?",
    "H6": "Maximum consecutive shifts worked (twelves in a row, counted as consecutive days with a shift).",
    "H9": "No nurse assigned to two places in the same block. Which places (float, sitter, triage) do NOT count as a "
          "separate place? [] means every place counts.",
}
PARAMS = {"H1": {"min_rn_by_band": {"low": None, "normal": None, "high": None, "surge": None},
                 "charge_counts_toward_h1": None, "missing_band_policy": None},
          "H2": {}, "H4": {"allowed_exceptions": None},
          "H5": {"min_rest_hours": None, "boundary_inclusive": None, "day_after_night_forbidden": None},
          "H6": {"max_consecutive_shifts": None}, "H9": {"not_separate_places": None}}
template = {"source": "FOUNDER TEMPLATE - every rule LOW, no parameter set; the founder ratifies (MED/HIGH), fixes, or "
                      "kills each rule and fills its parameters. Nothing here is a default.",
            "rules": {rid: {"status": "LOW", "params": copy.deepcopy(PARAMS[rid]), "question": QUESTIONS[rid],
                            "founder_note": ""} for rid in PARAMS}}
dump("rules/RULES.founder-template.json", template)


def test_rules(enable, params=None, tag=""):
    r = {"source": "TEST-ONLY CONSTRUCTED rule set" + (f" ({tag})" if tag else "") + ". HYPOTHETICAL example values; "
                   "never used for measurement and not a clinical rule.", "rules": {}}
    for rid in PARAMS:
        r["rules"][rid] = {"status": "HIGH" if rid in enable else "LOW", "params": copy.deepcopy(PARAMS[rid])}
    for rid, pv in (params or {}).items():
        r["rules"][rid]["params"].update(pv)
    return r


SHIFTS = [{"shift": "DAY", "start_hour": 7, "end_hour": 19}, {"shift": "NIGHT", "start_hour": 19, "end_hour": 7}]
STAFF = [{"staff_id": f"S0{i}", "role": "RN", "qualifications": ["charge"] if i in (1, 4) else []} for i in range(1, 6)]


def roster(dates, assignments, availability=None, context=None, tag=""):
    avail = availability if availability is not None else [
        {"staff_id": s["staff_id"], "date": d, "shift": sh["shift"], "status": "AVAILABLE"} for s in STAFF for d in dates for sh in SHIFTS]
    ctx = context if context is not None else [{"date": d, "shift": sh["shift"], "census_band": "normal"} for d in dates for sh in SHIFTS]
    return {"provenance": {"synthetic": True, "generator": "make_fixtures.py (CONSTRUCTED)", "seed": None, "fixture": tag},
            "staff": copy.deepcopy(STAFF), "shifts": copy.deepcopy(SHIFTS), "dates": list(dates), "context": ctx,
            "availability": avail, "assignments": assignments}


A = lambda sid, d, s, place="ED", **kw: dict({"staff_id": sid, "date": d, "shift": s, "place": place}, **kw)

# Brief §4 positive controls (exact rosters as written there)
dump("fixtures/LEGAL-PC-01.json", roster(["D01"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY"),
                                                  A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")], tag="LEGAL-PC-01"))
dump("fixtures/CONSTRUCTED-ILLEGAL-PC-01.json", roster(["D01"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY"),
                                                                A("S03", "D01", "NIGHT"), A("S05", "D01", "NIGHT")],
                                                      tag="CONSTRUCTED-ILLEGAL-PC-01"))
dump("rules/RULES.test-H2-only.json", test_rules({"H2"}, tag="brief §4: H2 only"))

# Annex A1: threshold boundary for H5. S02 works D01 DAY and D02 DAY: 12 h of rest. The HYPOTHETICAL minimum P is
# varied instead of the roster: P=13 (rest = P-1), P=12 (rest = P), P=11 (rest = P+1).
# Only S02 has back-to-back shifts (D01 DAY then D02 DAY: 12 h); everyone else rests 24 h or more, or works once.
dump("fixtures/A1-H5-BOUNDARY.json", roster(["D01", "D02"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY"), A("S04", "D01", "NIGHT"),
                                                             A("S03", "D01", "NIGHT"), A("S02", "D02", "DAY"), A("S05", "D02", "DAY"),
                                                             A("S01", "D02", "NIGHT")], tag="A1"))
for P in (11, 12, 13):
    for inc in (True, False):
        dump(f"rules/RULES.test-H5-P{P}-{'incl' if inc else 'excl'}.json",
             test_rules({"H5"}, {"H5": {"min_rest_hours": P, "boundary_inclusive": inc, "day_after_night_forbidden": False}},
                        tag=f"annex A1, HYPOTHETICAL P={P}"))

# Annex A2: missing / unknown census band (H1)
ctx_missing = [{"date": "D01", "shift": "DAY", "census_band": "normal"}]                      # NIGHT has no band
ctx_unknown = [{"date": "D01", "shift": "DAY", "census_band": "normal"}, {"date": "D01", "shift": "NIGHT", "census_band": "unknown"}]
base_a2 = [A("S01", "D01", "DAY"), A("S02", "D01", "DAY"), A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")]
dump("fixtures/A2-BAND-MISSING.json", roster(["D01"], base_a2, context=ctx_missing, tag="A2 missing"))
dump("fixtures/A2-BAND-UNKNOWN.json", roster(["D01"], base_a2, context=ctx_unknown, tag="A2 unknown"))
h1p = {"min_rn_by_band": {"low": 2, "normal": 2, "high": 3, "surge": 4}, "charge_counts_toward_h1": True}
dump("rules/RULES.test-H1-H2-skip.json", test_rules({"H1", "H2"}, {"H1": dict(h1p, missing_band_policy="skip")}, tag="annex A2, HYPOTHETICAL bands"))
dump("rules/RULES.test-H1-H2-refuse.json", test_rules({"H1", "H2"}, {"H1": dict(h1p, missing_band_policy="refuse")}, tag="annex A2, HYPOTHETICAL bands"))
dump("rules/RULES.test-H1-H2-default-normal.json", test_rules({"H1", "H2"}, {"H1": dict(h1p, missing_band_policy="normal")},
                                                              tag="annex A2 control: a policy that names a band"))

# Annex A3: contradictory constraint. Both charge-qualified nurses (S01, S04) are UNAVAILABLE on D03 NIGHT.
dates3 = ["D01", "D02", "D03"]
av3 = [{"staff_id": s["staff_id"], "date": d, "shift": sh["shift"],
        "status": "UNAVAILABLE" if (s["staff_id"] in ("S01", "S04") and d == "D03" and sh["shift"] == "NIGHT") else "AVAILABLE"}
       for s in STAFF for d in dates3 for sh in SHIFTS]
day_night = lambda d, night: [A("S01", d, "DAY"), A("S02", d, "DAY")] + night
dump("fixtures/A3-CONTRA-NONCHARGE.json", roster(dates3, day_night("D01", [A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")])
                                                 + day_night("D02", [A("S04", "D02", "NIGHT"), A("S05", "D02", "NIGHT")])
                                                 + [A("S02", "D03", "DAY"), A("S01", "D03", "DAY"), A("S03", "D03", "NIGHT"), A("S05", "D03", "NIGHT")],
                                                 availability=av3, tag="A3 non-charge night"))
dump("fixtures/A3-CONTRA-UNAVAILABLE-CHARGE.json", roster(dates3, day_night("D01", [A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")])
                                                          + day_night("D02", [A("S04", "D02", "NIGHT"), A("S05", "D02", "NIGHT")])
                                                          + [A("S02", "D03", "DAY"), A("S01", "D03", "DAY"), A("S04", "D03", "NIGHT"), A("S03", "D03", "NIGHT")],
                                                          availability=av3, tag="A3 unavailable charge scheduled"))
dump("rules/RULES.test-H2-H4.json", test_rules({"H2", "H4"}, {"H4": {"allowed_exceptions": []}}, tag="annex A3"))

# Single-rule fixtures for H4, H6, H9 and H1 (positive and negative)
dump("fixtures/H4-VIOLATION.json", roster(["D01"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY"), A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")],
                                          availability=[{"staff_id": "S02", "date": "D01", "shift": "DAY", "status": "UNAVAILABLE"}], tag="H4 violation"))
dump("fixtures/H4-EXCEPTION.json", roster(["D01"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY", exception="mandation"),
                                                    A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")],
                                          availability=[{"staff_id": "S02", "date": "D01", "shift": "DAY", "status": "UNAVAILABLE"}], tag="H4 exception"))
dump("rules/RULES.test-H4-mandation.json", test_rules({"H4"}, {"H4": {"allowed_exceptions": ["mandation"]}}, tag="HYPOTHETICAL exception list"))
dump("rules/RULES.test-H4-none.json", test_rules({"H4"}, {"H4": {"allowed_exceptions": []}}, tag="no exceptions"))
dates5 = ["D01", "D02", "D03", "D04", "D05"]
dump("fixtures/H6-FOUR-IN-A-ROW.json", roster(dates5, [A("S02", d, "DAY") for d in dates5[:4]] + [A("S01", d, "DAY") for d in dates5], tag="H6"))
dump("rules/RULES.test-H6-max3.json", test_rules({"H6"}, {"H6": {"max_consecutive_shifts": 3}}, tag="HYPOTHETICAL max 3"))
dump("rules/RULES.test-H6-max5.json", test_rules({"H6"}, {"H6": {"max_consecutive_shifts": 5}}, tag="HYPOTHETICAL max 5"))
dump("fixtures/H9-TWO-PLACES.json", roster(["D01"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY", place="ED"), A("S02", "D01", "DAY", place="triage"),
                                                     A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")], tag="H9"))
dump("rules/RULES.test-H9-all-count.json", test_rules({"H9"}, {"H9": {"not_separate_places": []}}, tag="every place counts"))
dump("rules/RULES.test-H9-triage-not-separate.json", test_rules({"H9"}, {"H9": {"not_separate_places": ["triage"]}}, tag="HYPOTHETICAL: triage not separate"))
dump("fixtures/H1-SHORT.json", roster(["D01"], [A("S01", "D01", "DAY"), A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")], tag="H1 short on DAY"))
dump("rules/RULES.test-H1-charge-not-counted.json", test_rules({"H1"}, {"H1": dict(h1p, charge_counts_toward_h1=False, missing_band_policy="skip")},
                                                              tag="HYPOTHETICAL: charge not counted"))

# Refused inputs (fence F1)
bad = roster(["D01"], [A("S01", "D01", "DAY")], tag="not synthetic"); bad["provenance"]["synthetic"] = False
dump("fixtures/REFUSE-NOT-SYNTHETIC.json", bad)
bad = roster(["D01"], [A("S01", "D01", "DAY")], tag="name"); bad["staff"][1]["staff_id"] = "Jane Doe"
bad["availability"] = [x for x in bad["availability"] if x["staff_id"] != "S02"]
dump("fixtures/REFUSE-NAME.json", bad)
bad = roster(["D01"], [A("S01", "D01", "DAY")], tag="calendar date"); bad["dates"] = ["2026-07-01"]
bad["availability"], bad["context"], bad["assignments"] = [], [], []
dump("fixtures/REFUSE-CALENDAR-DATE.json", bad)
# Colour review CR-T3: an employee-ID-length number or a calendar date behind the token letter is refused too
bad = roster(["D01"], [A("S01", "D01", "DAY")], tag="employee-ID-length staff token"); bad["staff"][1]["staff_id"] = "S004512"
bad["availability"] = [x for x in bad["availability"] if x["staff_id"] != "S02"]
dump("fixtures/REFUSE-LONG-STAFF-ID.json", bad)
bad = roster(["D01"], [A("S01", "D01", "DAY")], tag="calendar date behind the D"); bad["dates"] = ["D20261030"]
bad["availability"], bad["context"], bad["assignments"] = [], [], []
dump("fixtures/REFUSE-LONG-DATE.json", bad)
# Colour review CR-T2: nobody on the staff list holds the charge qualification
nc = roster(["D01"], [A("S01", "D01", "DAY"), A("S02", "D01", "DAY"), A("S04", "D01", "NIGHT"), A("S03", "D01", "NIGHT")], tag="no charge on the staff list")
for s in nc["staff"]:
    s["qualifications"] = []
dump("fixtures/NO-CHARGE-STAFF.json", nc)
print("fixtures and rule sets written")
