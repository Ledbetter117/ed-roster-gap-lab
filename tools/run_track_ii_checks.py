"""run_track_ii_checks.py (ORCA-ED-DELIVER-NOW-20261103-r1): run the Track (ii) kit's own checks on a COPY of a kit folder.

Copies <kit> to a new temporary folder (the kit is never written), then runs, with this interpreter:
  tests/test_gapcheck.py, tests/test_measure.py, tests/test_gapcheck_r12.py      (each prints "N PASS · M FAIL")
  tests/mutation_gapcheck.py, tests/mutation_measure.py, tests/mutation_gapcheck_r12.py   (planted defects; each must be caught)
Writes <out>/TRACK-II-CHECKS-<python>.json and one log per run. Exit 0 when every suite ends with 0 FAIL and every mutant is caught.
Usage: python -B run_track_ii_checks.py <kit> <out>"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

SUITES = ["test_gapcheck.py", "test_measure.py", "test_gapcheck_r12.py", "test_release.py", "test_security.py"]
MUTATIONS = ["mutation_gapcheck.py", "mutation_measure.py", "mutation_gapcheck_r12.py"]


def run(cmd, cwd, log):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"))
    Path(log).write_text("# %s\n# exit %s seconds %.1f\n%s\n--- stderr ---\n%s" % (cmd, p.returncode, time.time() - t0, p.stdout, p.stderr),
                         encoding="utf-8")
    return p.returncode, p.stdout + p.stderr, round(time.time() - t0, 1)


def main():
    kit, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tag = "py%d%d" % sys.version_info[:2]
    tmp = Path(tempfile.mkdtemp(prefix="t2chk-"))
    res = {"kit": str(kit), "python": sys.version, "executable": sys.executable, "suites": {}, "mutations": {},
           "source_sha256": {f.relative_to(kit).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(kit.rglob("*.py"))
                             if not any(x in ("runs", ".git", "__pycache__") for x in f.relative_to(kit).parts)}}
    try:
        root = tmp / "kit"
        shutil.copytree(kit, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "runs"))
        for s in SUITES:
            code, text, secs = run([sys.executable, "-B", str(root / "tests" / s), str(root)], root, out / ("%s-%s.log" % (s[:-3], tag)))
            m = re.findall(r"(\d+) PASS · (\d+) FAIL", text)
            res["suites"][s] = {"exit": code, "seconds": secs, "pass": int(m[-1][0]) if m else None, "fail": int(m[-1][1]) if m else None,
                                "unverified": [line for line in text.splitlines() if line.startswith("UNVERIFIED ")]}
        for s in MUTATIONS:
            jo = tmp / ("%s.json" % s[:-3])
            code, text, secs = run([sys.executable, "-B", str(root / "tests" / s), str(root), str(tmp / ("scr-" + s[:-3])), str(jo)], root,
                                   out / ("%s-%s.log" % (s[:-3], tag)))
            doc = json.loads(jo.read_text(encoding="utf-8")) if jo.is_file() else {}
            caught = re.findall(r"(\d+)\s*/\s*(\d+)\s+(?:mutants\s+)?caught", text) or re.findall(r"caught[^\d]*(\d+)\D+(\d+)", text)
            res["mutations"][s] = {"exit": code, "seconds": secs, "summary_lines": [l for l in text.splitlines() if "caught" in l.lower()][-3:],
                                   "total": len(doc) if isinstance(doc, list) else 0,
                                   "caught": sum(x.get("caught") is True for x in doc) if isinstance(doc, list) else 0,
                                   "all_caught": isinstance(doc, list) and bool(doc) and all(x.get("caught") is True for x in doc)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        res["temp_residue"] = str(tmp) if tmp.exists() else None
    ok = all(v["exit"] == 0 and v["fail"] == 0 for v in res["suites"].values()) and all(v["exit"] == 0 and v["all_caught"] for v in res["mutations"].values())
    res["verdict"] = "PASS" if ok else "FAIL"
    (out / ("TRACK-II-CHECKS-%s.json" % tag)).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"verdict": res["verdict"], "suites": res["suites"],
                      "mutations": {k: {"exit": v["exit"], "lines": v["summary_lines"]} for k, v in res["mutations"].items()}}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
