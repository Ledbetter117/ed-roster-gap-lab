# Limitations

The founder-versus-detector endpoint is not measured. No reviewed founder rule set, frozen human protocol, or genuine blinded labels were found in the named source records. Generated labels do not fill that gap.

- **Scope:** synthetic roster checking only. No clinical use, deployment, scheduling optimizer, roster repair, employer integration, or comparison of language models is evaluated.
- **Reference:** the intended study has one rater who also specifies the rules. Agreement is partly consistency with that person's own formalization. It cannot establish agreement among clinicians, staffing safety, or improved outcomes.
- **Generator:** staffing targets, band weights, availability, and perturbations are hypothetical. Their prevalence changes agreement and kappa. The demonstration is one fixed seed and two combined parameter branches, not a factorial or population study.
- **Blinding:** the facts sheet shows charge status, availability, place, rest, and consecutive days. It can cue the rule logic. The sealed folder is not encrypted; blinding is behavioral. The rater string cannot authenticate who labeled a file.
- **Statistics:** 12 synthetic rosters in the demo provide a small number of clusters. The percentile bootstrap is not a validation of nominal coverage, and there is no formal power calculation. No human acceptance threshold has been chosen.
- **Supported rules:** H1/H2/H4/H5/H6/H9 have executable checks. H3 (competency mix), H7 (FTE/pay-period hours), and H10 (traveler contracts) have interfaces only. H8 is a limited hypothetical orientee/preceptor check with orientee exclusion from H1; the generator carries no orientee data and the branch is not a validated orientation policy. It does not implement all possible preceptor or competency rules.
- **Rule semantics:** H6 counts a run over consecutive calendar dates and can count either days or shifts within it. H9 checks distinct places within a block; cross-block overlaps are separate notes. Unsatisfiability notes cover specified conditions only.
- **Data protection:** token checks are not a general anonymizer. Do not supply real records. Free-text fields are not a comprehensive sensitive-data detector.
- **Integrity:** hashes expose accidental change relative to a trusted manifest. Anyone able to edit source and hashes can bypass them. Direct invocation of modules bypasses the top-level release check; the documented launch command enforces it.
- **Portability:** the saved local checks are from the interpreter/platform listed in the validation record. A GitHub workflow is provided for Windows/Linux and Python 3.10/3.12/3.13; an unexecuted workflow is not a cross-platform result.

The original endpoint remains open. The software and protocol report is a useful intermediate artifact; it does not silently replace the intended empirical result.
