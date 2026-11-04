# Local security and release audit — 3 November 2026

This correction follows the published v0.1.0 commit `ea506d7ef072ed65d00ff51ec48bac8003aa6515`. The audit found and repaired local file-safety and input-validation defects. It does not certify the software as vulnerability-free or validate clinical use.

## Verified findings and corrections

| Finding | Impact and prerequisite | Correction |
|---|---|---|
| Manifest roster IDs accepted paths | A user running `seal` on a crafted set could read and replace a JSON file outside that set. Reproduced with an owned synthetic fixture. | Roster IDs must be tokens; paths are contained within the set; linked paths are refused; the roster mapping digest is rechecked. |
| Existing outputs could be overwritten | Reissuing a sheet before lock erased filled labels; `detect --out` could replace an existing file. | A sheet is issued once. Both CSV and detector output creation require new files. |
| Existing internal files could be aliases | A pre-existing hard link could make a direct truncating write affect a file outside the set. | Internal JSON uses atomic directory-entry replacement; the outside hard-linked fixture remains unchanged. |
| Non-finite or malformed values were accepted or crashed validation | A NaN rest threshold was accepted and could suppress a finding. Duplicate identifiers and ambiguous structures could produce misleading interpretation or a traceback. | Reject NaN/Infinity, malformed rule/roster structures, duplicate staff/date/shift tokens and boolean clock values. Short letter-led shift tokens prevent formula-valued spreadsheet cells and unit-ID delimiter ambiguity. |
| Publication renderer accepted unconstrained source/branch keys | Supplied evidence could refer outside the source tree or use unexpected experiment directory names. This was a maintainer-tool input boundary, not a hosted endpoint. | Source keys must be relative Python files within the project; only the documented A/B branches are accepted. |
| Optional renderer dependency was unconstrained | ReportLab allowed an older Pillow version with published advisories. The supplied renderer uses text/tables and does not open images; exploitability of those image/PDF parser paths through this renderer was not demonstrated. | Pin the tested optional stack to ReportLab 4.4.9, Pillow 13.0.0 and charset-normalizer 3.5.2. Rendering now requires Python 3.11+; core software remains standard-library Python 3.10+. |

The existing synthetic-check workflow now pins checkout and Python setup to full commit IDs verified against the official action repositories, disables persisted checkout credentials and has a 20-minute job limit. Repository-wide release guards and platform settings are maintained separately by the release owner.

## Verification

Independent review found one remaining malformed-input edge: ratified H8 with `params: null` crashed after validation treated it as unset. The correction now records a ratified skipped rule; no-finding units remain not-evaluated. Both behaviors have explicit regressions. The earlier failing probe is preserved in the private review record.

- **134 PASS, 0 FAIL**, including 36 security checks, on Windows/Python 3.12.14.
- **42/42 active mutants caught, zero void.** The first rerun exposed an obsolete text anchor after the input-validation change. Its failed record was retained, the anchor was corrected without changing the intended mutant, and the complete suite was rerun.
- **One local group remains UNVERIFIED:** this Windows host did not permit symbolic-link creation. Windows junction and hard-link checks passed. The cross-platform workflow can exercise symlinks on a supporting host; an unexecuted run is not claimed as evidence.
- A fresh 168-unit synthetic demo matched all **52 compared numerical fields** and both branch label-count dictionaries from v0.1.0. No human result was created.
- The corrected optional stack was installed in an isolated audit directory. It regenerated a five-page PDF with text identical to the preserved v0.1.0 PDF. The shared runtime and published PDF were not replaced.

The machine-readable check record is [security-validation.json](security-validation.json); the evidence binding is [security-evidence.json](security-evidence.json). These are separate from the preserved [v0.1.0 numerical results](RESULTS.md) and paper. They record a bounded local run, not an independent security certification or a later GitHub CI result.

## Public content and dependency boundary

At audit start the public history contained one commit and 83 tracked files; v0.1.0 had no separately uploaded release assets. Its standard source archives are generated from Git. The five-page PDF contains the intended public author/title/date, five scholarly URI links, no detected local-home path or credential-pattern markers in extracted text, no embedded-file names and no non-URI actions. Targeted content review is not a proof that every possible sensitive string is absent. Repository history secret scanning and final platform checks have separate release-owner records.

Official PyPI metadata was queried for [ReportLab 4.4.9](https://pypi.org/pypi/reportlab/4.4.9/json), [Pillow 13.0.0](https://pypi.org/pypi/pillow/13.0.0/json) and [charset-normalizer 3.5.2](https://pypi.org/pypi/charset-normalizer/3.5.2/json). Their `vulnerabilities` arrays were empty at this audit. This is a dated database observation, not a guarantee against undisclosed vulnerabilities. No dependency in that optional stack is required for detection, measurement, the demo or core checks.

The intended study remains detector-versus-founder agreement with genuine blinded labels. Neither the original empirical endpoint, clinical safety, a staffing optimizer nor all declared rule interfaces are complete. Rater identity is a declaration, sealed data are unencrypted, and file hashes are not signatures. The tool is designed for a single local operator and is not a sandbox for hostile same-user processes or unbounded files. See [SECURITY.md](../SECURITY.md) for reporting and operating boundaries.
