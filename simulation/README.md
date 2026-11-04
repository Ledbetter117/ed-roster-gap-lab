# Roster Gap Lab: ten-rule simulation study

This edition checks synthetic staffing schedules against ten explicit hypothetical rules and compares those checks with actual local model judgments. It is a completed software instrument for the stated simulation task. The model study is reported from saved responses, including errors and missing answers. It does not establish safe staffing or clinical performance.

The earlier workbench and human-study protocol remain historical material in the parent repository. Their unsupported rule interfaces do not describe this successor: the command below implements H1 through H10. The original human-label endpoint is a separate future study, outside this authorized simulation edition.

## Run the detector

From the repository root, using Python 3.10 or newer:

```text
python -B simulation/detector.py simulation/frozen-inputs/rosters/M01.json
```

The result lists all 14 scored day/shift units and the rules each unit violates. Add `--out new-result.json` to save it. Existing output files are refused. This command needs only Python's standard library; it does not call a model or download anything.

The input is a synthetic 28-day roster with seven scored dates. See [M01.json](frozen-inputs/rosters/M01.json) for the complete schema. Each month includes prior shifts so rest, consecutive days, and period hours can be calculated before the scored week. `synthetic: true` is mandatory. This is a local command-line tool: the caller selects file paths; roster values do not select output paths.

## Rules implemented

| Rule | Hypothetical behavior |
|---|---|
| H1 | Non-orientee RN headcount meets the census-band minimum: 2, 3, 4, or 4. |
| H2 | At least one non-orientee RN is charge-qualified. |
| H3 | Non-orientee RNs cover TRIAGE and RESUS competencies. |
| H4 | An unavailable assignment needs an explicit EMERGENCY exception. |
| H5 | Rest since the preceding distinct shift is at least 12 hours. |
| H6 | Every block on the fourth or later consecutive worked day is flagged. |
| H7 | Cumulative distinct-shift hours stay within the person's fictional 14-day cap. |
| H8 | Each orientee has their named RN preceptor in the block; capacity is one orientee. |
| H9 | A person occupies at most one distinct place in a block. |
| H10 | A traveler stays within fictional contract dates and allowed shifts. |

These choices are declared assumptions, not founder-approved clinical policy. H7 is an upper-cap check, not a minimum-hours or payroll check. H10 does not interpret law or real contracts. H6 deliberately reports every affected block, unlike the older engine's first-crossing behavior.

## Evidence and reproduction

Read the [paper](paper/MANUSCRIPT.pdf), its [Markdown source](paper/MANUSCRIPT.md), or the [complete results](analysis/final/RESULTS.json). Both planned model batches returned 24 observations. Bolt detected 1 of 46 reference gap units, with 1 false positive. Flint detected 32 of 46, with 219 false positives and 71 invalid unit answers. Neither result supports reliable use for this task. Completion means the declared experiment was executed and reported, including its unfavorable results.

The design freezes 24 constructed months, one seven-day window per month, both shifts, and 336 units. It includes four valid schedules and two perturbation schedules targeting each rule. The separate reference implementation evaluates actual resulting violations, including co-occurring rules; generator intent is not treated as truth.

Run these commands from the `simulation` directory:

```text
python -B validate_study.py
python -B test_analysis.py
python -B test_cli.py
```

Validation writes a new timestamped directory, checks the frozen data hashes, exercises manual controls and rule-removal mutations, and compares all units with the reference. [The saved validated edition](validation/20261104T030744.897001Z/VALIDATION.json) has 45 passing controls, 10 of 10 mutants caught, and exact rule-set agreement on 336 of 336 units. The analysis and command-line suites add 30 and 6 passing controls. These are constructed checks, not proof that all bugs are absent.

To rescore the actual saved model responses without inference, run from the repository root. Choose an output directory that does not already exist:

```text
python -B simulation/analyze_responses.py --validation simulation/validation/20261104T030744.897001Z --responses BoltBF16=simulation/observations/BoltBF16.jsonl --responses FlintUD-Q3KXL=simulation/observations/FlintUD-Q3KXL.jsonl --out new-simulation-replay
python -B simulation/compare_replay.py simulation/analysis/final/RESULTS.json new-simulation-replay/RESULTS.json
```

The comparison requires exact equality of results and source/observation hashes; only the analysis timestamp may differ. The workflow runs the same commands. This replay is not a new model run. The original model responses are supplied in full, with host paths and transport metadata removed from their wrappers.

The saved Markdown report can be regenerated with `python -B simulation/write_report.py simulation/analysis/final/RESULTS.json --out new-paper-source`. PDF rendering is optional and uses the separately pinned packages in `simulation/requirements-report.txt`: `python simulation/tools/render_pdf.py simulation/paper/MANUSCRIPT.md new-paper.pdf`. The detector, tests, and analysis do not need those packages.

[The frozen protocol](PROTOCOL.json), [model-setting clarification](PROTOCOL-CLARIFICATION-01.md), and [software correction record](SOFTWARE-AMENDMENT-01.json) separate prospective choices from later repairs. The frozen sources are preserved under `source-at-input-freeze/`; current sources contain the documented input and evidence-binding corrections.

## What model agreement means

Models receive rules and structured facts, including calculated rest, consecutive days, and cumulative hours. They do not receive detector answers, reference answers, or perturbation intent. This evaluates assisted rule judgment, not the ability to read raw schedules or clinical expertise. BoltBF16 and FlintUD-Q3KXL are prespecified local model candidates; their operational availability is not an expert qualification.

Missing, invalid, unsure, and failed answers remain in the primary denominator as nonagreement. Complete-case metrics are separately named. Uncertainty resamples whole rosters, not individual day/shift rows. A constant no-gap response already agrees on 290 of 336 units (86.3%), so agreement alone is misleading; positive-class recall and balanced accuracy are essential.

The detector and reference were separately implemented in the same AI-assisted work context. Manual controls, mutation checks, and independent review provide additional evidence, but this is not independent human ground truth. The constructed schedules are not a representative staffing sample. No clinical deployment, patient outcomes, human agreement, or time-saving result is claimed.

## Authorship and historical scope

AI assistance was used for design, implementation, review, analysis, and writing. Actual model judgments are study observations; software-generated reference labels are labeled as reference outputs. Neither is presented as a human judgment. Historical demonstrations and the original human-study protocol keep their original numbers and limits.
