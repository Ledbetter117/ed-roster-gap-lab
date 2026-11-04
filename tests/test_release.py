"""Regression checks for the portable release. All inputs are constructed."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "measure"))
import ii_measure as M
spec = importlib.util.spec_from_file_location("release_runner", ROOT / "run_ed_ii.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
results = []


def check(name, ok):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name)


def refused(fn):
    try:
        fn()
    except SystemExit as exc:
        return "REFUSED" in str(exc)
    return False


with tempfile.TemporaryDirectory(prefix="edii-release-") as temp:
    base = Path(temp)
    frozen = base / "frozen"
    M.make_set(str(frozen), 1, 1, "regression", "nights")
    original = {str(x.relative_to(frozen)): x.read_bytes() for x in frozen.rglob("*") if x.is_file()}
    check("set-reuse-refused", refused(lambda: M.make_set(str(frozen), 2, 2, "different", "both")))
    check("frozen-evidence-preserved", original == {str(x.relative_to(frozen)): x.read_bytes() for x in frozen.rglob("*") if x.is_file()})
    for name, n, days, unit in [("zero-rosters", 0, 7, "both"), ("zero-days", 1, 0, "both"),
                                 ("day-overflow", 1, 1000, "both"), ("invalid-unit", 1, 7, "day")]:
        target = base / name
        check(name, refused(lambda: M.make_set(str(target), n, days, "test", unit)) and not target.exists())
    rules_path = base / "partial-rules.json"
    rules_path.write_text(json.dumps({"source": "CONSTRUCTED TEST ONLY", "rules": {
        "H1": {"status": "HIGH", "params": {"min_rn_by_band": {"low": 0, "normal": 0, "high": 0, "surge": 0},
                "charge_counts_toward_h1": True, "missing_band_policy": "refuse"}},
        "H3": {"status": "HIGH", "params": {"min_by_competency": {"test": 1}}}}}), encoding="utf8")
    seal_rec = M.seal(str(frozen), str(rules_path))
    check("unsupported-ratified-rule-is-not-no-gap", set(M.verdicts(str(frozen), M.load_set(str(frozen)), seal_rec).values()) == {"not-evaluated"})
    rs = json.loads(rules_path.read_text())
    rs["rules"]["H3"]["status"] = "LOW"
    rules_path.write_text(json.dumps(rs), encoding="utf8")
    seal_rec = M.seal(str(frozen), str(rules_path))
    check("unratified-rule-does-not-block-evaluation", set(M.verdicts(str(frozen), M.load_set(str(frozen)), seal_rec).values()) == {"no-gap"})
    non_rn = json.loads((ROOT / "fixtures/LEGAL-PC-01.json").read_text(encoding="utf8"))
    for staff in non_rn["staff"]:
        if "charge" in staff.get("qualifications", []):
            staff["role"] = "LPN"
    non_rn_result = M.G.detect(non_rn, {"source": "CONSTRUCTED TEST ONLY", "rules": {"H2": {"status": "HIGH", "params": {}}}})
    check("h2-charge-must-be-rn", len([x for x in non_rn_result["findings"] if x["rule_id"] == "H2"]) == len(non_rn["dates"]) * len(non_rn["shifts"]))
    render_demo, render_checks = base / "render-demo.json", base / "render-checks.json"
    render_demo.write_text('{}', encoding="utf8")
    render_checks.write_text('{"verdict": "PASS"}', encoding="utf8")
    def render():
        return subprocess.run([sys.executable, "-B", str(ROOT / "tools/render_evidence.py"), "--demo", str(render_demo), "--checks", str(render_checks)], capture_output=True, text=True)
    rendered = render()
    check("renderer-refuses-unbound-evidence", rendered.returncode != 0 and "REFUSED" in rendered.stderr)
    render_checks.write_text(json.dumps({"verdict": "PASS", "source_sha256": {"run_ed_ii.py": hashlib.sha256((ROOT / "run_ed_ii.py").read_bytes()).hexdigest()}}), encoding="utf8")
    render_demo.write_text(json.dumps({"results": {"founder_template": "NOT_RUN", "A": {"exclude": {"pipeline_test": False, "rater": "founder"}}, "B": {}}}), encoding="utf8")
    rendered = render()
    check("renderer-refuses-human-label-evidence", rendered.returncode != 0 and "only simulated pipeline evidence" in rendered.stderr)
    root = base / "release"
    (root / "detector").mkdir(parents=True)
    detector = root / "detector/gapcheck.py"
    detector.write_text("from pathlib import Path\nPath('EXECUTED').write_text('yes')\n", encoding="utf8")
    R.HERE = root
    def seal():
        (root / "MANIFEST.json").write_text(json.dumps({"files": [{"path": "detector/gapcheck.py", "sha256": hashlib.sha256(detector.read_bytes()).hexdigest()}]}), encoding="utf8")
    def invoke(command):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return R.run(command)
    check("missing-manifest-refuses-child", invoke(["detect"]) == 4 and not (root / "EXECUTED").exists())
    seal()
    check("clean-manifest-allows-child", invoke(["detect"]) == 0 and (root / "EXECUTED").exists())
    (root / "EXECUTED").unlink()
    detector.write_text(detector.read_text() + "# changed\n", encoding="utf8")
    check("drift-refuses-child", invoke(["detect"]) == 4 and not (root / "EXECUTED").exists())
    for command in ["demo", "checks", "measure"]:
        check(command + "-drift-refuses", invoke([command]) == 4 and not (root / "runs").exists())
    detector.write_text("from pathlib import Path\np=Path(__file__)\np.write_text(p.read_text()+'# changed\\n')\n", encoding="utf8")
    seal()
    check("post-run-drift-fails", invoke(["detect"]) == 4)
    (root / "MANIFEST.json").write_text('{"files": []}', encoding="utf8")
    check("empty-manifest-refused", invoke(["verify"]) == 4)
    (root / "MANIFEST.json").write_text('{"files": [{"path": "../outside", "sha256": "x"}]}', encoding="utf8")
    check("unsafe-manifest-refused", invoke(["verify"]) == 4)
    (root / "MANIFEST.json").write_text('{broken', encoding="utf8")
    check("malformed-manifest-refused", invoke(["verify"]) == 4)

failed = len(results) - sum(results)
print(f"{sum(results)} PASS · {failed} FAIL")
sys.exit(1 if failed else 0)
