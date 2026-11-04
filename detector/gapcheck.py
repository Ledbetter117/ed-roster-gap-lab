#!/usr/bin/env python3
"""gapcheck.py -- track (ii) increment 1: a deterministic roster-gap detector (2026-10-30, candidate).

Implements the PROPOSED contract in ED-SPRINT-2026-10-16/TRACK-II_NEXT-STEP-BRIEF.md §2-§4 and the acceptance annex of
2026-10-30. It applies only rules the founder has RATIFIED (status MED or HIGH) and whose parameters he has filled. Every
rule ships as LOW with no parameters (rules/RULES.founder-template.json), so with the founder template the detector
returns NOT_RUN: it never guesses a clinical rule or a number.

    python3 gapcheck.py --rules <rules.json> --input <roster.json> [--out <result.json>]
Exit: 0 COMPLETED · 3 NOT_RUN · 2 ERROR (input refused). The output has no timestamp: the same input and rules always
give the same bytes.

Rules (logic from II-CONSTRAINTS-v0.md Part 1; parameters are founder inputs, none has a default):
  H1  minimum RN count on a shift, by census band      params: min_rn_by_band, charge_counts_toward_h1, missing_band_policy
  H2  a charge-qualified RN on every shift              params: none (ratification only)
  H4  a nurse marked UNAVAILABLE is never scheduled     params: allowed_exceptions (a list; [] means none)
  H5  minimum rest between shifts                       params: min_rest_hours, boundary_inclusive, day_after_night_forbidden
  H6  maximum consecutive shifts worked                 params: max_consecutive_shifts
  H9  no nurse in two places in the same block          params: not_separate_places (a list; [] means every place counts)
H3, H7, H8 and H10 need data the synthetic input does not carry; they are not implemented and are reported as skipped.
Fences F1/F2: input must declare provenance.synthetic = true and use short tokens (S01-S999, D01-D999), never names,
employee IDs or calendar dates. A token with more digits is refused, because an employee ID or a date such as 20261030
fits behind the letter (colour review CR-T3). A named --input file that does not exist is ERROR, not NOT_RUN (CR-T1).
H6 counts consecutive calendar days with at least one shift; a DAY and a NIGHT on one date count as one day.

Increment 1.2 (ORCA-ED-MAX-PROGRESS-20261030, Windows reproduction and adversarial review; successor edition, candidate):
  R1  a ratified rule whose parameters are the wrong type or impossible (negative rest, a maximum below 1, a negative band minimum,
      an unknown missing-band policy) is ERROR with the reason, never evaluated (1.1 accepted max 0 and flagged every worked day)
  R2  the same assignment listed twice is an input note DUPLICATE_ASSIGNMENT (1.1 removed it silently)
  R3  a roster with no date or no shift is NOT_RUN 'empty roster' (1.1 returned COMPLETED with no findings: empty is not absent)
  R4  one nurse on two assignments whose hours overlap in different blocks is an input note OVERLAPPING_ASSIGNMENT (1.1: no signal
      unless H5 was ratified); whether H9 should also cover it is a founder choice, not decided here
  R5  H6 parameter count_unit (OPTIONAL): 'calendar_day' (default; the 1.1 behaviour) or 'shift' (a DAY and a NIGHT on one date count
      as two shifts). Founder item W3.4 decides; the envelope always states the unit used
  R6  optional roster field evaluate_from (Dnn): earlier dates are carry-in context; H5 and H6 sequences include them, but no
      finding is reported on a carry-in date and block rules (H1, H2, H4, H9) are not evaluated there (founder item W3.5)
  R7  H3, H7, H8 and H10 have declared interfaces (parameters and the roster data each needs). A ratified interface-only rule is
      skipped with the missing data named; none is guessed. H8 has a HYPOTHETICAL branch that runs only when ratified and the
      roster marks orientees and their preceptors
Defaults are unchanged for every 1.1 input that 1.1 handled validly; changed results occur only for R1-R4 inputs.
"""
import argparse, hashlib, json, math, re, sys

DETECTOR_VERSION = "gapcheck-increment-1.2.1-2026-11-03"  # 1.2: R1-R7 above; 1.1: colour-review fixes CR-T1..CR-T3
RATIFIED = {"MED", "HIGH"}
IMPLEMENTED = ("H1", "H2", "H4", "H5", "H6", "H9")
INTERFACE_ONLY = {   # R7: declared parameters and the roster data each needs; nothing runs without both
    "H3": {"params": ("min_by_competency",), "data": "staff[].competencies (list of competency names)"},
    "H7": {"params": ("pay_period_days", "fte_band_hours"), "data": "staff[].fte_hours_per_period and hours per shift"},
    "H8": {"params": ("pairing_required",), "data": "staff[].orientee (true) and staff[].preceptor (a staff_id)"},
    "H10": {"params": ("contract_hardness",), "data": "staff[].contract_blocks (the blocks a traveler contract allows)"}}
NOT_IMPLEMENTED = ("H3", "H7", "H8", "H10")
H6_UNITS = ("calendar_day", "shift")


def validate_rules(rules):
    """R1: problems with the parameters of RATIFIED implemented rules (types and impossibilities only; no clinical bound)."""
    bad = []
    if not isinstance(rules, dict) or not isinstance(rules.get("rules", {}), dict):
        return ["rules must be an object containing a rules object"]
    for rid, spec in ((rules.get("rules") or {}).items()):
        if not isinstance(spec, dict) or not isinstance(spec.get("status"), (str, type(None))):
            bad.append("each rule must be an object with a text status")
            continue
        if not isinstance(spec.get("params", {}), (dict, type(None))):
            bad.append("rule parameters must be an object")
            continue
        if spec.get("status") not in RATIFIED or rid not in IMPLEMENTED + ("H8",):
            continue
        p = spec.get("params") or {}
        isint = lambda v: isinstance(v, int) and not isinstance(v, bool)
        if rid == "H1":
            mb = p.get("min_rn_by_band")
            if mb is not None and (not isinstance(mb, dict) or set(mb) - set(BANDS) or
                                   any(v is not None and (not isint(v) or v < 0) for v in mb.values())):
                bad.append("H1 min_rn_by_band must map bands %s to whole numbers >= 0 (got %r)" % ("/".join(BANDS), mb))
            if p.get("charge_counts_toward_h1") is not None and not isinstance(p["charge_counts_toward_h1"], bool):
                bad.append("H1 charge_counts_toward_h1 must be true or false")
            pol = p.get("missing_band_policy")
            if pol is not None and pol not in ("skip", "refuse") + BANDS:
                bad.append("H1 missing_band_policy must be skip, refuse or a band name (got %r)" % (pol,))
        elif rid == "H4":
            ex = p.get("allowed_exceptions")
            if ex is not None and (not isinstance(ex, list) or not all(isinstance(x, str) for x in ex)):
                bad.append("H4 allowed_exceptions must be a list of names")
        elif rid == "H5":
            r = p.get("min_rest_hours")
            if r is not None and (not isinstance(r, (int, float)) or isinstance(r, bool) or r < 0 or (isinstance(r, float) and not math.isfinite(r))):
                bad.append("H5 min_rest_hours must be a finite number >= 0 (got %r)" % (r,))
            for k in ("boundary_inclusive", "day_after_night_forbidden"):
                if p.get(k) is not None and not isinstance(p[k], bool):
                    bad.append("H5 %s must be true or false" % k)
        elif rid == "H6":
            m = p.get("max_consecutive_shifts")
            if m is not None and (not isint(m) or m < 1):
                bad.append("H6 max_consecutive_shifts must be a whole number >= 1 (got %r)" % (m,))
            if p.get("count_unit") not in (None,) + H6_UNITS:
                bad.append("H6 count_unit must be %s (got %r)" % (" or ".join(H6_UNITS), p.get("count_unit")))
        elif rid == "H9":
            ns = p.get("not_separate_places")
            if ns is not None and (not isinstance(ns, list) or not all(isinstance(x, str) for x in ns)):
                bad.append("H9 not_separate_places must be a list of place names")
        elif rid == "H8":
            if p.get("pairing_required") is not None and not isinstance(p["pairing_required"], bool):
                bad.append("H8 pairing_required must be true or false")
    return bad
REQUIRED = {"H1": ("min_rn_by_band", "charge_counts_toward_h1", "missing_band_policy"), "H2": (),
            "H4": ("allowed_exceptions",), "H5": ("min_rest_hours", "boundary_inclusive", "day_after_night_forbidden"),
            "H6": ("max_consecutive_shifts",), "H9": ("not_separate_places",)}
BANDS = ("low", "normal", "high", "surge")
STAFF_RE, DATE_RE = re.compile(r"^S\d{2,3}$"), re.compile(r"^D\d{2,3}$")


class InputRefused(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def validate_input(r):
    """Refuse anything that is not a synthetic, token-only roster in the contract shape."""
    if not isinstance(r, dict):
        raise InputRefused("input is not a JSON object")
    if not isinstance(r.get("provenance"), dict) or r["provenance"].get("synthetic") is not True:
        raise InputRefused("provenance.synthetic is not true: only synthetic rosters are accepted (fence F1)")
    for k in ("staff", "shifts", "dates", "assignments"):
        if not isinstance(r.get(k), list):
            raise InputRefused(f"'{k}' must be a list")
    staff_ids = set()
    for s in r["staff"]:
        if not isinstance(s, dict) or not isinstance(s.get("staff_id"), str) or not STAFF_RE.fullmatch(s["staff_id"]):
            raise InputRefused(f"staff_id {s.get('staff_id') if isinstance(s, dict) else s!r} is not a token like S01 "
                               "(S01-S999; names and employee IDs are refused)")
        if s["staff_id"] in staff_ids:
            raise InputRefused("duplicate staff_id")
        if not isinstance(s.get("role"), str) or not isinstance(s.get("qualifications", []), list) or not all(isinstance(q, str) for q in s.get("qualifications", [])):
            raise InputRefused("staff role must be text and qualifications a list of text")
        if s.get("orientee") is not None and not isinstance(s["orientee"], bool):
            raise InputRefused("orientee must be true or false")
        if s.get("preceptor") is not None and not isinstance(s["preceptor"], str):
            raise InputRefused("preceptor must be a staff token or null")
        staff_ids.add(s["staff_id"])
    for d in r["dates"]:
        if not isinstance(d, str) or not DATE_RE.fullmatch(d):
            raise InputRefused(f"date {d!r} is not a day index like D01 (D01-D999; calendar dates are refused)")
    if len(set(r["dates"])) != len(r["dates"]):
        raise InputRefused("duplicate date token")
    shifts = {}
    for sh in r["shifts"]:
        if not (isinstance(sh, dict) and type(sh.get("start_hour")) is int and type(sh.get("end_hour")) is int
                and 0 <= sh["start_hour"] < 24 and 0 <= sh["end_hour"] < 24 and isinstance(sh.get("shift"), str)
                and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", sh["shift"])):
            raise InputRefused(f"bad shift definition {sh!r}")
        if sh["shift"] in shifts:
            raise InputRefused("duplicate shift token")
        shifts[sh["shift"]] = sh
    dates = set(r["dates"])
    for key in ("assignments", "availability", "context"):
        if r.get(key) is not None and not isinstance(r[key], list):
            raise InputRefused(f"{key} must be a list")
        for a in r.get(key) or []:
            if not isinstance(a, dict) or not isinstance(a.get("date"), str) or not isinstance(a.get("shift"), str):
                raise InputRefused(f"{key} entries must be objects with text date and shift tokens")
            if a.get("date") not in dates or a.get("shift") not in shifts:
                raise InputRefused(f"{key} entry {a!r} names an unknown date or shift")
            if key != "context" and (not isinstance(a.get("staff_id"), str) or a["staff_id"] not in staff_ids):
                raise InputRefused(f"{key} entry {a!r} names an unknown staff_id")
            for field in ("place", "exception", "status", "census_band"):
                if a.get(field) is not None and not isinstance(a[field], str):
                    raise InputRefused(f"{key}.{field} must be text or null")
    return shifts


def rule_state(rules, rid):
    """(runnable, reason). A rule runs only if ratified (MED/HIGH) and every required parameter is set."""
    spec = (rules.get("rules") or {}).get(rid)
    if spec is None:
        return False, "not in the rule set"
    st = spec.get("status")
    if st == "KILLED":
        return False, "killed by the founder"
    if st not in RATIFIED:
        return False, f"unratified ({st or 'no status'}); LOW lines are excluded, not guessed"
    p = spec.get("params") or {}
    missing = [k for k in REQUIRED[rid] if p.get(k) is None]
    if missing:
        return False, "parameter unset: " + ", ".join(missing)
    return True, ""


def _abs_hours(date, sh):
    day = int(date[1:]) - 1
    start = day * 24 + sh["start_hour"]
    dur = (sh["end_hour"] - sh["start_hour"]) % 24 or 24
    return start, start + dur


def detect(roster, rules):
    """Return the run envelope. Never raises for a refused input: that is run_status ERROR."""
    env = {"detector_version": DETECTOR_VERSION, "rules_source": rules.get("source") if isinstance(rules, dict) else None, "rules_sha256": sha(rules),
           "input_sha256": sha(roster) if roster is not None else None, "rules_evaluated": [], "rules_skipped": [],
           "findings": [], "input_notes": []}
    if roster is None:
        env.update(run_status="NOT_RUN", reason="no input")
        return env
    if isinstance(roster, dict) and "__unparseable__" in roster:
        env.update(run_status="ERROR", reason="input is not valid JSON: " + roster["__unparseable__"][:120])
        return env
    if isinstance(roster, dict) and "__missing__" in roster:
        env.update(run_status="ERROR", reason="input file not found: " + roster["__missing__"])
        return env
    try:
        shifts = validate_input(roster)
    except InputRefused as ex:
        env.update(run_status="ERROR", reason=str(ex))
        return env
    bad = validate_rules(rules)
    if bad:   # R1: an impossible or mistyped ratified parameter is refused, never evaluated
        env.update(run_status="ERROR", reason="rule parameter invalid: " + "; ".join(bad))
        return env
    if not roster["dates"] or not shifts:   # R3: empty is not absent
        env.update(run_status="NOT_RUN", reason="empty roster: no date or no shift to evaluate")
        return env
    ef = roster.get("evaluate_from")
    if ef is not None and (not DATE_RE.match(str(ef)) or ef not in roster["dates"]):
        env.update(run_status="ERROR", reason="evaluate_from %r is not one of the roster's dates" % (ef,))
        return env
    carry = {d for d in roster["dates"] if ef is not None and int(d[1:]) < int(ef[1:])}
    if carry:
        env["carry_in_dates"] = sorted(carry, key=lambda d: int(d[1:]))
    staff = {s["staff_id"]: s for s in roster["staff"]}
    charge = {sid for sid, s in staff.items() if s.get("role") == "RN" and "charge" in (s.get("qualifications") or [])}
    blocks = [(d, s) for d in roster["dates"] for s in shifts]
    by_block = {b: [] for b in blocks}
    for a in roster["assignments"]:
        by_block[(a["date"], a["shift"])].append(a)
    unavail = {(a["staff_id"], a["date"], a["shift"]) for a in roster.get("availability") or [] if a.get("status") == "UNAVAILABLE"}
    band = {(c["date"], c["shift"]): c.get("census_band") for c in roster.get("context") or []}
    tok = {int(d[1:]): d for d in roster["dates"]}
    # R2 / R4: input-level notes about the roster itself (data validity, not clinical rules); they never replace findings
    seen_rows, spans = {}, {}
    for a in roster["assignments"]:
        key = (a["staff_id"], a["date"], a["shift"], a.get("place"))
        seen_rows[key] = seen_rows.get(key, 0) + 1
        spans.setdefault(a["staff_id"], set()).add((a["date"], a["shift"]))
    for (sid, d, s, pl), n in sorted(seen_rows.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        if n > 1:
            env["input_notes"].append({"type": "DUPLICATE_ASSIGNMENT", "rules": [], "date": d, "shift": s,
                                       "explanation": f"{sid} is listed {n} times on {d} {s} at {pl}; counted once by every rule."})
    for sid in sorted(spans):
        iv = sorted((_abs_hours(d, shifts[s]), d, s) for d, s in spans[sid])
        for ((a0, a1), d1, s1), ((b0, b1), d2, s2) in zip(iv, iv[1:]):
            if b0 < a1:
                env["input_notes"].append({"type": "OVERLAPPING_ASSIGNMENT", "rules": [], "date": d2, "shift": s2,
                                           "explanation": f"{sid} works {d1} {s1} and {d2} {s2}, whose hours overlap by {a1 - b0} h "
                                                          f"(two different blocks; H9 covers only the same block)."})
    runnable = {}
    for rid in IMPLEMENTED:
        ok, why = rule_state(rules, rid)
        runnable[rid] = ok
        if ok:
            env["rules_evaluated"].append(rid)
        else:
            env["rules_skipped"].append({"rule_id": rid, "scope": "all", "reason": why,
                                         "ratified": (rules.get("rules", {}).get(rid) or {}).get("status") in RATIFIED})
    h8 = False
    for rid in NOT_IMPLEMENTED:
        spec = (rules.get("rules") or {}).get(rid) or {}
        iface = INTERFACE_ONLY[rid]
        if spec.get("status") in RATIFIED and rid == "H8" and (spec.get("params") or {}).get("pairing_required") is not None \
                and any(s.get("orientee") for s in roster["staff"]):
            h8 = True   # R7: HYPOTHETICAL branch, runs only when ratified and the roster marks orientees
            env["rules_evaluated"].append("H8")
            continue
        reason = ("interface only (increment 1.2): ratified, but needs %s and parameters %s; nothing is guessed"
                  % (iface["data"], ", ".join(iface["params"])) if spec.get("status") in RATIFIED else
                  "not implemented in increment 1 (needs data the input does not carry)")
        env["rules_skipped"].append({"rule_id": rid, "scope": "all", "reason": reason, "ratified": spec.get("status") in RATIFIED})
    P = lambda rid: (rules["rules"][rid].get("params") or {})
    F = env["findings"]

    def finding(rid, sids, date, shift, text):
        if date in carry:   # R6: a carry-in date is context only
            return
        F.append({"rule_id": rid, "locator": {"staff_ids": sorted(sids), "date": date, "shift": shift},
                  "severity": "HARD", "explanation": text})

    if runnable["H1"]:
        p = P("H1")
        for (d, s), assigned in sorted(by_block.items()):
            if d in carry:   # R6: block rules are not evaluated on carry-in dates
                continue
            b = band.get((d, s))
            if b not in BANDS:
                pol = p["missing_band_policy"]
                if pol == "skip":
                    env["rules_skipped"].append({"rule_id": "H1", "scope": {"date": d, "shift": s},
                                                 "reason": f"census band {'missing' if b is None else 'unknown: ' + str(b)}"})
                    continue
                if pol == "refuse":
                    env.update(run_status="ERROR", reason=f"census band missing or unknown on {d} {s} (H1 policy: refuse)",
                               findings=[])
                    return env
                if pol not in BANDS:
                    env["rules_skipped"].append({"rule_id": "H1", "scope": {"date": d, "shift": s}, "reason": "missing_band_policy not understood"})
                    continue
                b = pol
            need = p["min_rn_by_band"].get(b)
            if need is None:
                env["rules_skipped"].append({"rule_id": "H1", "scope": {"date": d, "shift": s}, "reason": f"min_rn_by_band.{b} unset"})
                continue
            rns = sorted({a["staff_id"] for a in assigned if staff[a["staff_id"]].get("role") == "RN"
                          and not (h8 and staff[a["staff_id"]].get("orientee"))})   # R7: H8 text - an orientee does not count toward H1
            counted = len(rns) - (1 if (not p["charge_counts_toward_h1"] and any(x in charge for x in rns)) else 0)
            if counted < need:
                finding("H1", rns, d, s, f"{counted} RN counted on {d} {s} ({b} census) against a minimum of {need}.")
    if runnable["H2"]:
        for (d, s), assigned in sorted(by_block.items()):
            sids = sorted({a["staff_id"] for a in assigned})
            if not any(x in charge for x in sids):
                tail = ("nobody assigned." if not sids else f"assigned {', '.join(sids)}; "
                        + ("neither holds charge." if len(sids) == 2 else "none holds charge." if len(sids) > 2 else f"{sids[0]} does not hold charge."))
                finding("H2", sids, d, s, f"No charge-qualified RN on {d} {s}; {tail}")
    if runnable["H4"]:
        allowed = set(P("H4")["allowed_exceptions"])
        for a in sorted(roster["assignments"], key=lambda x: (x["date"], x["shift"], x["staff_id"])):
            if (a["staff_id"], a["date"], a["shift"]) in unavail and a.get("exception") not in allowed:
                finding("H4", [a["staff_id"]], a["date"], a["shift"],
                        f"{a['staff_id']} is scheduled on {a['date']} {a['shift']} but marked UNAVAILABLE"
                        + (f" (exception '{a['exception']}' is not an allowed exception)." if a.get("exception") else "."))
    if runnable["H5"]:
        p = P("H5")
        per = {}
        for a in roster["assignments"]:
            per.setdefault(a["staff_id"], set()).add((a["date"], a["shift"]))
        for sid in sorted(per):
            seq = sorted(per[sid], key=lambda x: _abs_hours(x[0], shifts[x[1]])[0])
            for (d1, s1), (d2, s2) in zip(seq, seq[1:]):
                e1 = _abs_hours(d1, shifts[s1])[1]
                st2 = _abs_hours(d2, shifts[s2])[0]
                rest = st2 - e1
                short = rest < p["min_rest_hours"] or (rest == p["min_rest_hours"] and not p["boundary_inclusive"])
                dan = (p["day_after_night_forbidden"] and s1 == "NIGHT" and s2 == "DAY" and int(d2[1:]) == int(d1[1:]) + 1)
                if short or dan:
                    why = (f"{rest} h of rest before {d2} {s2} (minimum {p['min_rest_hours']} h"
                           f"{', inclusive' if p['boundary_inclusive'] else ', exclusive'})" if short else
                           f"DAY on {d2} directly after NIGHT on {d1} (forbidden outright)")
                    finding("H5", [sid], d2, s2, f"{sid}: {why}.")
    if runnable["H6"]:
        mx = P("H6")["max_consecutive_shifts"]
        unit = P("H6").get("count_unit") or "calendar_day"   # R5: default = the 1.1 behaviour
        env["h6_count_unit"] = unit + (" (default; founder item W3.4 open)" if "count_unit" not in P("H6") else "")
        per_day = {}
        for a in roster["assignments"]:
            per_day.setdefault(a["staff_id"], {}).setdefault(int(a["date"][1:]), set()).add(a["shift"])
        for sid in sorted(per_day):
            run_len, prev, reported = 0, None, False
            for dn in sorted(per_day[sid]):
                add = 1 if unit == "calendar_day" else len(per_day[sid][dn])
                if prev is None or dn != prev + 1:
                    run_len, reported = 0, False
                run_len += add
                prev = dn
                d_tok = tok.get(dn, f"D{dn:02d}")
                if run_len > mx and not reported and d_tok not in carry:
                    reported = True
                    what = "consecutive days" if unit == "calendar_day" else "shifts on consecutive days"
                    finding("H6", [sid], d_tok, None, f"{sid} works {run_len} {what} to {d_tok}, above the maximum of {mx}.")
    if runnable["H9"]:
        ignore = set(P("H9")["not_separate_places"])
        for (d, s), assigned in sorted(by_block.items()):
            places = {}
            for a in assigned:
                if a.get("place") not in ignore:
                    places.setdefault(a["staff_id"], set()).add(a.get("place"))
            for sid, pl in sorted(places.items()):
                if len(pl) > 1:
                    finding("H9", [sid], d, s, f"{sid} is assigned to {len(pl)} places on {d} {s}: {', '.join(sorted(map(str, pl)))}.")
    # Input-level note (PROPOSED, annex A3): when H2 and H4 both apply, a block with no AVAILABLE charge-qualified
    # nurse cannot be satisfied by any roster. Reported beside the findings; it never replaces them.
    if runnable["H2"] and not charge:  # CR-T2: nobody on the staff list holds charge
        env["input_notes"].append({"type": "UNSATISFIABLE", "rules": ["H2"], "date": None, "shift": None,
                                   "explanation": "No one on the staff list holds the charge qualification: no roster from this staff list can satisfy H2."})
    if h8:   # R7 HYPOTHETICAL branch: an orientee needs their preceptor on the same block (rule text of H8; no number)
        pre = {s["staff_id"]: s.get("preceptor") for s in roster["staff"] if s.get("orientee")}
        for (d, s), assigned in sorted(by_block.items()):
            on = {a["staff_id"] for a in assigned}
            for sid in sorted(on & set(pre)):
                if P("H8").get("pairing_required") and pre[sid] not in on:
                    finding("H8", [sid], d, s, f"orientee {sid} is on {d} {s} without preceptor {pre[sid]} (HYPOTHETICAL H8 branch).")
    if runnable["H2"] and runnable["H4"]:
        for (d, s) in blocks:
            if d in carry:
                continue
            if charge and all((c, d, s) in unavail for c in charge):
                env["input_notes"].append({"type": "UNSATISFIABLE", "rules": ["H2", "H4"], "date": d, "shift": s,
                                           "explanation": f"No charge-qualified nurse is available on {d} {s}: no roster can satisfy H2 and H4 together."})
    F.sort(key=lambda f: (f["locator"]["date"] or "", f["locator"]["shift"] or "", f["rule_id"], f["locator"]["staff_ids"]))
    if not env["rules_evaluated"]:
        env.update(run_status="NOT_RUN", reason="no rule is ratified with its parameters filled; nothing was evaluated")
        return env
    env["run_status"] = "COMPLETED"
    return env


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True)
    ap.add_argument("--input")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules = json.load(open(a.rules, encoding="utf-8"))
    roster = None
    if a.input:
        try:
            roster = json.load(open(a.input, encoding="utf-8"))
        except FileNotFoundError:
            roster = {"__missing__": __import__("os").path.basename(a.input)}  # named but absent: ERROR, never "no input"
        except ValueError as ex:
            roster = {"__unparseable__": str(ex)}
    env = detect(roster, rules)
    text = json.dumps(env, indent=1, sort_keys=True, ensure_ascii=False)
    if a.out:
        try:
            with open(a.out, "x", encoding="utf-8", newline="\n") as f:
                f.write(text + "\n")
        except FileExistsError:
            print("REFUSED: output already exists; choose a new file", file=sys.stderr)
            return 2
    print(text)
    return {"COMPLETED": 0, "NOT_RUN": 3, "ERROR": 2}[env["run_status"]]


if __name__ == "__main__":
    sys.exit(main())
