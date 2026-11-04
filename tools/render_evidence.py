"""Render public evidence and the manuscript from an already completed demo/check run."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=Path, required=True)
    ap.add_argument("--checks", type=Path, required=True)
    args = ap.parse_args()
    raw = json.loads(args.demo.read_text(encoding="utf-8"))
    checks = json.loads(args.checks.read_text(encoding="utf-8"))
    if checks["verdict"] != "PASS" or not checks.get("source_sha256"):
        raise SystemExit("REFUSED: passing check record with source hashes required")
    for name, expected in checks["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise SystemExit("REFUSED: source changed since checks: " + name)
    branches = [name for name in raw["results"] if name != "founder_template"]
    if len(branches) != 2:
        raise SystemExit("REFUSED: the report expects exactly two demo branches")
    result = raw["results"]
    for branch in branches:
        for policy in ("exclude", "disagree"):
            record = result[branch][policy]
            if not record["pipeline_test"] or record["rater"] != "SIMULATED":
                raise SystemExit("REFUSED: this publication renderer accepts only simulated pipeline evidence")
            if record["detector_sha256"] != sha(ROOT / "detector/gapcheck.py") or record["kit_sha256_at_seal"] != sha(ROOT / "measure/ii_measure.py"):
                raise SystemExit("REFUSED: source changed since demo")
    sets = [args.demo.parent / "scratch" / branch / "set/SET-MANIFEST.json" for branch in branches]
    man = json.loads(sets[0].read_text(encoding="utf-8"))
    a, b = (result[branch]["exclude"]["agreement"] for branch in branches)
    total_checks = sum(row["pass"] for row in checks["suites"].values())
    total_mutants = sum(row["total"] for row in checks["mutations"].values())
    table = ["Table 2. Synthetic pipeline outputs; SIMULATED rater only.", "",
             "| Branch | Unsure policy | Scored units | Agreement | 95% roster interval | Kappa |",
             "|---|---|---:|---:|---|---:|"]
    for i, branch in enumerate(branches):
        for policy in ("exclude", "disagree"):
            r = result[branch][policy]
            lo, hi = r["agreement_95ci_roster_bootstrap"]
            table.append(f"| {'A' if i == 0 else 'B'} | {policy} | {r['n']} | {r['agreement']:.3f} | {lo:.3f}–{hi:.3f} | {r['kappa']:.3f} |")
    validation = ["Table 1. Local software checks; constructed inputs only.", "",
                  "| Check group | Passed/caught | Failed/uncaught |", "|---|---:|---:|"]
    for name, row in checks["suites"].items():
        validation.append(f"| {name} | {row['pass']} | {row['fail']} |")
    for name, row in checks["mutations"].items():
        validation.append(f"| {name} | {row['caught']}/{row['total']} | {row['total'] - row['caught']} |")
    values = {"check_total": total_checks, "mutant_total": total_mutants, "rosters": man["n_rosters"], "days": man["days"],
              "units": man["n_units"], "agreement_a": f"{a:.3f}", "agreement_b": f"{b:.3f}",
              "delta_pp": f"{(a-b)*100:.1f}", "bootstrap_reps": result[branches[0]]["exclude"]["bootstrap_reps"],
              "unsure": result[branches[0]]["labels"]["unsure"], "python_version": checks["python"].split("\n")[0],
              "validation_table": "\n".join(validation), "demo_table": "\n".join(table)}
    text = (ROOT / "paper/MANUSCRIPT.md.in").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    if re.search(r"\{\{[^}]+\}\}", text):
        raise SystemExit("REFUSED: manuscript has an unresolved value")
    public_checks = {k: v for k, v in checks.items() if k not in ("kit", "executable", "temp_residue")}
    public_checks["platform"] = "Windows" if "win32" in checks["python"].lower() or "MSC" in checks["python"] else "see python field"
    evidence = {"evidence_type": "SYNTHETIC SOFTWARE CHECK; NOT A HUMAN STUDY", "raw_demo_sha256": sha(args.demo),
                "raw_checks_sha256": sha(args.checks), "set_manifest_sha256": [sha(path) for path in sets],
                "source_sha256": checks["source_sha256"]}
    for name, obj in [("demo-results.json", result), ("validation-results.json", public_checks), ("EVIDENCE-SOURCES.json", evidence)]:
        (ROOT / "docs" / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    (ROOT / "paper/MANUSCRIPT.md").write_text(text, encoding="utf-8", newline="\n")
    results = "# Results: software checks and simulated demonstration\n\n**No human agreement result is available.** All demonstration labels are SIMULATED.\n\n"
    results += "\n".join(validation) + "\n\n" + "\n".join(table)
    results += "\n\nBranch A uses inclusive rest and calendar-day counts. Branch B changes both to exclusive rest and shift counts. The comparison does not isolate either change.\n\n"
    results += f"Generated set: {man['n_rosters']} rosters × {man['days']} days × 2 shifts = {man['n_units']} units; seed `{man['seed']}`. Simulated label counts: `{result[branches[0]]['labels']}`.\n\n"
    results += "The full result JSON, source hashes, and validation summary are adjacent to this file. The original human endpoint remains pending. See METHODS.md and LIMITATIONS.md before interpreting any number.\n"
    (ROOT / "docs/RESULTS.md").write_text(results, encoding="utf-8", newline="\n")
    macro_manifest = {"macros": [{"name": key, "value": value, "classification": "TRACED",
                                  "source_chain": "saved demo/check JSON -> tools/render_evidence.py -> paper/MANUSCRIPT.md"}
                                 for key, value in values.items()], "bare_numbers": [],
                      "scope": "Generated empirical-looking values and tables; source/version labels, rule IDs, bibliographic years are identifiers, not study outcomes."}
    (ROOT / "paper/MANUSCRIPT-macro-manifest.json").write_text(json.dumps(macro_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered manuscript and results: {total_checks} checks, {total_mutants} mutants, {man['n_units']} simulated units")


if __name__ == "__main__":
    main()
