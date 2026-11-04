"""Render the simulation report from saved, completed observations and analysis."""
from pathlib import Path
import argparse,hashlib,json

def pct(value):return 'NA' if value is None else f'{100*value:.2f}%'
def number(value):return 'NA' if value is None else f'{value:.3f}'
def interval(values):return '–'.join(pct(x) for x in values)

def render(result):
    if not result['model_study_operationally_complete']:
        raise ValueError('Both planned model batches need a returned answer or failure record')
    raters=result['raters'];baseline=result['descriptive_always_no_gap_baseline']
    agreement=[];classification=[];coverage=[];rules=[]
    for r in raters:
        s=r['summary'];c=s['complete_case_confusion'];status=s['status_counts']
        agreement.append(f"| {r['rater']} | {pct(s['primary_agreement'])} | {interval(s['primary_agreement_roster_bootstrap_95ci'])} | {pct(s['exact_rule_set_match_planned'])} |")
        classification.append(f"| {r['rater']} | {c['tp']}/{c['fn']}/{c['fp']}/{c['tn']} | {pct(s['complete_case_sensitivity'])} | {pct(s['complete_case_balanced_accuracy'])} | {number(s['complete_case_kappa'])} |")
        coverage.append(f"| {r['rater']} | {r['returned_unique_planned_requests']}/24 | {status['definite']} | {status['unsure']}/{status['missing']}/{status['invalid']} |")
    for h in (f'H{i}' for i in range(1,11)):
        values=[r['summary']['per_rule'][h] for r in raters]
        rules.append(f"| {h} | {values[0]['reference_positive_units']} | {values[0]['true_positive_units']}/{values[0]['emitted_units']} | {values[1]['true_positive_units']}/{values[1]['emitted_units']} |")
    a,b=[r['summary'] for r in raters]
    gaps=sum(bool(u['reference_rules']) for u in raters[0]['units'])
    detected=[r['summary']['complete_case_confusion']['tp'] for r in raters]
    invalid_gaps=sum(u['status']=='invalid' and bool(u['reference_rules']) for u in raters[1]['units'])
    target=', '.join(r['rater']+(' met' if r['summary']['illustrative_target_lower_bound_0_80_met'] else ' did not meet')+' the illustrative threshold' for r in raters)
    return f'''# Ten hypothetical roster rules: constructive validation and a two-model agreement study

Simulation study and software report. No human participants or clinical validation.

## Abstract

We implemented ten explicit hypothetical staffing constraints and tested a rule detector against a separately implemented reference on 24 constructed 28-day schedules. One seven-day window per schedule and both shifts gave 336 scored units. The schedules, prompts, design, and metrics were frozen before reference scoring or model calls. Two local model candidates, BoltBF16 and FlintUD-Q3KXL, judged the same structured facts in separate requests without detector answers or generator intent. The detector matched the reference rule sets on all 336 units. Model agreement was {pct(a['primary_agreement'])} for Bolt and {pct(b['primary_agreement'])} for Flint, compared with {pct(baseline['metrics']['primary_agreement'])} for a constant no-gap response. Bolt detected {detected[0]} of {gaps} reference gap units with {a['complete_case_confusion']['fp']} false positive. Flint detected {detected[1]} of {gaps}, with {b['complete_case_confusion']['fp']} false positives and {b['status_counts']['invalid']} invalid units. These results describe the fixed synthetic task; they do not establish clinical competence or safe staffing. The source, raw model responses to synthetic inputs, failures, prospective records, and scoring commands support independent reproduction.

## 1. Purpose and scope

This study asks whether explicit hypothetical scheduling rules can be implemented consistently and whether local models apply those same rules to supplied facts. It separates software correctness on constructed cases from agreement with model judgments. Neither outcome substitutes for clinical validation.

The project began with a proposed detector-versus-founder-judgment study. That protocol and its earlier numerical demonstration are preserved. A later explicit authorization permitted a separate simulation edition using fictitious operational choices and actual model observations. This report completes that simulation study. It does not relabel models as humans or claim that the original human-label endpoint was measured.

The successor implements all ten named interfaces. H1 checks the assigned non-orientee RN minimum by census band; H2 checks charge qualification; H3 checks TRIAGE and RESUS competencies; H4 checks unavailability with explicit exceptions; H5 checks 12-hour rest; H6 flags every block on a fourth or later consecutive worked day; H7 checks a fictional 14-day upper hours cap; H8 checks a named, co-assigned RN preceptor with capacity one; H9 checks multiple distinct places in a block; H10 checks fictional traveler dates and allowed shifts. Exact thresholds and edge cases are in PROTOCOL.json. These are study assumptions, not clinical policy. H7 does not enforce minimum hours, and H10 does not interpret legal contracts. H6 intentionally differs from the historical engine's first-crossing reporting.

## 2. Prospective design and implementation

The locally frozen prospective design used seed 2026110302 and 24 schedules. Four were valid controls; two schedules targeted each of H1–H10. Target types were shuffled before generation. Each schedule contained 20 synthetic staff in alternating two-day crews and spanned a fictional 28-day month. A seeded week was selected for scoring. Perturbations could produce more than one violation, so the target name was not used as a reference label.

The detector normalizes each assigned person's prior-shift rest, consecutive worked dates, cumulative period hours, competencies, exceptions, preceptor, places, and traveler terms. A second implementation computes rule sets directly from raw assignments and histories using a different organization of the calculations. It imports neither the detector nor the generator intent. Both implementations were authored in the same AI-assisted work context. This is separation of implementation, not independent human ground truth.

Manual controls cover each rule, equality boundaries, the period reset, duplicate rows, preceptor eligibility, and exceptions. Ten rule-removal mutations each disable one rule and must be caught by its corresponding control. The final constructed validation has 45 passing controls, 10 of 10 mutations caught, and no detector/reference disagreements across 336 units. The analysis suite has 30 passing checks; the command-line suite has 6. Independent review added constructed checks and identified evidence-binding and generation-finish handling gaps; those were repaired with regression tests before final model scoring.

Protocol, input, and source hashes preserve the prospective state. Post-freeze changes added strict malformed-input validation, a runnable command, exclusive output creation, label/source binding, and refusal of incomplete generation finishes. They did not alter any frozen roster, prompt, or valid-data rule verdict. Original source files and earlier validation records remain available. The amendment states that reference outcomes were visible but model answers had not yet been read by the implementation agent.

## 3. Model observations and analysis

BoltBF16 and FlintUD-Q3KXL were prespecified local model candidates. Their names identify operationally available models, not clinical or expert qualifications. Each received 24 separate requests, with 14 unit judgments per request. The system prompt, exact user prompts, model setting contract, model file identifiers and hashes, finish reasons, token counts, and elapsed generation times are retained. The requested settings were temperature 0, a 32,768-token context, 4,096 maximum output tokens, thinking off, and a 600-second request timeout. Requested settings and runtime-reported settings are distinguished in the public metadata. No answer-driven repair or feedback was supplied.

The task provided structured facts rather than raw roster images. In particular, models received already calculated rest, consecutive-day, and cumulative-hour context. They did not receive detector or reference judgments, generator intent, or perturbation names. This tests assisted application of rules, not unassisted interpretation of schedules. Both models used the same frozen prompt; model and quantization differences remain part of the comparison.

The accepted answer is a JSON object with the exact request identity and unit IDs. Unknown or duplicate units, wrong request IDs, and extra schema fields invalidate the request. Missing requested units remain missing. Bad label/rule combinations invalidate that unit. A complete JSON code fence is accepted; arbitrary prose is not repaired. Missing, invalid, unsure, and execution-failed answers count as nonagreement over all 336 planned units. Complete-case statistics are named separately.

Primary outcomes are detector/reference agreement and each model's gap/no-gap agreement with the reference and detector. Secondary outcomes include coverage, exact rule-set match, per-rule precision and recall, sensitivity, specificity, balanced accuracy, and Cohen's kappa [1]. The code reports undefined denominators as null, not zero. We estimated descriptive 95% intervals using 2,000 percentile resamples of whole rosters with seed 2026110303. Resampling clusters preserves their internal dependence [2], but 24 deliberately constructed schedules do not establish population coverage.

## 4. Results

The reference found 46 gap units and 290 no-gap units. Detector binary and exact rule-set agreement were 336/336; precision and recall for each rule were 1.0 on the constructed design. This is observed performance on these controls, not a guarantee for arbitrary schedules.

Table 1. Returned requests and unit-level answer status. The last column reports unsure/missing/invalid units.

| Candidate | Requests | Definite units | Unsure/missing/invalid |
|---|---:|---:|---:|
{chr(10).join(coverage)}

Table 2. Agreement over all 336 planned units. Detector and reference comparisons are identical because their labels match.

| Candidate | Agreement | Roster 95% interval | Exact rule set |
|---|---:|---|---:|
{chr(10).join(agreement)}
| Constant no-gap | {pct(baseline['metrics']['primary_agreement'])} | {interval(baseline['primary_agreement_roster_bootstrap_95ci'])} | {pct(baseline['metrics']['exact_rule_set_match_planned'])} |

Table 3. Complete-case classification. Counts are true positives/false negatives/false positives/true negatives. Only definite units are included here; invalid, missing, and unsure units remain in Table 2.

| Candidate | TP/FN/FP/TN | Gap sensitivity | Balanced accuracy | Kappa |
|---|---|---:|---:|---:|
{chr(10).join(classification)}
| Constant no-gap | 0/46/0/290 | 0.00% | 50.00% | 0.000 |

Flint's complete-case sensitivity excludes {invalid_gaps} reference-positive units with invalid answers. Across all {gaps} planned positive units, it detected {detected[1]} ({pct(detected[1]/gaps)}). Its complete-case 100% sensitivity therefore does not mean it found every gap. Five malformed JSON responses invalidated 70 units; one further unit had an invalid label/rule combination. Those 71 units remain in the primary denominator. Bolt's apparent agreement advantage was accompanied by {a['complete_case_confusion']['fn']} missed gaps and no correctly identified individual rule. Neither candidate showed useful balanced classification on this fixed design.

Table 4. Rule-specific outputs. Each model cell is correct rule emissions/all rule emissions. Recall is correct emissions divided by reference-positive units. Zero emitted rules gives undefined precision, not perfect precision.

| Rule | Reference positives | Bolt correct/emitted | Flint correct/emitted |
|---|---:|---:|---:|
{chr(10).join(rules)}

The constant no-gap comparator was added descriptively after the reference prevalence was observed. It was not substituted for a prospectively declared primary endpoint. The frozen illustrative target required a lower agreement interval bound of at least 0.80: {target}. A constant no-gap response also has high agreement on this design. The threshold therefore cannot establish useful gap detection; the confusion counts and positive-class performance are necessary to interpret it. We retained the threshold and reported its weakness rather than selecting a new threshold after seeing outcomes.

## 5. Interpretation and limitations

The constructive checks support the stated ten-rule implementation on the supplied cases. They do not establish that the hypothetical rules are clinically appropriate. Model results show why high overall agreement must be read alongside missed gaps, false positives, and rule-specific findings. A protocol can be fully executed and yield unfavorable model performance.

The sample is finite and deliberately constructed, with one seed and few positive units for several rules. Perturbations can overlap, and the design does not isolate causal effects of individual changes. The same AI-assisted work context created the detector, reference, and test design. Independent review and mutation checks reduce some implementation risk but do not create an external clinical standard. Structured context makes the task easier in some respects and may cue rule application. Results depend on the selected models, quantizations, prompt, and runtime settings. No alternate prompts or repeated stochastic generations were tested.

There are no human labels, clinical ratification, real staffing schedules, patient outcomes, deployment outcomes, or measured labor savings. The original human study remains a distinct future empirical project. Its absence does not leave this explicitly authorized simulation study unexecuted.

## 6. Reproduction and availability

The public `simulation` directory contains the ten-rule detector, separate reference, fixed inputs, exact prompts, raw model responses to synthetic inputs, sanitized runtime metadata, validation editions, analysis, and tests. Assistant text and errors are preserved exactly; host paths and transport details are omitted through an explicit metadata allowlist. Saved observations can be rescored without loading a model. The README gives commands for detection, validation, and analysis; existing output editions are not overwritten.

AI assistance contributed to design, code, review, analysis, and drafting. Actual model responses are marked as observations, and deterministic reference outputs as constructed reference data. No AI output is attributed to a human participant. The parent repository preserves the earlier workbench and its original manuscript as historical evidence.

## References

1. Cohen J. A coefficient of agreement for nominal scales. Educational and Psychological Measurement. 1960;20(1):37–46. https://doi.org/10.1177/001316446002000104. Publisher bibliographic record was checked in the earlier project; full text was not retrieved.
2. Field CA, Welsh AH. Bootstrapping clustered data. Journal of the Royal Statistical Society: Series B. 2007;69(3):369–390. https://doi.org/10.1111/j.1467-9868.2007.00593.x. Publisher abstract and metadata were checked in the earlier project; no study-specific coverage guarantee is inferred.
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('results',type=Path);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();result=json.loads(args.results.read_text(encoding='utf8'));text=render(result)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'MANUSCRIPT.md').write_text(text,encoding='utf8')
    (args.out/'REPORT-SOURCE.json').write_text(json.dumps({'results_sha256':hashlib.sha256(args.results.read_bytes()).hexdigest(),'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'manuscript_sha256':hashlib.sha256((args.out/'MANUSCRIPT.md').read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf8')
    print(str(args.out/'MANUSCRIPT.md'))

if __name__=='__main__':main()
