# Provenance and reproduction

The saved result JSON, generated manuscript/PDF, macro manifest and original numerical audit are the **v0.1.0 evidence snapshot**, from commit `ea506d7ef072ed65d00ff51ec48bac8003aa6515`. Their recorded source hashes refer to that version. Subsequent security corrections and checks are recorded separately in [SECURITY-AUDIT.md](SECURITY-AUDIT.md); the historical evidence has not been relabeled as a run of later code. Use the original tag to reproduce that exact snapshot, with its disclosed defects and security limits.

This release continues the Track (ii) workbench 1.2 installed on 2026-11-03. The detector, measurement kit, fixtures, and tests were copied into an isolated candidate before changes. Originals and earlier attempts remain preserved outside the public repository. No private founder forms or operational ledgers are distributed here.

`docs/demo-results.json` is the machine-readable output from a fresh synthetic run. `docs/validation-results.json` is a public summary of the full check record, with machine-specific paths removed. Raw local run evidence remains in `runs/` and is excluded from version control. `docs/EVIDENCE-SOURCES.json` binds the published summaries to the complete raw records by SHA-256 and records relevant code hashes.

The result table, validation counts, and manuscript are generated together:

```sh
python -B tools/render_evidence.py --demo runs/<DEMO_RUN>/DEMO-REPORT.json --checks runs/<CHECK_RUN>/TRACK-II-CHECKS-py312.json
```

Use the actual filenames from your interpreter. The tool reads the saved outputs and fills `paper/MANUSCRIPT.md.in`; it does not compute new scientific observations. Re-run `demo` and `checks` first if relevant source changes. After reviewing intentional source/document changes, maintainers run `python -B tools/build_manifest.py` to update the manifest. End users should not regenerate the manifest just to silence unexplained drift.

The paper's generated values trace to these outputs. Generator settings and the bootstrap repetition count trace to `measure/ii_measure.py`; branch settings and demo seed trace to `demo/run_demo.py`. References were checked against primary scholarly sources on 2026-11-03. The paper makes no claim of an exhaustive novelty search or clinical validation.

AI assistance was used in the earlier implementation and this revision. Current execution needs only Python and makes no model calls. The human author remains responsible for approving the manuscript and for supplying genuine study judgments.

The PDF is rendered from the generated Markdown with the optional ReportLab stack (see `paper/requirements.txt`). The corrected optional stack requires Python 3.11+; core evaluation remains standard-library Python 3.10+. Install the pinned requirements in a separate environment before rendering:

```sh
python -B tools/render_paper.py paper/MANUSCRIPT.md paper/MANUSCRIPT.pdf
```

The detector, demonstration, and tests need no ReportLab installation.
