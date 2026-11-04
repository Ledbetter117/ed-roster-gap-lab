# Roster Gap Lab

A reproducible simulation study of ten hypothetical staffing rules and actual local model judgments. The completed simulation engine, study inputs, saved responses, and paper are in [`simulation/`](simulation/README.md).

## Start here

```text
python -B simulation/detector.py simulation/frozen-inputs/rosters/M01.json
```

This checks 14 day/shift units and reports the violated rules. Python's standard library is sufficient. No model service, download, or paid call is needed to run the detector or rescore the saved observations.

- [Simulation study and commands](simulation/README.md)
- [Written paper](simulation/paper/MANUSCRIPT.pdf) · [Markdown source](simulation/paper/MANUSCRIPT.md)
- [Both-model results](simulation/analysis/final/RESULTS.json)
- [Frozen design](simulation/PROTOCOL.json) and [software correction record](simulation/SOFTWARE-AMENDMENT-01.json)
- [LinkedIn draft](simulation/LINKEDIN-DRAFT.md)

## What this project demonstrates

The simulation engine implements all ten declared constraints: RN headcount, charge coverage, skill coverage, unavailability, rest, consecutive days, period hours, preceptor pairing, multiple-place assignments, and fictional traveler terms. A separately implemented reference matches its exact rule sets on all 336 constructed units. Manual controls, targeted mutations, malformed-input checks, independent review, and saved model observations make the methods inspectable.

This is a study of explicit hypothetical rules. It is not a clinical scheduling product. A high model agreement percentage can conceal missed gaps, so the paper reports sensitivity, balanced accuracy, confusion counts, and a constant no-gap baseline alongside agreement.

## Historical workbench

The earlier detector, `run_ed_ii.py` launcher, and [original protocol](PROTOCOL.md) remain available for reproducing historical demonstrations. Their unimplemented interfaces and earlier numbers belong to that edition. Use the `simulation/detector.py` command above for the new ten-rule instrument.

The proposed founder-versus-detector human study remains a separate future empirical project. The authorized simulation study uses actual model observations and constructed reference labels; neither is presented as human judgment. AI assistance contributed to implementation, review, analysis, and writing. No clinical validity, safe staffing, human agreement, or measured time savings is claimed.

See [security reporting](SECURITY.md) and the MIT [license](LICENSE).
