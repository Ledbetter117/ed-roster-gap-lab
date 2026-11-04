# Inputs needed for the original human agreement study

This sheet contains no answers. The present software release can proceed independently. A human study needs genuine values and judgments; a model cannot manufacture them.

## 1. Rules

For each rule, choose KEEP/FIX/KILL, set confidence HIGH or MED if kept, and provide the listed values. The machine-readable starting point is `rules/RULES.founder-template.json`.

| Rule | Human input still missing |
|---|---|
| H1 | Minimum RN count for low/normal/high/surge; whether charge counts; missing-band policy |
| H2 | Whether a charge-qualified RN must be present every shift |
| H4 | Allowed exceptions to unavailability, or none |
| H5 | Minimum rest hours; whether equality is legal; whether day-after-night is prohibited; confirm end-to-start basis |
| H6 | Maximum consecutive work; count calendar days or shifts |
| H9 | Places that do not count as separate assignments, or none |

Also state any missing clinical rule. H3/H7/H10 have no implementation; H8 is a limited hypothetical branch. Do not label a study set as if these capabilities are complete. Confirm carry-in policy and whether specified unsatisfiability notes should be displayed separately.

## 2. Measurement choices

Record a dated choice for binary versus graded gaps, fragile shifts, both shifts versus nights, unsure labels and primary/sensitivity treatment, N rosters, seed, generator settings, and the disqualifying lower-bound threshold. The current code supports binary labels; graded labels require a defined protocol and implementation change.

Confirm the facts shown to the rater, day-level H6 mapping, primary statistic, interval method, and treatment of not-evaluated units. Freeze the choices before any study labels exist. Do not reuse the demonstration set for a blinded study after inspecting its outputs.

## 3. Actual labels

After the study set and outputs are frozen, fill its blank sheet without opening `SEALED/`. Mark every unit. Lock the completed file under the true rater declaration before unblinding. Keep any later correction separately from the locked primary labels.

## Current record

The original founder DOCX forms inspected on 2026-11-03 were blank. Proposed B/C companion answers were recommendations, not decisions. Historical HOLD/sequencing and ledger-adoption records were not rewritten for this release. The current task authorizes continued engineering and public packaging; it does not create the missing rules or labels.
