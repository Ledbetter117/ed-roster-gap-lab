"""Maintainer command: regenerate the manifest after reviewing intended source changes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = []
for path in sorted(root.rglob("*")):
    rel = path.relative_to(root)
    if path.is_file() and not any(p in (".git", "__pycache__", "runs") for p in rel.parts) and path.name != "MANIFEST.json" and path.suffix != ".pyc":
        rows.append({"path": rel.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(root / "MANIFEST.json").write_text(json.dumps({"schema": "ed-roster-gap-lab/1", "files": rows}, indent=2) + "\n", encoding="utf-8")
print("Manifest written: %d files" % len(rows))
