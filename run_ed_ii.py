"""ED Roster Gap Lab: synthetic software demonstration and measurement kit.

python -B run_ed_ii.py verify
python -B run_ed_ii.py demo
python -B run_ed_ii.py checks
python -B run_ed_ii.py detect --rules rules/RULES.test-H2-H4.json --input fixtures/CONSTRUCTED-ILLEGAL-PC-01.json
python -B run_ed_ii.py measure --help

Every command verifies MANIFEST.json before execution and fails if tracked files change.
The demo uses hypothetical rules and a SIMULATED rater. It is not a human study.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent


def verify():
    manifest = json.loads((HERE / "MANIFEST.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ValueError("manifest has no files")
    seen, bad = set(), []
    for row in files:
        path = row["path"]
        target = (HERE / path).resolve()
        if path in seen or not target.is_relative_to(HERE.resolve()) or target == HERE.resolve():
            raise ValueError("duplicate or unsafe manifest path")
        seen.add(path)
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
            bad.append(path)
    if bad:
        raise ValueError("manifest mismatch: " + ", ".join(bad))
    return len(files)


def run(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("verify", "demo", "checks", "detect", "measure"):
        print(__doc__)
        return 2
    try:
        count = verify()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("REFUSED before execution: " + str(exc), file=sys.stderr)
        return 4
    command, extra = args[0], args[1:]
    if command == "verify":
        print("PASS: %d manifest files match" % count)
        return 0
    run_dir = None
    if command in ("demo", "checks"):
        if extra:
            print("REFUSED: demo and checks take no arguments", file=sys.stderr)
            return 2
        run_dir = HERE / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + command)
        run_dir.mkdir(parents=True)
        if command == "demo":
            child = [HERE / "demo/run_demo.py", HERE, run_dir / "scratch", run_dir / "DEMO-REPORT.md"]
        else:
            child = [HERE / "tools/run_track_ii_checks.py", HERE, run_dir]
    else:
        child = [HERE / ("detector/gapcheck.py" if command == "detect" else "measure/ii_measure.py"), *extra]
    proc = subprocess.run([sys.executable, "-B", *map(str, child)], cwd=HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"))
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    code = proc.returncode
    integrity = "PASS"
    try:
        verify()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        integrity = "FAIL: " + str(exc)
        print("FAILED after execution: " + str(exc), file=sys.stderr)
        code = 4
    if run_dir:
        (run_dir / "execution.log").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
        record = {"command": command, "exit_code": code, "child_exit_code": proc.returncode, "integrity": integrity,
                  "python": sys.version, "evidence_type": "SYNTHETIC SOFTWARE CHECK; NOT A HUMAN STUDY"}
        (run_dir / "SUMMARY.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print("Saved run: " + str(run_dir))
    return code


if __name__ == "__main__":
    sys.exit(run())
