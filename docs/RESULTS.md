# Results: software checks and simulated demonstration

This is the preserved **v0.1.0** evidence snapshot. Source hashes and counts below describe that release. Later security checks and corrections are separate in [SECURITY-AUDIT.md](SECURITY-AUDIT.md).

**No human agreement result is available.** All demonstration labels are SIMULATED.

Table 1. Local software checks; constructed inputs only.

| Check group | Passed/caught | Failed/uncaught |
|---|---:|---:|
| test_gapcheck.py | 29 | 0 |
| test_measure.py | 26 | 0 |
| test_gapcheck_r12.py | 22 | 0 |
| test_release.py | 21 | 0 |
| mutation_gapcheck.py | 14/14 | 0 |
| mutation_measure.py | 18/18 | 0 |
| mutation_gapcheck_r12.py | 10/10 | 0 |

Table 2. Synthetic pipeline outputs; SIMULATED rater only.

| Branch | Unsure policy | Scored units | Agreement | 95% roster interval | Kappa |
|---|---|---:|---:|---|---:|
| A | exclude | 156 | 0.622 | 0.528–0.702 | 0.296 |
| A | disagree | 168 | 0.577 | 0.488–0.661 | 0.296 |
| B | exclude | 156 | 0.359 | 0.300–0.416 | 0.091 |
| B | disagree | 168 | 0.333 | 0.274–0.393 | 0.091 |

Branch A uses inclusive rest and calendar-day counts. Branch B changes both to exclusive rest and shift counts. The comparison does not isolate either change.

Generated set: 12 rosters × 7 days × 2 shifts = 168 units; seed `demo-seed-1030`. Simulated label counts: `{'gap': 28, 'no-gap': 128, 'unsure': 12}`.

The full result JSON, source hashes, and validation summary are adjacent to this file. The original human endpoint remains pending. See METHODS.md and LIMITATIONS.md before interpreting any number.
