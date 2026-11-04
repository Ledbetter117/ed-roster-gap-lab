# Independent review of the simulation instrument

A separate reviewing agent inspected the rule implementation, reference implementation, frozen request boundaries, parser, and evidence bindings. The final bounded review found no unresolved material issue in that scope. This is an independent agent review, not clinical review or external peer review.

The initial constructive review passed 19 checks after correcting one review-fixture expectation. That fixture expected a consecutive-days finding alone but also lacked RN headcount and charge coverage. The first 18/19 record and the corrected 19/19 record were preserved by the reviewer. No producer rule change was needed for that fixture.

Further review identified two real evidence-handling defects: a changed label file could be scored under an unchanged validation receipt, and a valid-looking answer with an explicit incomplete-generation finish could be accepted by direct scoring. The current code binds label files, source, protocol, and inputs to validation, and treats incomplete finishes as missing. The run collector already marked those finishes as errors; direct scoring now enforces the same boundary.

The final repair retest passed 29 checks. These included malformed input refusal, changed label/source/protocol/input rejection, old-receipt rejection, incomplete-finish handling, complete-finish acceptance, planned-denominator behavior, whole-roster resampling, equality of all 336 current reference labels, and unchanged frozen inputs. Producer suites separately passed 45 constructed/input checks, 30 analysis checks, 6 command-line checks, and caught all 10 rule-removal mutations.

The review emphasized that the always-no-gap baseline reaches 86.3% agreement. An 80% agreement interval threshold alone therefore does not establish useful gap detection. The report retains that prospective target and presents the baseline, missed gaps, balanced accuracy, and rule-specific results beside it.

The review does not prove absence of every defect. It does not qualify either model as a clinician, ratify the hypothetical staffing rules, or validate clinical use. Public-release integration, rendered-paper inspection, installation, and remote CI are separate checks owned by the release coordinator.
