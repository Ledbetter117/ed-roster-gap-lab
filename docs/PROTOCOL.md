# Human agreement protocol — draft, not frozen

**Status:** the study has not run. This document is a protocol template. It preserves the original endpoint: detector-versus-founder judgment agreement with an interval on a synthetic roster set.

## Study question

On a prespecified synthetic set, how often does the formal detector agree with one founder's pre-output binary gap/no-gap judgments? The reference is this rater's judgment, not objective clinical truth. No patient or employee records are used.

## Fields to freeze before labeling

| Field | Current state |
|---|---|
| Rule decisions and parameter file hash | UNSET — genuine human rule input required |
| N rosters, days, unit scope, seed | UNSET |
| Generator settings and boundary-case policy | UNSET |
| Binary/graded decision and fragility definition | UNSET; software currently binary |
| Unsure policy, primary statistic, interval and threshold | UNSET |
| Facts view, findings-to-unit mapping, incomplete-rule treatment | UNSET |
| Dated study-start decision and rater | UNSET |

The frozen record should also name the release tag/commit, detector and kit hashes, how the set was selected, the number of intended units, and who had access to sealed outputs. The demonstration's seed, labels, and hypothetical values are not study defaults.

## Procedure

1. Encode the human's reviewed rules exactly. Run the constructed legal/illegal controls and inspect the encoded file against the human answers.
2. Save the dated protocol with all fields filled before any study label. The hypothetical Wilson reachability table is only an optimistic planning aid; it ignores within-roster dependence and is not a power calculation.
3. Use `python -B run_ed_ii.py measure make-set --out <NEW_SET> --n <N> --days <DAYS> --seed <SEED> --unit <both_or_nights>`.
4. Use `measure seal --set <SET> --rules <REVIEWED_RULES.json>`, then `measure label-sheet --set <SET> --out <BLANK_SHEET.csv>`.
5. The human labels every row from the agreed facts view, without detector outputs or generator intent. Record deviations, interruptions, and accidental unblinding.
6. Use `measure lock-labels --set <SET> --labels <FILLED.csv> --rater founder` only for actual founder labels. The name is a declaration, not authentication.
7. Use `measure agreement --set <SET> --labels <FILLED.csv> --unsure <exclude_or_disagree>`. Report the frozen primary analysis and prespecified sensitivity analysis, exclusions, contingency table, agreement, interval, and secondary measures.
8. Compare the lower interval bound to the threshold chosen before labeling. Do not add rosters after seeing the result or alter locked primary labels. Report a failure to reach the threshold as such.

## Interpretation and report

A successful software run does not validate the model of staffing need. Even high agreement would only support agreement with this one rater on this synthetic set under these rule choices. Describe the shared role of rule author and rater, cueing from the facts view, generator dependence, small-cluster uncertainty, unsupported rules, and deviations. Preserve the distinction between software tests and empirical observations.

The study ends with a transparent agreement report and interval. Roster optimization, automatic repair, clinical deployment, and language-model comparison are separate studies, outside this protocol.
