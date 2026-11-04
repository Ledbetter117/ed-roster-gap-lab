"""Constructed parser/denominator controls, never model observations."""
import copy,hashlib,json,tempfile
from pathlib import Path
from analyze_responses import decode_answer,metrics,clustered_interval,verified_labels,analyze

request={'request_id':'x','expected_unit_ids':['M01/D01/DAY','M01/D01/NIGHT']}
answer={'schema_version':'edii-rater-v1','request_id':'x','labels':[
    {'unit_id':'M01/D01/DAY','label':'gap','rule_ids':['H2']},
    {'unit_id':'M01/D01/NIGHT','label':'no-gap','rule_ids':[]}]}
checks=[]
def check(name,condition):checks.append(bool(condition));print(('PASS ' if condition else 'FAIL ')+name)
def decode(obj):return decode_answer({'text':json.dumps(obj),'error':None},request)
check('valid-answer',all(v['status']=='definite' for v in decode(answer).values()))
check('empty-is-missing',all(v['status']=='missing' for v in decode_answer({'text':''},request).values()))
check('failure-is-missing',all(v['status']=='missing' for v in decode_answer({'text':json.dumps(answer),'error':'timeout'},request).values()))
check('prose-not-recovered',all(v['status']=='invalid' for v in decode_answer({'text':'Here it is: '+json.dumps(answer)},request).values()))
check('complete-json-fence-accepted',all(v['status']=='definite' for v in decode_answer({'text':'```json\n'+json.dumps(answer)+'\n```'},request).values()))
for name,edit in [('wrong-request',lambda x:x.update(request_id='other')),('unknown-unit',lambda x:x['labels'][0].update(unit_id='other')),('duplicate-unit',lambda x:x['labels'].append(x['labels'][0])),('extra-field',lambda x:x.update(confidence=1))]:
    obj=copy.deepcopy(answer);edit(obj);check(name,all(v['status']=='invalid' for v in decode(obj).values()))
obj=copy.deepcopy(answer);obj['labels'].pop();check('omitted-unit-stays-missing',decode(obj)['M01/D01/NIGHT']['status']=='missing')
obj=copy.deepcopy(answer);obj['labels'][0]['rule_ids']=['H99'];check('unknown-rule-is-invalid',decode(obj)['M01/D01/DAY']['status']=='invalid')
obj=copy.deepcopy(answer);obj['labels'][0].update(label='unsure',rule_ids=[]);check('unsure-is-not-definite',decode(obj)['M01/D01/DAY']['status']=='unsure')
check('duplicate-json-key-rejected',all(v['status']=='invalid' for v in decode_answer({'text':'{"schema_version":"edii-rater-v1","request_id":"x","request_id":"x","labels":[]}'},request).values()))
rows=[{'roster_id':'M01','status':'definite','label':'gap','rule_ids':['H2'],'reference_rules':['H2'],'detector_rules':['H2']},
      {'roster_id':'M01','status':'missing','label':None,'rule_ids':[],'reference_rules':[],'detector_rules':[]}]
m=metrics(rows)
check('missing-penalizes-primary-denominator',m['primary_agreement']==.5 and m['complete_case_agreement']==1 and m['coverage_definite']==.5)
check('cluster-resampling-keeps-whole-roster',clustered_interval(rows,100)==[.5,.5])
rows[1].update(status='definite',label='no-gap');m=metrics(rows)
check('perfect-contingency-kappa',m['complete_case_confusion']=={'tp':1,'tn':1,'fp':0,'fn':0} and m['complete_case_kappa']==1 and m['complete_case_balanced_accuracy']==1)
rows[0].update(label='no-gap',rule_ids=[]);m=metrics(rows)
check('always-negative-does-not-get-perfect-balanced-accuracy',m['primary_agreement']==.5 and m['complete_case_balanced_accuracy']==.5 and m['per_rule']['H2']['recall_planned']==0)
check('length-finish-stays-missing',all(v['status']=='missing' for v in decode_answer({'text':json.dumps(answer),'metadata':{'finish_reason':'length'}},request).values()))
check('eos-token-is-complete',all(v['status']=='definite' for v in decode_answer({'text':json.dumps(answer),'metadata':{'finish_reason':'eos_token'}},request).values()))
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);directory=root/'validated';directory.mkdir()
    files=['PROTOCOL.json','frozen-inputs/INPUT-FREEZE.json','detector.py','reference.py','generate_inputs.py','validate_study.py']
    for name in files:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'unchanged')
    digest=hashlib.sha256(b'unchanged').hexdigest()
    names=['reference-labels.json','detector-labels.json'];labels={u:[] for u in request['expected_unit_ids']}
    data=json.dumps(labels).encode()
    for name in names:(directory/name).write_bytes(data)
    validation={'verdict':'PASS','protocol_sha256':digest,'input_freeze_sha256':digest,
        'source_sha256':{n:digest for n in files[2:]},'label_files_sha256':{n:hashlib.sha256(data).hexdigest() for n in names}}
    (directory/'VALIDATION.json').write_text(json.dumps(validation))
    check('exact-validation-bindings-pass',verified_labels(directory,root)==(labels,labels))
    for name in names:
        (directory/name).write_text('{}')
        try:verified_labels(directory,root);refused=False
        except ValueError:refused=True
        check('changed-'+name+'-refused',refused);(directory/name).write_bytes(data)
    for name in files:
        (root/name).write_bytes(b'changed')
        try:verified_labels(directory,root);refused=False
        except ValueError:refused=True
        check('changed-'+name+'-refused',refused);(root/name).write_bytes(b'unchanged')
    response=root/'answers.jsonl';req={**request,'roster_id':'M01'}
    row={'rater':'BoltBF16','request_id':'x','text':json.dumps(answer)}
    response.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
    got=analyze([req],labels,labels,response,'BoltBF16')
    check('duplicate-wrapper-invalidates-all-units',not got['operational_completion'] and got['summary']['status_counts']['invalid']==2)
    response.write_text(json.dumps({**row,'request_id':'unknown'})+'\n')
    got=analyze([req],labels,labels,response,'BoltBF16')
    check('unknown-request-cannot-complete-study',not got['operational_completion'] and got['summary']['status_counts']['missing']==2)
print(f'{sum(checks)} PASS; {len(checks)-sum(checks)} FAIL')
raise SystemExit(0 if all(checks) else 1)
