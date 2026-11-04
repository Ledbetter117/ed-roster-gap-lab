"""Score actual returned model text, preserving missing/invalid/unsure observations."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse, hashlib, json, random

ROOT=Path(__file__).resolve().parent
RULES={f'H{i}' for i in range(1,11)}


def strict_json(text):
    text=text.strip()
    if text.startswith('```'):
        lines=text.splitlines()
        if lines[0] not in ('```','```json') or lines[-1]!='```':
            raise ValueError('Incomplete or unsupported code fence')
        text='\n'.join(lines[1:-1])
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('Duplicate JSON key')
            out[key]=value
        return out
    def bad_constant(value):raise ValueError('Nonfinite JSON value')
    return json.loads(text,object_pairs_hook=pairs,parse_constant=bad_constant)


def decode_answer(record, request):
    expected=request['expected_unit_ids']
    empty=lambda status,reason:{u:{'status':status,'reason':reason,'label':None,'rule_ids':[]} for u in expected}
    if record is None:return empty('missing','No returned request record')
    if record.get('error'):return empty('missing','Recorded transport/execution failure')
    meta=record.get('metadata',{})
    if not isinstance(meta,dict):return empty('invalid','Invalid execution metadata container')
    finish=meta.get('finish_reason')
    if finish is not None and finish not in ('stop','eos','eos_token','end_turn','completed'):
        return empty('missing','Recorded incomplete generation finish')
    text=record.get('text')
    if not isinstance(text,str) or not text.strip():return empty('missing','Empty raw response')
    try:
        obj=strict_json(text)
        if not isinstance(obj,dict) or set(obj)!={'schema_version','request_id','labels'}:
            raise ValueError('Top-level schema fields differ')
        if obj['schema_version']!='edii-rater-v1' or obj['request_id']!=request['request_id'] or not isinstance(obj['labels'],list):
            raise ValueError('Wrong schema/request identity or labels container')
        ids=[]
        for row in obj['labels']:
            if not isinstance(row,dict) or set(row)!={'unit_id','label','rule_ids'} or row.get('unit_id') not in expected:
                raise ValueError('Unknown unit or non-schema fields')
            ids.append(row['unit_id'])
        if len(set(ids))!=len(ids):raise ValueError('Duplicate unit identifier')
    except (ValueError,TypeError) as exc:
        return empty('invalid',str(exc))
    result=empty('missing','Requested unit absent from answer')
    for row in obj['labels']:
        label,rules=row['label'],row['rule_ids']
        valid=label in ('gap','no-gap','unsure') and isinstance(rules,list) and all(isinstance(r,str) and r in RULES for r in rules)
        valid=valid and len(set(rules))==len(rules) and ((label=='gap' and bool(rules)) or (label in ('no-gap','unsure') and not rules))
        if not valid:result[row['unit_id']]={'status':'invalid','reason':'Invalid label/rule combination','label':None,'rule_ids':[]}
        else:result[row['unit_id']]={'status':'unsure' if label=='unsure' else 'definite','reason':None,'label':label,'rule_ids':rules}
    return result


def ratio(a,b):return a/b if b else None


def metrics(rows):
    counts=Counter(r['status'] for r in rows)
    definite=[r for r in rows if r['status']=='definite']
    tp=sum(r['label']=='gap' and bool(r['reference_rules']) for r in definite)
    tn=sum(r['label']=='no-gap' and not r['reference_rules'] for r in definite)
    fp=sum(r['label']=='gap' and not r['reference_rules'] for r in definite)
    fn=sum(r['label']=='no-gap' and bool(r['reference_rules']) for r in definite)
    n=len(definite);po=ratio(tp+tn,n)
    pe=((tp+fp)*(tp+fn)+(fn+tn)*(fp+tn))/(n*n) if n else None
    sensitivity=ratio(tp,tp+fn);specificity=ratio(tn,tn+fp)
    by_rule={}
    for h in sorted(RULES,key=lambda x:int(x[1:])):
        positives=sum(h in r['reference_rules'] for r in rows)
        emitted=sum(r['status']=='definite' and h in r['rule_ids'] for r in rows)
        hits=sum(r['status']=='definite' and h in r['rule_ids'] and h in r['reference_rules'] for r in rows)
        by_rule[h]={'reference_positive_units':positives,'emitted_units':emitted,'true_positive_units':hits,'precision':ratio(hits,emitted),'recall_planned':ratio(hits,positives)}
    return {'planned_units':len(rows),'status_counts':{k:counts[k] for k in ('definite','unsure','missing','invalid')},
        'primary_agreement':ratio(tp+tn,len(rows)),
        'agreement_vs_detector_planned':ratio(sum(r['status']=='definite' and (r['label']=='gap')==bool(r['detector_rules']) for r in rows),len(rows)),
        'coverage_definite':ratio(n,len(rows)),'complete_case_agreement':po,
        'complete_case_confusion':{'tp':tp,'tn':tn,'fp':fp,'fn':fn},
        'complete_case_sensitivity':sensitivity,'complete_case_specificity':specificity,
        'complete_case_balanced_accuracy':(sensitivity+specificity)/2 if sensitivity is not None and specificity is not None else None,
        'complete_case_kappa':(po-pe)/(1-pe) if pe is not None and pe<1 else None,
        'exact_rule_set_match_planned':ratio(sum(r['status']=='definite' and set(r['rule_ids'])==set(r['reference_rules']) for r in rows),len(rows)),
        'per_rule':by_rule}


def clustered_interval(rows,reps=2000):
    groups={}
    for row in rows:groups.setdefault(row['roster_id'],[]).append(row)
    keys=sorted(groups);rng=random.Random(2026110303);values=[]
    for _ in range(reps):
        sample=[r for k in rng.choices(keys,k=len(keys)) for r in groups[k]]
        values.append(sum(r['status']=='definite' and (r['label']=='gap')==bool(r['reference_rules']) for r in sample)/len(sample))
    values.sort()
    def quantile(p):
        rank=p*(len(values)-1);lo=int(rank);hi=min(lo+1,len(values)-1)
        return values[lo]+(values[hi]-values[lo])*(rank-lo)
    return [quantile(.025),quantile(.975)]


def load_requests():
    freeze=json.loads((ROOT/'frozen-inputs/INPUT-FREEZE.json').read_text())
    for name,expected in freeze['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Frozen input changed: '+name)
    return [json.loads(line) for line in (ROOT/'frozen-inputs/rater-requests.jsonl').read_text().splitlines()]


def verified_labels(directory, root=ROOT):
    """Bind scores to the exact validated inputs, labels and source edition."""
    validation=json.loads((directory/'VALIDATION.json').read_text())
    if validation.get('verdict')!='PASS':raise ValueError('Reference validation did not pass')
    bindings={'PROTOCOL.json':validation.get('protocol_sha256'),
              'frozen-inputs/INPUT-FREEZE.json':validation.get('input_freeze_sha256')}
    expected_sources={'detector.py','reference.py','generate_inputs.py','validate_study.py'}
    sources=validation.get('source_sha256',{})
    if set(sources)!=expected_sources:raise ValueError('Incomplete validation source binding')
    bindings.update(sources)
    for name,expected in bindings.items():
        if not expected or hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Validation binding changed: '+name)
    hashes=validation.get('label_files_sha256',{})
    if set(hashes)!={'reference-labels.json','detector-labels.json'}:
        raise ValueError('Missing validated label hashes')
    labels={}
    for name,expected in hashes.items():
        data=(directory/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Validated labels changed: '+name)
        labels[name]=strict_json(data.decode('utf8'))
    return labels['reference-labels.json'],labels['detector-labels.json']


def analyze(requests,reference,detector,response_file,rater):
    records=[]
    if response_file is not None:
        records=[json.loads(line) for line in response_file.read_text(encoding='utf8').splitlines() if line.strip()]
    planned={r['request_id'] for r in requests};by_id={};duplicates=set();unknown=[]
    for record in records:
        if record.get('rater')!=rater:raise ValueError('Wrong rater identity in return file')
        rid=record.get('request_id')
        if rid not in planned:unknown.append(rid);continue
        if rid in by_id:duplicates.add(rid)
        by_id[rid]=record
    rows=[];request_results=[]
    for request in requests:
        rid=request['request_id'];record=by_id.get(rid)
        decoded=decode_answer(record,request)
        if rid in duplicates:
            decoded={u:{'status':'invalid','reason':'Duplicate returned request records','label':None,'rule_ids':[]} for u in request['expected_unit_ids']}
        request_results.append({'request_id':rid,'returned':record is not None,'duplicate':rid in duplicates,
            'raw_text_sha256':hashlib.sha256(record.get('text','').encode()).hexdigest() if record and isinstance(record.get('text'),str) else None,
            'unit_status_counts':dict(Counter(v['status'] for v in decoded.values()))})
        for unit,value in decoded.items():
            rows.append({'unit_id':unit,'roster_id':request['roster_id'],'request_id':rid,**value,
                'reference_rules':reference[unit],'detector_rules':detector[unit]})
    summary=metrics(rows);summary['primary_agreement_roster_bootstrap_95ci']=clustered_interval(rows)
    summary['illustrative_target_lower_bound_0_80_met']=summary['primary_agreement_roster_bootstrap_95ci'][0]>=.80
    return {'rater':rater,'response_file_sha256':hashlib.sha256(response_file.read_bytes()).hexdigest() if response_file else None,
        'operational_completion':len(by_id)==len(requests) and not duplicates and not unknown,
        'planned_requests':len(requests),'returned_unique_planned_requests':len(by_id),'unknown_request_ids':unknown,
        'request_results':request_results,'summary':summary,'units':rows}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--validation',type=Path,required=True)
    ap.add_argument('--responses',action='append',default=[],metavar='RATER=JSONL')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():raise SystemExit('Refusing to overwrite an analysis edition')
    requests=load_requests();truth,det=verified_labels(args.validation)
    planned_units={u for r in requests for u in r['expected_unit_ids']}
    if set(truth)!=planned_units or set(det)!=planned_units:raise SystemExit('Reference/detector unit identities differ from freeze')
    supplied={}
    for spec in args.responses:
        name,path=spec.split('=',1)
        if name not in ('BoltBF16','FlintUD-Q3KXL') or name in supplied:raise SystemExit('Unplanned or duplicate rater')
        supplied[name]=Path(path)
    results=[analyze(requests,truth,det,supplied.get(name),name) for name in ('BoltBF16','FlintUD-Q3KXL')]
    baseline=[{'unit_id':u,'roster_id':u.split('/')[0],'status':'definite','label':'no-gap','rule_ids':[],'reference_rules':v,'detector_rules':det[u]} for u,v in truth.items()]
    report={'analyzed_at':datetime.now(timezone.utc).isoformat(),'protocol_id':'edii-simulation-20261103-v1',
        'evidence_type':'ACTUAL MODEL OUTPUTS WHEN PROVIDED; ABSENT OUTPUTS ARE MISSING, NOT SIMULATED MODEL RESULTS',
        'validation_record_sha256':hashlib.sha256((args.validation/'VALIDATION.json').read_bytes()).hexdigest(),
        'detector_reference_exact_units':sum(det[u]==truth[u] for u in truth),'planned_units':len(truth),
        'descriptive_always_no_gap_baseline':{'registration':'Added descriptively after reference prevalence was observed; not a new primary endpoint or altered success threshold.','metrics':metrics(baseline),'primary_agreement_roster_bootstrap_95ci':clustered_interval(baseline)},
        'raters':results,'model_study_operationally_complete':all(r['operational_completion'] for r in results),
        'limits':['Synthetic structured-fact task; no human or clinical endpoint','24 constructed clusters, not a population sample','Same AI work context authored detector and separate oracle; manual controls and independent review provide additional evidence','Missing/invalid/unsure count as nonagreement in the planned primary denominator','The high no-gap prevalence makes raw agreement alone an inadequate success summary']}
    args.out.mkdir(parents=True)
    (args.out/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'output':str(args.out),'operationally_complete':report['model_study_operationally_complete'],'raters':[{k:r[k] for k in ('rater','operational_completion','summary')} for r in results]},indent=2))


if __name__=='__main__':main()
