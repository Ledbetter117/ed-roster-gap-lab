"""Check the runnable synthetic detector and its explicit output boundary."""
import json, subprocess, sys, tempfile
from pathlib import Path
from validate_study import fixture

ROOT=Path(__file__).resolve().parent
checks=[]
def check(name,condition):
    checks.append(bool(condition));print(('PASS ' if condition else 'FAIL ')+name)
def run(*args):
    return subprocess.run([sys.executable,'-B',str(ROOT/'detector.py'),*map(str,args)],capture_output=True,text=True)
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp);roster=path/'roster.json';out=path/'result.json'
    roster.write_text(json.dumps(fixture()),encoding='utf8')
    result=run(roster)
    parsed=json.loads(result.stdout)
    check('stdout-detects-fourteen-units-all-ten-rules',result.returncode==0 and parsed['units']==14 and len(parsed['hypothetical_rules'])==10 and parsed['labels']['M01/D04/DAY']==[])
    result=run(roster,'--out',out)
    check('writes-new-json-output',result.returncode==0 and json.loads(out.read_text())==parsed)
    before=out.read_bytes();result=run(roster,'--out',out)
    check('refuses-existing-output-and-preserves-bytes',result.returncode==2 and out.read_bytes()==before)
    before=roster.read_bytes();result=run(roster,'--out',roster)
    check('refuses-input-output-collision',result.returncode==2 and roster.read_bytes()==before)
    roster.write_text('{"synthetic":true,"synthetic":false}')
    result=run(roster)
    check('duplicate-json-keys-refused',result.returncode==2 and 'Duplicate JSON key' in result.stderr)
    broken=fixture();broken['score_days'].append(1);roster.write_text(json.dumps(broken))
    result=run(roster)
    check('invalid-shape-has-clear-error-no-traceback',result.returncode==2 and 'seven distinct' in result.stderr and 'Traceback' not in result.stderr)
print(f'{sum(checks)} PASS; {len(checks)-sum(checks)} FAIL')
raise SystemExit(0 if all(checks) else 1)
