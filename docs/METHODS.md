# Methods

## Question and evidence boundary

The intended study asks how a deterministic gap detector agrees with the founder's own judgments on a frozen synthetic roster set. Agreement with one person is not clinical ground truth. The public demonstration tests the machinery using a simulated heuristic; it does not answer the study question.

## Input and rule model

A roster contains synthetic staff tokens `S01`–`S999`, day tokens `D01`–`D999`, shift definitions, assignments, availability, and census-band context. `provenance.synthetic` must be true. These checks restrict the expected format; they do not anonymize arbitrary data or prove that a supplied record is synthetic.

A rule runs when its status is `MED` or `HIGH` and its required parameters are present. `LOW` rules are excluded; `KILLED` rules do not run. These statuses are data declarations, not independently verified human decisions. The provided founder template leaves all rules LOW. Test rule sets carry a TEST-ONLY or HYPOTHETICAL source label.

The engine reports located findings, evaluated/skipped rules, duplicate-assignment notes, overlapping-assignment notes, and specified unsatisfiability signals. The latter are limited conditions, not a complete feasibility solver. Findings are deterministic for the same input and rules. Carry-in dates can contribute to rest and consecutive-work calculations without receiving findings.

## Synthetic generator

`measure/ii_measure.py::GENERATOR` is the complete generator configuration. It creates 10 RN tokens, including 3 charge-qualified tokens; availability probability is 0.8; band weights are 2:5:2:1; staffing targets are 2/3/4/4. Per-block structural perturbation probabilities are 0.10 charge removal, 0.10 one short, 0.05 unavailable assignment, 0.05 back-to-back assignment, and 0.03 double booking. These are hypothetical software settings, never empirical staffing estimates.

A seeded `random.Random` instance builds each roster. The generator records its intended perturbations separately from the label sheet. Perturbation intent is not reference truth. It does not create a clinical label and is not used as the agreement reference. No borderline set has been selected with actual founder thresholds.

## Order and records

`make-set` writes roster hashes and a set manifest to a new directory; reuse of an existing directory is refused. `seal` runs the detector and records output, rules, detector, and kit hashes. `label-sheet` issues a randomized facts view and records which seal preceded it. `lock-labels` requires all expected units, refuses duplicates/unknown units, and records the label file hash, sheet, seal, and declared rater. `agreement` verifies the frozen files before scoring. A new seal after issuing the sheet and edited labels after locking are refused.

The workflow is an audit trail, not access control: the local user can open the sealed folder, relabel simulated data as human, or rewrite hashes. Such conduct invalidates the human protocol even if the program runs. Blinding and authorship require honest participant conduct.

## Unit, mapping, and statistics

A unit is `(roster, day, shift)`. The selected scope is both shifts or nights only. Any located finding maps the unit to gap. A day-level H6 finding maps to both shifts on that day. With no finding, a skipped ratified rule makes the affected unit not evaluated: a global skip affects the whole roster, a scoped skip only its block. Not-evaluated units are excluded and counted.

For definite labels, let `a` be both gap, `b` detector-only gap, `c` rater-only gap, and `d` both no-gap; `n=a+b+c+d`. Raw agreement is `(a+d)/n`. Expected agreement from marginal proportions is `((a+b)(a+c)+(c+d)(b+d))/n²`; kappa is `(observed-expected)/(1-expected)` and is undefined when its denominator is zero. Sensitivity and specificity are explicitly against this rater, not against clinical truth. See [Cohen](https://journals.sagepub.com/doi/abs/10.1177/001316446002000104) for the named agreement coefficient and [Warrens](https://pmc.ncbi.nlm.nih.gov/articles/PMC2792365/) for a primary treatment of chance correction for binary tables.

`unsure=exclude` removes unsure units from the primary agreement denominator. `unsure=disagree` counts them against agreement. Under the latter policy, kappa, sensitivity, and specificity still use definite labels only. The agreement confusion-table cells under `disagree` include policy-assigned mismatches and must not be interpreted as new human judgments.

The percentile interval uses 5,000 resamples of whole rosters, sampled with replacement, with a seed derived from the frozen set hash. Each sampled roster contributes all its scored units; the statistic remains unit-weighted. Whole-roster resampling retains within-roster dependence, but its inferential performance depends on the data-generating model. This implementation has no study-specific coverage calibration, particularly with few rosters. [Field and Welsh](https://doi.org/10.1111/j.1467-9868.2007.00593.x) analyze that dependence on model assumptions.

## Verification and reproducibility

The check command copies source to temporary storage, executes the detector/measurement/release suites, and checks every mutation record. A missing summary, a failed suite, a void mutant, or an uncaught mutant prevents PASS. Temporary files are removed after execution. The launcher checks the release manifest before and after commands. A manifest is an accidental-drift check, not a signed trust root.

Run commands are in the README. The numeric report and manuscript table are regenerated from demo and check JSON by `tools/render_evidence.py`; code and result provenance are recorded in `docs/PROVENANCE.md`. The exact locally checked interpreter and results are in `docs/validation-results.json`.
