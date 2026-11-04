# v0.1.0 - ED Roster Gap Lab

This is a public software and protocol release. The original human-agreement study remains pending; no human, clinical, staffing-safety or deployment outcome is claimed.

## Delivered

- Portable Python rule checker, constructed fixtures, a synthetic demonstration, and a frozen-record/label-locking workflow.
- Reproducible methods, limitations, generated result tables, manuscript source and a readable PDF.
- Windows launchers and a Linux/Windows CI definition. CI results must be observed before claiming remote validation.
- 98 passing regression checks and 42 of 42 active planted defects caught on the producer's Windows Python 3.12 run. A separate same-family review agent reproduced those counts on Python 3.13 and passed 26 additional edge cases plus seven runner-enforcement checks.

## Corrected

- Installation drift now prevents execution, including changes during a command.
- Failed, missing, void or uncaught mutation results cannot produce a passing check run.
- Set generation refuses to overwrite an existing study directory.
- A skipped active rule no longer creates a false no-gap result.
- Charge eligibility requires an RN role as well as the charge qualification.

The tests establish behavior on the exercised cases, not freedom from all defects. Both demonstration branches use hypothetical settings and a SIMULATED rater. Their output is not an estimate of human agreement.

## Original study work still open

Genuine staffing-rule choices, prospectively frozen measurement choices, and blinded human labels are still required. See `docs/PROTOCOL.md` and `docs/FOUNDER-INPUTS.md`. A software release does not replace those inputs.
