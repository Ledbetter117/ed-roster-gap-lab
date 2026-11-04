# Correction record — portable release 0.1.0

The installed October/November workbench remains preserved. This edition makes focused corrections in a separate public source tree.

| Issue | Previous behavior | This edition | Evidence |
|---|---|---|---|
| Release integrity | Workbench printed drift and continued; detect bypassed the check | All documented commands refuse before execution on mismatch and fail on drift during execution | `tests/test_release.py` checks missing, changed, malformed, unsafe, empty manifests and drift after child execution |
| Mutation accounting | Two legacy mutation scripts printed misses/voids but returned success; wrapper trusted exit alone | Scripts fail on uncaught/void controls; runner also inspects every structured mutation result | Three mutation suites; final JSON reports caught/total |
| Superseded mutation | Legacy H6 anchor no longer matched successor code; legacy clock check depended on clock resolution | Two obsolete entries removed from active legacy suite; explicit H6 and clock controls already in successor suite are retained | 14 legacy + 18 measurement + 10 successor active mutants |
| Frozen set reuse | `make-set` could overwrite an existing set directory | Existing output path and invalid roster/day/unit values are refused | Preservation and input checks in `tests/test_release.py` |
| Incomplete rule scoring | A globally skipped ratified rule could leave units scored as no-gap | Skips carry ratification state; no-finding units with incomplete ratified checks are not evaluated | Unsupported-ratified and unratified-rule controls in `tests/test_release.py` |
| H2 charge qualification | A non-RN carrying a charge tag could satisfy H2 | Charge eligibility now requires role RN as well as the qualification | Independent constructed LPN probe and `h2-charge-must-be-rn` regression |
| Capability wording | Older documents described all H3/H7/H8/H10 as unimplemented | Public docs distinguish the limited hypothetical H8 branch from the remaining interfaces | Current detector source and successor acceptance tests |

The changes do not select clinical parameters, fill founder forms, create human labels, or change the historical study ledger. Test success covers the stated software controls, not clinical validity.
