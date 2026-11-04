#!/usr/bin/env python3
"""ii_measure.py -- track (ii) measurement kit (II-8b): detector vs the founder's own labels, blinded. Candidate, 2026-10-30.

The order is the design (brief §5 freeze list):
  1 make-set     a frozen, seeded set of synthetic rosters; every roster and the whole set are hashed
  2 seal         run the detector with the founder's RATIFIED rules; outputs are written and hashed BEFORE any label
                 exists, and nobody opens them
  3 label-sheet  a randomised, blinded sheet: one row per unit (roster, day, shift), the roster facts only; no
                 detector output and no generator intent
  4 lock-labels  the founder's filled sheet is hashed and locked BEFORE unblinding; later edits are recorded, not scored
  5 agreement    verifies the seal and the lock, then reports agreement with a roster-clustered bootstrap interval
The generator's perturbations are structural (a charge nurse removed, a nurse short, an unavailable nurse assigned,
a double booking, back-to-back shifts). They are not clinical thresholds and they are not labels: whether a unit is a
gap is the founder's judgment, and whether a rule fires is the detector's. Labels from a SIMULATED rater exist only to
test this pipeline; `agreement` refuses them unless --pipeline-test is passed, and then prints PIPELINE TEST.
The rater name given to lock-labels is a declaration. The code cannot tell who filled the sheet.

Colour review 2026-10-30 (review/COLOUR-REVIEW_track-ii_2026-10-30.md):
  CR-M1 the sheet records the seal it was issued after, and a later re-seal is refused
  CR-M2 a lock needs an issued sheet, and records the seal and the sheet
  CR-M3 agreement refuses a seal that differs from the one recorded at the lock
  CR-M4 unknown (and duplicate) unit ids are refused at the lock
  CR-M5 a unit where a ratified rule was skipped and nothing fired is 'not-evaluated' and is not scored
  CR-M6 under --unsure disagree, kappa, sensitivity and specificity use only the labels the rater gave
  CR-M7 the facts show, per nurse, the hours of rest since the previous shift and the days in a row
  CR-M8 the generator puts nobody on back-to-back blocks except by a recorded perturbation
  CR-M9 every sheet row names its set, and a sheet from another set is refused at the lock
  CR-M10 agreement before the lock is a refusal that names the next step, not a traceback
"""
import argparse, csv, hashlib, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "detector"))
import gapcheck as G  # noqa: E402

LABELS = {"gap", "no-gap", "unsure"}


def h_bytes(b):
    return hashlib.sha256(b).hexdigest()


def h_file(p):
    with open(p, "rb") as f:
        return h_bytes(f.read())


def write_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:   # 1.2 (T2-W01): LF on every OS, so hashes match across OSes
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")


GENERATOR = {  # HYPOTHETICAL generator settings: they shape the set only. They are not clinical rules or the founder's numbers.
    "staff": "10 RNs, S01-S03 charge-qualified", "availability": 0.8, "band_weights": {"low": 2, "normal": 5, "high": 2, "surge": 1},
    "staffing_target_by_band": {"low": 2, "normal": 3, "high": 4, "surge": 4},
    "never_back_to_back_unless_perturbed": True,
    "perturbation_rates_per_block": {"charge removed": 0.10, "one short": 0.10, "unavailable nurse assigned": 0.05,
                                     "back-to-back shift": 0.05, "double booking": 0.03}}


def make_set(out, n, days, seed, unit):
    """CR-M8: the first kit drew each block independently, so a nurse often worked the block straight after her last
    (0 h of rest) by accident; under any H5 minimum most units would have been gaps by chance. Now nobody works two
    blocks back to back unless the 'back-to-back shift' perturbation puts them there, and natural shortfalls are recorded."""
    if os.path.exists(out):
        raise SystemExit("REFUSED: set output already exists; use a new directory to preserve frozen evidence")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1 or isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 999:
        raise SystemExit("REFUSED: n must be positive and days must be between 1 and 999")
    if unit not in ("both", "nights"):
        raise SystemExit("REFUSED: unit must be both or nights")
    rng = random.Random(f"ii-set:{seed}")
    staff = [{"staff_id": f"S{i:02d}", "role": "RN", "qualifications": ["charge"] if i <= 3 else []} for i in range(1, 11)]
    shifts = [{"shift": "DAY", "start_hour": 7, "end_hour": 19}, {"shift": "NIGHT", "start_hour": 19, "end_hour": 7}]
    dates = [f"D{d:02d}" for d in range(1, days + 1)]
    want, rate = GENERATOR["staffing_target_by_band"], GENERATOR["perturbation_rates_per_block"]
    rosters, intent = {}, {}
    for k in range(1, n + 1):
        rid = f"R{k:03d}"
        ctx, avail, asg, events, last, bi = [], [], [], [], {}, -1
        for d in dates:
            for sh in shifts:                      # DAY then NIGHT: time order
                bi += 1
                band = rng.choices(tuple(GENERATOR["band_weights"]), tuple(GENERATOR["band_weights"].values()))[0]
                ctx.append({"date": d, "shift": sh["shift"], "census_band": band})
                ok, off = [], []
                for s in staff:
                    st = "AVAILABLE" if rng.random() < GENERATOR["availability"] else "UNAVAILABLE"
                    avail.append({"staff_id": s["staff_id"], "date": d, "shift": sh["shift"], "status": st})
                    (ok if st == "AVAILABLE" else off).append(s["staff_id"])
                rested = [x for x in ok if last.get(x) != bi - 1]
                rng.shuffle(rested)
                chg = [x for x in rested if int(x[1:]) <= 3]
                pick = ([chg[0]] if chg else []) + [x for x in rested if x not in chg[:1]]
                pick = pick[:want[band]]
                ev = []
                if not chg:
                    ev.append("no rested charge nurse available")
                if len(pick) < want[band]:
                    ev.append("fewer rested nurses than the generator target")
                if pick and pick[0] in chg and rng.random() < rate["charge removed"]:
                    alt = [x for x in rested if int(x[1:]) > 3 and x not in pick]
                    if alt:
                        pick[0] = alt[0]; ev.append("charge removed")
                if len(pick) > 1 and rng.random() < rate["one short"]:
                    pick.pop(); ev.append("one short")
                if rng.random() < rate["unavailable nurse assigned"]:
                    cand = sorted(x for x in off if last.get(x) != bi - 1)
                    if cand:
                        pick.append(rng.choice(cand)); ev.append("unavailable nurse assigned")
                if rng.random() < rate["back-to-back shift"]:
                    tired = sorted(x for x in ok if last.get(x) == bi - 1 and x not in pick)
                    if tired:
                        pick.append(rng.choice(tired)); ev.append("back-to-back shift")
                for x in pick:
                    asg.append({"staff_id": x, "date": d, "shift": sh["shift"], "place": "ED"})
                    last[x] = bi
                if pick and rng.random() < rate["double booking"]:
                    asg.append({"staff_id": pick[-1], "date": d, "shift": sh["shift"], "place": "float"}); ev.append("double booking")
                if ev:
                    events.append({"date": d, "shift": sh["shift"], "events": ev})
        rosters[rid] = {"provenance": {"synthetic": True, "generator": "ii_measure.make_set", "seed": seed, "roster": rid},
                        "staff": staff, "shifts": shifts, "dates": dates, "context": ctx, "availability": avail, "assignments": asg}
        intent[rid] = events
    for rid, r in rosters.items():
        write_json(os.path.join(out, "rosters", rid + ".json"), r)
    write_json(os.path.join(out, "SEALED", "generator-intent.json"), intent)
    units = [(rid, d, s["shift"]) for rid in rosters for d in dates for s in shifts if unit == "both" or s["shift"] == "NIGHT"]
    man = {"schema": "ii-roster-set/1", "n_rosters": n, "days": days, "seed": seed, "unit": unit, "n_units": len(units),
           "generator_sha256": h_file(os.path.abspath(__file__)), "generator_settings_HYPOTHETICAL": GENERATOR,
           "rosters": {rid: h_file(os.path.join(out, "rosters", rid + ".json")) for rid in sorted(rosters)},
           "sealed_intent_sha256": h_file(os.path.join(out, "SEALED", "generator-intent.json"))}
    man["set_sha256"] = h_bytes(json.dumps(man["rosters"], sort_keys=True).encode())
    write_json(os.path.join(out, "SET-MANIFEST.json"), man)
    return man


def load_set(d):
    man = json.load(open(os.path.join(d, "SET-MANIFEST.json"), encoding="utf-8"))
    for rid, hv in man["rosters"].items():
        if h_file(os.path.join(d, "rosters", rid + ".json")) != hv:
            raise SystemExit(f"REFUSED: roster {rid} changed after the set was frozen")
    return man


def units_of(man, d):
    out = []
    for rid in sorted(man["rosters"]):
        r = json.load(open(os.path.join(d, "rosters", rid + ".json"), encoding="utf-8"))
        for date in r["dates"]:
            for sh in r["shifts"]:
                if man["unit"] == "both" or sh["shift"] == "NIGHT":
                    out.append((rid, date, sh["shift"]))
    return out


def seal(d, rules_path):
    man = load_set(d)
    if os.path.exists(os.path.join(d, "LABELS-LOCK.json")):
        raise SystemExit("REFUSED: labels are already locked; sealing after labelling would break the blinding order")
    if os.path.exists(os.path.join(d, "LABEL-SHEET.json")):
        raise SystemExit("REFUSED: the label sheet was already issued after the earlier seal; sealing again now would let the rules "
                         "follow the labels. Make a new set for new rules")
    rules = json.load(open(rules_path, encoding="utf-8"))
    outs = {}
    for rid in sorted(man["rosters"]):
        env = G.detect(json.load(open(os.path.join(d, "rosters", rid + ".json"), encoding="utf-8")), rules)
        p = os.path.join(d, "SEALED", "detector", rid + ".json")
        write_json(p, env)
        outs[rid] = h_file(p)
    s = {"rules_sha256": h_file(rules_path), "rules_source": rules.get("source"), "detector_version": G.DETECTOR_VERSION,
         "detector_sha256": h_file(os.path.abspath(G.__file__)), "kit_sha256": h_file(os.path.abspath(__file__)),
         "outputs": outs, "set_sha256": man["set_sha256"]}
    write_json(os.path.join(d, "DETECTOR-SEAL.json"), s)
    return s


def render(r, date, shift):
    """The roster facts for one unit, per assigned nurse: charge, marked unavailable, place(s), hours of rest since that
    nurse's previous shift, and days in a row. Facts only: no rule, threshold or verdict. (CR-M7: the earlier text showed
    only who worked the previous night, so a DAY-then-NIGHT double on one date was invisible to the rater.)"""
    shifts = {s["shift"]: s for s in r["shifts"]}
    q = {s["staff_id"]: s for s in r["staff"]}
    off = {x["staff_id"] for x in r.get("availability") or [] if x["date"] == date and x["shift"] == shift and x["status"] == "UNAVAILABLE"}
    band = next((c.get("census_band") for c in r.get("context") or [] if c["date"] == date and c["shift"] == shift), None)
    here = {}
    for x in r["assignments"]:
        if x["date"] == date and x["shift"] == shift:
            here.setdefault(x["staff_id"], set()).add(str(x.get("place")))
    start = G._abs_hours(date, shifts[shift])[0]
    parts = []
    for sid in sorted(here):
        mine = sorted({(G._abs_hours(a["date"], shifts[a["shift"]]), a["date"], a["shift"]) for a in r["assignments"] if a["staff_id"] == sid})
        before = [b for b in mine if b[0][0] < start]
        if before:
            (_, end), pd, ps = before[-1]
            rest = f"rest {start - end} h since {pd} {ps}" if start >= end else f"overlaps {pd} {ps}"
        else:
            rest = "first shift in the roster"
        worked, run = {int(a["date"][1:]) for a in r["assignments"] if a["staff_id"] == sid}, 1
        while int(date[1:]) - run in worked:
            run += 1
        tag = " (charge)" if "charge" in (q[sid].get("qualifications") or []) else ""
        parts.append(f"{sid}{tag}{' [marked UNAVAILABLE]' if sid in off else ''} @ {'+'.join(sorted(here[sid]))}, {rest}, day {run} in a row")
    rns = sum(1 for sid in here if q[sid].get("role") == "RN")
    return f"census {band}; {rns} RN assigned: {'; '.join(parts) or 'nobody'}"


def label_sheet(d, out_csv):
    man = load_set(d)
    if not os.path.exists(os.path.join(d, "DETECTOR-SEAL.json")):
        raise SystemExit("REFUSED: seal the detector outputs before the label sheet exists (blinding order)")
    if os.path.exists(os.path.join(d, "LABELS-LOCK.json")):
        raise SystemExit("REFUSED: labels are already locked; a new sheet is not issued after the lock")
    us = units_of(man, d)
    random.Random(man["set_sha256"]).shuffle(us)
    rows = []
    for i, (rid, date, sh) in enumerate(us, 1):
        r = json.load(open(os.path.join(d, "rosters", rid + ".json"), encoding="utf-8"))
        rows.append({"order": i, "unit_id": f"{rid}/{date}/{sh}", "set": man["set_sha256"][:12], "roster": rid, "date": date, "shift": sh,
                     "facts": render(r, date, sh), "label (gap / no-gap / unsure)": "", "note": ""})
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    write_json(os.path.join(d, "LABEL-SHEET.json"), {"sheet_sha256": h_file(out_csv), "n_units": len(rows),
                                                     "seal_sha256": h_file(os.path.join(d, "DETECTOR-SEAL.json"))})
    return len(rows)


def read_labels(p):
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    lab = {}
    for r in rows:
        v = (r.get("label (gap / no-gap / unsure)") or "").strip().lower()
        if v:
            if v not in LABELS:
                raise SystemExit(f"REFUSED: unit {r['unit_id']} has label {v!r}; allowed: {sorted(LABELS)}")
            if r["unit_id"] in lab:
                raise SystemExit(f"REFUSED: unit {r['unit_id']} is labelled twice")
            lab[r["unit_id"]] = v
    return lab


def _need(d, name, step):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        raise SystemExit(f"REFUSED: {name} is missing; run {step} first (order: make-set, seal, label-sheet, lock-labels, agreement)")
    return p


def lock_labels(d, labels_csv, rater):
    man = load_set(d)
    if os.path.exists(os.path.join(d, "LABELS-LOCK.json")):
        raise SystemExit("REFUSED: labels are already locked; a later edit is recorded separately, never re-locked")
    sheet = json.load(open(_need(d, "LABEL-SHEET.json", "label-sheet"), encoding="utf-8"))
    seal_hash = h_file(_need(d, "DETECTOR-SEAL.json", "seal"))
    if seal_hash != sheet["seal_sha256"]:
        raise SystemExit("REFUSED: the detector seal changed after the label sheet was issued")
    with open(labels_csv, newline="", encoding="utf-8") as f:
        sets = {(r.get("set") or "").strip() for r in csv.DictReader(f)}
    if sets != {man["set_sha256"][:12]}:   # CR-M9: unit ids repeat across sets, so a sheet from another set must not lock here
        raise SystemExit(f"REFUSED: the labels file belongs to another set (set column {sorted(sets)}; this set is {man['set_sha256'][:12]})")
    lab = read_labels(labels_csv)
    expected = {f"{a}/{b}/{c}" for a, b, c in units_of(man, d)}
    unknown = sorted(set(lab) - expected)
    if unknown:
        raise SystemExit(f"REFUSED: {len(unknown)} labelled unit(s) are not in this set, e.g. {unknown[:3]}")
    missing = sorted(expected - set(lab))
    if missing:
        raise SystemExit(f"REFUSED: {len(missing)} unit(s) unlabelled, e.g. {missing[:3]}; every unit needs a label before the lock")
    lock = {"labels_sha256": h_file(labels_csv), "rater": rater, "rater_is_a_declaration": True, "n_units": len(lab),
            "seal_sha256": seal_hash, "sheet_sha256": sheet["sheet_sha256"],
            "counts": {k: sum(1 for v in lab.values() if v == k) for k in sorted(LABELS)}}
    write_json(os.path.join(d, "LABELS-LOCK.json"), lock)
    return lock


def verdicts(d, man, seal_rec):
    """gap if any finding falls on the unit (a day-level finding, shift None, falls on both shifts of that date);
    not-evaluated if no finding falls on it and a ratified rule was skipped for its block; otherwise no-gap."""
    v = {}
    for rid in sorted(man["rosters"]):
        p = os.path.join(d, "SEALED", "detector", rid + ".json")
        if h_file(p) != seal_rec["outputs"][rid]:
            raise SystemExit(f"REFUSED: sealed detector output {rid} changed after sealing")
        env = json.load(open(p, encoding="utf-8"))
        if env["run_status"] != "COMPLETED":
            raise SystemExit(f"REFUSED: the detector did not run on {rid} ({env['run_status']}): no verdict can be scored")
        hit = {(f["locator"]["date"], f["locator"]["shift"]) for f in env["findings"]}
        days = {f["locator"]["date"] for f in env["findings"] if f["locator"]["shift"] is None}
        skipped = {(s["scope"]["date"], s["scope"]["shift"]) for s in env["rules_skipped"] if isinstance(s.get("scope"), dict)}
        incomplete = any(s.get("scope") == "all" and s.get("ratified") for s in env["rules_skipped"])
        r = json.load(open(os.path.join(d, "rosters", rid + ".json"), encoding="utf-8"))
        for date in r["dates"]:
            for sh in r["shifts"]:
                b = (date, sh["shift"])
                v[f"{rid}/{date}/{sh['shift']}"] = ("gap" if (b in hit or date in days) else "not-evaluated" if incomplete or b in skipped else "no-gap")
    return v


def stats(pairs):
    n = len(pairs)
    a = sum(1 for x, y in pairs if x == "gap" and y == "gap"); b = sum(1 for x, y in pairs if x == "gap" and y == "no-gap")
    c = sum(1 for x, y in pairs if x == "no-gap" and y == "gap"); dd = n - a - b - c
    po = (a + dd) / n if n else None
    pe = (((a + b) * (a + c)) + ((c + dd) * (b + dd))) / (n * n) if n else None
    kappa = (po - pe) / (1 - pe) if n and pe is not None and pe < 1 else None
    return {"n": n, "both_gap": a, "detector_only": b, "founder_only": c, "both_no_gap": dd, "agreement": po, "kappa": kappa,
            "detector_sensitivity_vs_rater": a / (a + c) if (a + c) else None, "detector_specificity_vs_rater": dd / (b + dd) if (b + dd) else None}


def agreement(d, labels_csv, unsure="exclude", pipeline_test=False, reps=5000):
    man = load_set(d)
    lock = json.load(open(_need(d, "LABELS-LOCK.json", "lock-labels"), encoding="utf-8"))
    seal_path = _need(d, "DETECTOR-SEAL.json", "seal")
    if h_file(seal_path) != lock["seal_sha256"]:
        raise SystemExit("REFUSED: DETECTOR-SEAL.json differs from the seal recorded at the lock; the detector outputs were replaced")
    seal_rec = json.load(open(seal_path, encoding="utf-8"))
    if h_file(labels_csv) != lock["labels_sha256"]:
        raise SystemExit("REFUSED: the labels file differs from the locked labels; post-unblinding edits are recorded, not scored")
    if lock["rater"] != "founder" and not pipeline_test:
        raise SystemExit(f"REFUSED: rater is {lock['rater']!r}; only founder labels produce a result (use --pipeline-test for a test)")
    lab = read_labels(labels_csv)
    det = verdicts(d, man, seal_rec)
    pairs, definite, excluded, not_eval = [], [], 0, 0
    by_roster = {}
    for uid, y in sorted(lab.items()):
        if det[uid] == "not-evaluated":
            not_eval += 1; continue                               # the detector made no full judgment here
        if y == "unsure":
            if unsure == "exclude":
                excluded += 1; continue
            y = "no-gap" if det[uid] == "gap" else "gap"          # 'disagree': an unsure label counts against agreement
        else:
            definite.append((det[uid], y))
        pairs.append((det[uid], y))
        by_roster.setdefault(uid.split("/")[0], []).append((det[uid], y))
    if not pairs:
        raise SystemExit("REFUSED: no unit can be scored (every unit is unsure or not evaluated)")
    res = stats(pairs)
    if unsure == "disagree":   # CR-M6: never compute kappa, sensitivity or specificity from a label the rater did not give
        d2 = stats(definite)
        res.update({k: d2[k] for k in ("kappa", "detector_sensitivity_vs_rater", "detector_specificity_vs_rater")})
        res["kappa_sens_spec_basis"] = "definite labels only; unsure units count only against agreement"
    res["not_evaluated_excluded"] = not_eval
    rng = random.Random(f"ii-boot:{man['set_sha256']}")
    keys = sorted(by_roster)
    boots = []
    for _ in range(reps):
        smp = [p for k in (keys[rng.randrange(len(keys))] for _ in keys) for p in by_roster[k]]
        boots.append(stats(smp)["agreement"])
    boots.sort()
    res.update({"agreement_95ci_roster_bootstrap": [boots[int(0.025 * reps)], boots[int(0.975 * reps) - 1]], "bootstrap_reps": reps,
                "unsure_policy": unsure, "unsure_excluded": excluded, "rater": lock["rater"], "rules_sha256": seal_rec["rules_sha256"],
                "detector_version": seal_rec.get("detector_version"), "detector_sha256": seal_rec.get("detector_sha256"),
                "kit_sha256_at_seal": seal_rec.get("kit_sha256"), "kit_sha256_now": h_file(os.path.abspath(__file__)),
                "set_sha256": man["set_sha256"], "pipeline_test": bool(pipeline_test),
                "label": "PIPELINE TEST - NOT A RESULT" if pipeline_test else "detector vs this one rater (not vs truth)"})
    return res


def wilson(k, n, z=1.96):
    import math
    p = k / n; dn = 1 + z * z / n; c = (p + z * z / (2 * n)) / dn
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / dn
    return c - hw, c + hw


def reachability(ns=(60, 100, 140, 200), ps=(0.7, 0.8, 0.9, 0.95), thresholds=(0.7, 0.8, 0.9)):
    """Wilson 95% intervals for agreement, and the smallest observed agreement whose lower bound clears a HYPOTHETICAL
    threshold. Both ignore clustering by roster, so they are optimistic: the real, roster-clustered interval is wider."""
    out = [{"units": n, "agreement": p, "wilson_95": [round(x, 3) for x in wilson(round(p * n), n)]} for n in ns for p in ps]
    for n in ns:
        for t in thresholds:
            k = next((k for k in range(n + 1) if wilson(k, n)[0] >= t), None)
            out.append({"units": n, "hypothetical_threshold_for_the_lower_bound": t,
                        "smallest_observed_agreement_that_clears_it": round(k / n, 3) if k is not None else None,
                        "disqualifier_reachable": k is not None and k > 0})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("make-set"); p.add_argument("--out", required=True); p.add_argument("--n", type=int, required=True)
    p.add_argument("--days", type=int, default=7); p.add_argument("--seed", required=True); p.add_argument("--unit", choices=("nights", "both"), required=True)
    p = sp.add_parser("seal"); p.add_argument("--set", required=True); p.add_argument("--rules", required=True)
    p = sp.add_parser("label-sheet"); p.add_argument("--set", required=True); p.add_argument("--out", required=True)
    p = sp.add_parser("lock-labels"); p.add_argument("--set", required=True); p.add_argument("--labels", required=True); p.add_argument("--rater", required=True)
    p = sp.add_parser("agreement"); p.add_argument("--set", required=True); p.add_argument("--labels", required=True)
    p.add_argument("--unsure", choices=("exclude", "disagree"), required=True); p.add_argument("--pipeline-test", action="store_true")
    sp.add_parser("reachability")
    a = ap.parse_args(argv)
    if a.cmd == "make-set":
        print(json.dumps(make_set(a.out, a.n, a.days, a.seed, a.unit), indent=1)[:600])
    elif a.cmd == "seal":
        s = seal(a.set, a.rules); print(f"sealed {len(s['outputs'])} detector outputs; do not open SEALED/ before the labels are locked")
    elif a.cmd == "label-sheet":
        print(f"label sheet written: {label_sheet(a.set, a.out)} units")
    elif a.cmd == "lock-labels":
        print(json.dumps(lock_labels(a.set, a.labels, a.rater), indent=1))
    elif a.cmd == "agreement":
        print(json.dumps(agreement(a.set, a.labels, a.unsure, a.pipeline_test), indent=1))
    elif a.cmd == "reachability":
        print(json.dumps(reachability(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
