"""Create the predeclared fictional schedules and blinded local-rater requests once."""
from pathlib import Path
from datetime import datetime, timezone
import copy, hashlib, json, random
from detector import facts, validate

ROOT=Path(__file__).resolve().parent
COLS=['staff_id','role','charge','competencies','unavailable','all_assignments_excepted','rest_hours','consecutive_days','period_hours','period_cap','orientee','preceptor','places','traveler','allowed_shifts','contract_days']


def build_roster(rng, number, kind):
    ids=[f'S{i:02}' for i in range(1,21)];rng.shuffle(ids)
    staff=[];crews=[]
    for crew in range(4):
        crew_ids=ids[crew*5:crew*5+5];crews.append(crew_ids)
        shift='DAY' if crew<2 else 'NIGHT'
        for k,sid in enumerate(crew_ids):
            staff.append({'staff_id':sid,'role':'RN','charge':k==0,
                'competencies':[['TRIAGE','RESUS'],['RESUS'],['TRIAGE'],['TRIAGE','RESUS'],[]][k],
                'orientee':k==4,'preceptor':crew_ids[3] if k==4 else None,'period_cap':96,
                'traveler':k==2,'allowed_shifts':[shift],'contract_days':[1,28]})
    phase=rng.randrange(4);start=rng.choice([1,8,15,22]);score_days=list(range(start,start+7))
    assignments=[];census={}
    for day in range(1,29):
        team=((day-1+phase)//2)%2
        for shift,crew in [('DAY',team),('NIGHT',team+2)]:
            census[f'D{day:02}/{shift}']=rng.choice(['low','normal','normal','high','surge'])
            assignments.extend({'staff_id':sid,'day':day,'shift':shift,'place':'ED'} for sid in crews[crew])
    roster={'schema_version':'edii-sim-roster-v1','synthetic':True,'roster_id':f'M{number:02}',
        'month_days':28,'score_days':score_days,'staff':staff,'assignments':assignments,'census':census,'unavailable':[]}
    day=start+3;shift=rng.choice(['DAY','NIGHT']);crew=((day-1+phase)//2)%2+(0 if shift=='DAY' else 2)
    team=crews[crew];people={s['staff_id']:s for s in staff};target=team[1]
    if kind=='H1':
        roster['assignments']=[a for a in assignments if not(a['day']==day and a['shift']==shift and a['staff_id'] in team[1:3])]
        census[f'D{day:02}/{shift}']='normal'
    elif kind=='H2':people[team[0]]['charge']=False
    elif kind=='H3':
        for sid in team:people[sid]['competencies']=[c for c in people[sid]['competencies'] if c!='RESUS']
    elif kind=='H4':roster['unavailable']=[[target,day,shift]]
    elif kind=='H5':
        prev_day,prev_shift=(day-1,'NIGHT') if shift=='DAY' else (day,'DAY')
        assignments.append({'staff_id':target,'day':prev_day,'shift':prev_shift,'place':'ED'})
    elif kind=='H6':
        for d in score_days:
            if not any(a['staff_id']==target and a['day']==d and a['shift']==shift for a in assignments):
                assignments.append({'staff_id':target,'day':d,'shift':shift,'place':'ED'})
    elif kind=='H7':people[target]['period_cap']=24
    elif kind=='H8':
        roster['assignments']=[a for a in assignments if not(a['day']==day and a['shift']==shift and a['staff_id']==team[3])]
        census[f'D{day:02}/{shift}']='normal'
    elif kind=='H9':assignments.append({'staff_id':target,'day':day,'shift':shift,'place':'TRIAGE'})
    elif kind=='H10':people[team[2]]['allowed_shifts']=['NIGHT' if shift=='DAY' else 'DAY']
    validate(roster)
    return roster


def prompt_for(roster, protocol):
    units=facts(roster)
    packet=[]
    for u in units:
        packet.append({'unit_id':u['unit_id'],'day':u['day'],'shift':u['shift'],'census_band':u['census_band'],
                       'assigned_rows':[[r[k] for k in COLS] for r in u['assigned']]})
    request_id='edii-sim-'+roster['roster_id']
    instruction=(
        'You are a model rater for a fictional scheduling experiment, not a clinician. Apply only the ten explicitly HYPOTHETICAL rules below. '
        'For each unit, report gap if ANY rule is violated, no-gap if none is violated, or unsure if you cannot determine it. '
        'Return only JSON matching the exact schema. Include every listed unit once. rule_ids must contain every violated rule, '
        'or [] for no-gap/unsure. Do not invent clinical requirements. These normalized facts already include prior shifts and pay-period context; '
        'all schedules are synthetic. True/false fields are facts, not detector judgments. rest_hours=null means no preceding shift. '
        'all_assignments_excepted indicates every assignment in that block has the EMERGENCY exception. '
        'period_hours includes this distinct shift; duplicate places do not add hours. '
        'A preceptor must be another assigned non-orientee RN. Units outside the scored week may contribute to rest, consecutive days and period hours.\n\n'
    )
    instruction+='HYPOTHETICAL RULES\n'+'\n'.join(k+': '+v for k,v in protocol['rules'].items())
    instruction+='\n\nOUTPUT SCHEMA\n'+json.dumps({'schema_version':'edii-rater-v1','request_id':request_id,'labels':[{'unit_id':'EXACT_LISTED_UNIT_ID','label':'gap|no-gap|unsure','rule_ids':['H1']} ]},separators=(',',':'))
    instruction+='\n\nINPUT\n'+json.dumps({'request_id':request_id,'assigned_row_columns':COLS,'units':packet},separators=(',',':'))
    return {'request_id':request_id,'roster_id':roster['roster_id'],'expected_unit_ids':[u['unit_id'] for u in units],
            'prompt':instruction,'output_schema':protocol['output_schema'],'max_output_tokens':1600,'temperature':0}


def main():
    protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    freeze=json.loads((ROOT/'PROTOCOL-FREEZE.json').read_text())
    assert hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest()==freeze['protocol_sha256']
    output=ROOT/'frozen-inputs'
    output.mkdir(exist_ok=False)
    (output/'rosters').mkdir();(output/'requests').mkdir();(output/'private-reference').mkdir()
    rng=random.Random(protocol['seed']);kinds=['valid']*4+[f'H{i}' for i in range(1,11) for _ in range(2)];rng.shuffle(kinds)
    requests=[];intent=[]
    for i,kind in enumerate(kinds,1):
        roster=build_roster(rng,i,kind);request=prompt_for(roster,protocol)
        (output/'rosters'/f"{roster['roster_id']}.json").write_text(json.dumps(roster,indent=2)+'\n',encoding='utf8')
        (output/'requests'/f"{request['request_id']}.json").write_text(json.dumps(request,indent=2)+'\n',encoding='utf8')
        (output/'requests'/f"{request['request_id']}.txt").write_text(request['prompt'],encoding='utf8')
        requests.append(request);intent.append({'roster_id':roster['roster_id'],'constructed_target':kind})
    (output/'rater-requests.jsonl').write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in requests),encoding='utf8')
    (output/'private-reference/GENERATOR-INTENT.json').write_text(json.dumps(intent,indent=2)+'\n',encoding='utf8')
    files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
    record={'frozen_at':datetime.now(timezone.utc).isoformat(),'protocol_sha256':freeze['protocol_sha256'],'model_calls_so_far':0,'reference_outcomes_computed':False,
        'requests':len(requests),'units':sum(len(r['expected_unit_ids']) for r in requests),'source_sha256':sources,'files':files,
        'prompt_characters':{'minimum':min(len(r['prompt']) for r in requests),'maximum':max(len(r['prompt']) for r in requests),'total':sum(len(r['prompt']) for r in requests)},
        'warning':'Only requests/ and rater-requests.jsonl may be supplied to models. Do not send rosters with intent, private-reference/, detector outcomes or analysis.'}
    (output/'INPUT-FREEZE.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('files','source_sha256')},indent=2))


if __name__=='__main__':main()
