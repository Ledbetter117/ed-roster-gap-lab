"""Manual controls, rule-removal mutations and separately calculated reference checks."""
from pathlib import Path
from datetime import datetime, timezone
import copy, hashlib, json
import detector
import reference

ROOT=Path(__file__).resolve().parent


def fixture():
    staff=[]
    for i in range(1,5):
        staff.append({'staff_id':f'S{i:02}','role':'RN','charge':i==1,
            'competencies':['TRIAGE','RESUS'] if i in (1,3) else [],'orientee':i==4,
            'preceptor':'S03' if i==4 else None,'period_cap':96,'traveler':False,
            'allowed_shifts':['DAY','NIGHT'],'contract_days':[1,28]})
    return {'schema_version':'edii-sim-roster-v1','synthetic':True,'roster_id':'M01','month_days':28,'score_days':list(range(1,8)),
        'staff':staff,'assignments':[{'staff_id':p['staff_id'],'day':4,'shift':'DAY','place':'ED'} for p in staff],
        'unavailable':[],'census':{f'D{d:02}/{sh}':'low' for d in range(1,29) for sh in ('DAY','NIGHT')}}


def add(roster, sid, day, shift='DAY', place='ED'):
    roster['assignments'].append({'staff_id':sid,'day':day,'shift':shift,'place':place})


def controls():
    cases=[]
    def case(name, edit, expected, unit='M01/D04/DAY'):
        r=fixture();edit(r);cases.append((name,r,unit,expected))
    case('valid-block',lambda r:None,[])
    case('H1-only',lambda r:r['census'].update({'D04/DAY':'surge'}),['H1'])
    case('H2-only',lambda r:r['staff'][0].update(charge=False),['H2'])
    case('H3-only',lambda r:[p.update(competencies=['TRIAGE']) for p in r['staff']],['H3'])
    case('H4-only',lambda r:r['unavailable'].append(['S02',4,'DAY']),['H4'])
    case('H5-only',lambda r:add(r,'S02',3,'NIGHT'),['H5'])
    case('H6-only',lambda r:[add(r,'S02',d) for d in (1,2,3)],['H6'])
    case('H7-only',lambda r:r['staff'][1].update(period_cap=0),['H7'])
    case('H8-only',lambda r:r.update(assignments=[a for a in r['assignments'] if a['staff_id']!='S03']),['H8'])
    case('H9-only',lambda r:add(r,'S02',4,place='TRIAGE'),['H9'])
    case('H10-only',lambda r:r['staff'][1].update(traveler=True,allowed_shifts=['NIGHT']),['H10'])
    case('rest-exactly12-allowed',lambda r:add(r,'S02',3),[])
    case('three-consecutive-days-allowed',lambda r:[add(r,'S02',d) for d in (2,3)],[])
    case('period-hours-exact-cap-allowed',lambda r:r['staff'][1].update(period_cap=12),[])
    case('contract-endpoints-inclusive',lambda r:r['staff'][1].update(traveler=True,contract_days=[4,4]),[])
    case('nontraveler-contract-not-applied',lambda r:r['staff'][1].update(allowed_shifts=['NIGHT']),[])
    case('same-place-duplicate-is-not-double-booking',lambda r:add(r,'S02',4),[])
    case('non-RN-charge-does-not-qualify',lambda r:r['staff'][0].update(role='LPN'),['H2'])
    case('preceptor-cannot-be-self',lambda r:r['staff'][3].update(preceptor='S04'),['H8'])
    case('preceptor-must-be-RN',lambda r:r['staff'][2].update(role='LPN'),['H8'])
    def two_orientees(r):
        p=copy.deepcopy(r['staff'][3]);p['staff_id']='S05';r['staff'].append(p);add(r,'S05',4)
    case('one-preceptor-cannot-cover-two-orientees',two_orientees,['H8'])
    def allowed_exception(r):
        r['unavailable'].append(['S02',4,'DAY'])
        for a in r['assignments']:
            if a['staff_id']=='S02':a['exception']='EMERGENCY'
    case('explicit-unavailability-exception',allowed_exception,[])
    def mixed_exception(r):
        allowed_exception(r);add(r,'S02',4)
    case('one-unexcepted-assignment-still-violates',mixed_exception,['H4'])
    def reset_period(r):
        r['score_days']=list(range(15,22))
        for a in r['assignments']:a['day']=15
        add(r,'S02',14);r['staff'][1]['period_cap']=12
    case('period-reset-at-day15',reset_period,[],'M01/D15/DAY')
    def fifth_day(r):
        for a in r['assignments']:a['day']=5
        for d in (1,2,3,4):add(r,'S02',d)
    case('H6-flags-fifth-day-too',fifth_day,['H6'],'M01/D05/DAY')
    def orientee_skill(r):
        for p in r['staff']:p['competencies']=['TRIAGE']
        r['staff'][3]['competencies'].append('RESUS')
    case('orientee-competency-not-counted',orientee_skill,['H3'])
    return cases


def main():
    freeze=json.loads((ROOT/'frozen-inputs/INPUT-FREEZE.json').read_text())
    mismatches=[name for name,h in freeze['files'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h]
    if mismatches:raise SystemExit('Frozen input mismatch: '+','.join(mismatches))
    checks=[]
    cases=controls()
    for name,roster,unit,expected in cases:
        got=detector.detect(roster)[unit];ref=reference.score(roster)[unit]
        checks.append({'name':name,'expected':expected,'detector':got,'reference':ref,'pass':got==ref==expected})
    malformed=[('not-synthetic',lambda r:r.update(synthetic=False)),('duplicate-staff',lambda r:r['staff'].append(copy.deepcopy(r['staff'][0]))),
        ('unknown-assignment',lambda r:r['assignments'][0].update(staff_id='S99')),('negative-hours',lambda r:r['staff'][0].update(period_cap=-1)),
        ('formula-place',lambda r:r['assignments'][0].update(place='=1+1')),('missing-census',lambda r:r['census'].pop('D04/DAY')),
        ('duplicate-eighth-scored-day',lambda r:r['score_days'].append(1)),
        ('missing-assignments',lambda r:r.pop('assignments')),('missing-unavailable',lambda r:r.pop('unavailable')),
        ('null-assignments',lambda r:r.update(assignments=None)),('object-unavailable',lambda r:r.update(unavailable={})),
        ('scalar-assignment',lambda r:r['assignments'].append(1)),('scalar-staff',lambda r:r['staff'].append(1)),
        ('list-staff-token',lambda r:r['staff'][0].update(staff_id=[])),('list-roster-token',lambda r:r.update(roster_id=[])),
        ('list-competency',lambda r:r['staff'][0].update(competencies=[[]])),
        ('list-shift',lambda r:r['assignments'][0].update(shift=[])),('list-census',lambda r:r['census'].update({'D04/DAY':[]})),
        ('wrong-schema',lambda r:r.update(schema_version='wrong'))]
    for name,edit in malformed:
        r=fixture();edit(r)
        try:detector.detect(r);ok=False
        except ValueError:ok=True
        checks.append({'name':name,'pass':ok})
    source=(ROOT/'detector.py').read_text()
    mutations=[]
    for i in range(1,11):
        rule=f'H{i}';needle=f"found.add('{rule}')"
        assert source.count(needle)==1
        namespace={};exec(compile(source.replace(needle,'pass'),f'<remove-{rule}>','exec'),namespace)
        name,r,unit,want=next(c for c in cases if c[0]==rule+'-only')
        observed=namespace['detect'](r)[unit]
        mutations.append({'removed_rule':rule,'caught_by':name,'expected':want,'mutant_observed':observed,'caught':observed!=want})
    predicted={};truth={};differences=[]
    for path in sorted((ROOT/'frozen-inputs/rosters').glob('*.json')):
        r=json.loads(path.read_text());a=detector.detect(r);b=reference.score(r)
        for unit in a:
            if a[unit]!=b[unit]:differences.append({'unit_id':unit,'detector':a[unit],'reference':b[unit]})
        predicted.update(a);truth.update(b)
    from collections import Counter
    label_bytes={name:(json.dumps(value,indent=2)+'\n').encode('utf8') for name,value in [('detector-labels.json',predicted),('reference-labels.json',truth)]}
    record={'recorded_at':datetime.now(timezone.utc).isoformat(),'protocol_sha256':freeze['protocol_sha256'],
        'input_freeze_sha256':hashlib.sha256((ROOT/'frozen-inputs/INPUT-FREEZE.json').read_bytes()).hexdigest(),
        'label_files_sha256':{name:hashlib.sha256(value).hexdigest() for name,value in label_bytes.items()},
        'evidence_type':'CONSTRUCTED SOFTWARE CHECKS; NOT MODEL OR HUMAN OUTCOMES','manual_checks':checks,'mutations':mutations,
        'check_pass':sum(c['pass'] for c in checks),'check_fail':sum(not c['pass'] for c in checks),
        'mutants_caught':sum(m['caught'] for m in mutations),'mutants_total':len(mutations),
        'planned_units':336,'scored_units':len(truth),'detector_reference_disagreements':differences,
        'reference_gap_units':sum(bool(v) for v in truth.values()),'reference_rule_counts':dict(Counter(h for values in truth.values() for h in values)),
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('detector.py','reference.py','generate_inputs.py','validate_study.py')}}
    record['verdict']='PASS' if record['check_fail']==0 and record['mutants_caught']==10 and not differences and len(truth)==336 else 'FAIL'
    out=ROOT/'validation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out.mkdir(parents=True)
    (out/'VALIDATION.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    for name,value in label_bytes.items():(out/name).write_bytes(value)
    print(json.dumps({'output':str(out),'verdict':record['verdict'],'checks':[record['check_pass'],record['check_fail']],'mutants':[record['mutants_caught'],10],'units':len(truth),'disagreements':differences,'reference_gap_units':record['reference_gap_units'],'reference_rule_counts':record['reference_rule_counts']},indent=2))
    return 0 if record['verdict']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
