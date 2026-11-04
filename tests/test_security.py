"""Constructed local file-safety and malformed-input regressions; no private data."""
from pathlib import Path
import contextlib,csv,copy,hashlib,importlib.util,io,json,os,subprocess,sys,tempfile
ROOT=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT/'measure'));import ii_measure as M
G=M.G;RULES=ROOT/'rules/RULES.test-H2-H4.json';results=[];unverified=[]
def check(name,ok):
    results.append(bool(ok));print(('PASS ' if ok else 'FAIL ')+name)
def refused(fn):
    try:fn()
    except SystemExit as exc:return 'REFUSED' in str(exc)
    return False
def write(p,obj):p.write_text(json.dumps(obj),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='edii-security-') as temp:
    base=Path(temp);s=base/'set';M.make_set(str(s),1,1,'security-fixture','both')
    manifest=json.loads((s/'SET-MANIFEST.json').read_text());original=(s/'SET-MANIFEST.json').read_bytes()
    outside=base/'outside.json';outside.write_bytes((ROOT/'fixtures/LEGAL-PC-01.json').read_bytes());outside_before=outside.read_bytes()
    for name,rid in [('parent','../../outside'),('absolute',str(outside.with_suffix(''))),('backslash','..\\..\\outside'),('drive','C:outside'),('newline','R001\n')]:
        bad=copy.deepcopy(manifest);bad['rosters']={rid:digest(outside)};bad['set_sha256']=M.h_bytes(json.dumps(bad['rosters'],sort_keys=True).encode());write(s/'SET-MANIFEST.json',bad)
        check('manifest-'+name+'-refused',refused(lambda:M.seal(str(s),str(RULES))) and outside.read_bytes()==outside_before and not (s/'DETECTOR-SEAL.json').exists())
    (s/'SET-MANIFEST.json').write_bytes(original)
    bad=copy.deepcopy(manifest);bad['set_sha256']='0'*64;write(s/'SET-MANIFEST.json',bad)
    check('manifest-digest-mismatch-refused',refused(lambda:M.load_set(str(s))))
    (s/'SET-MANIFEST.json').write_bytes(original)
    M.seal(str(s),str(RULES));sheet=base/'sheet.csv';sheet.write_text('existing labels must survive',encoding='utf-8');before=sheet.read_bytes()
    check('existing-sheet-preserved',refused(lambda:M.label_sheet(str(s),str(sheet))) and sheet.read_bytes()==before and not (s/'LABEL-SHEET.json').exists())
    fresh=base/'fresh.csv';M.label_sheet(str(s),str(fresh));rows=list(csv.DictReader(fresh.open(newline='',encoding='utf-8')))
    for row in rows:row['label (gap / no-gap / unsure)']='gap'
    with fresh.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    filled=fresh.read_bytes();record=(s/'LABEL-SHEET.json').read_bytes()
    check('issued-sheet-labels-preserved',refused(lambda:M.label_sheet(str(s),str(fresh))) and fresh.read_bytes()==filled and (s/'LABEL-SHEET.json').read_bytes()==record)
    check('second-sheet-refused',refused(lambda:M.label_sheet(str(s),str(base/'second.csv'))) and not (base/'second.csv').exists())
    try:
        linked=base/'linked-set';M.make_set(str(linked),1,1,'linked-fixture','both')
        target=linked/'rosters/R001.json';target.unlink();target.symlink_to(outside)
        check('linked-roster-refused',refused(lambda:M.load_set(str(linked))) and outside.read_bytes()==outside_before)
        linked2=base/'linked-seal';M.make_set(str(linked2),1,1,'linked2-fixture','both');outdir=base/'outside-seal';outdir.mkdir()
        (linked2/'SEALED/detector').symlink_to(outdir,target_is_directory=True)
        check('linked-output-directory-refused',refused(lambda:M.seal(str(linked2),str(RULES))) and not list(outdir.iterdir()))
    except (OSError,NotImplementedError) as exc:
        unverified.append('symlink checks unavailable: '+type(exc).__name__);print('UNVERIFIED '+unverified[-1])
    if os.name == 'nt':
        linked3=base/'junction-set';M.make_set(str(linked3),1,1,'junction-fixture','both');outdir3=base/'outside-junction';outdir3.mkdir()
        junction=linked3/'SEALED/detector'
        proc=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(outdir3)],capture_output=True,text=True)
        if proc.returncode:
            unverified.append('junction creation unavailable');print('UNVERIFIED '+unverified[-1])
        else:
            check('junction-output-directory-refused',refused(lambda:M.seal(str(linked3),str(RULES))) and not list(outdir3.iterdir()))
    hard=base/'hardlink-set';M.make_set(str(hard),1,1,'hardlink-fixture','both');(hard/'SEALED/detector').mkdir()
    try:
        os.link(outside,hard/'SEALED/detector/R001.json');M.seal(str(hard),str(RULES))
        check('hardlinked-output-preserves-outside',outside.read_bytes()==outside_before)
    except OSError:
        unverified.append('hard-link check unavailable');print('UNVERIFIED '+unverified[-1])
    roster=json.loads((ROOT/'fixtures/LEGAL-PC-01.json').read_text());rules=json.loads(RULES.read_text())
    def bad_roster(name,edit):
        r=copy.deepcopy(roster);edit(r)
        try:ok=G.detect(r,rules)['run_status']=='ERROR'
        except Exception:ok=False
        check(name,ok)
    bad_roster('formula-shift-refused',lambda r:r['shifts'][0].update(shift='=1+1'))
    bad_roster('duplicate-staff-refused',lambda r:r['staff'].append(copy.deepcopy(r['staff'][0])))
    bad_roster('duplicate-day-refused',lambda r:r['dates'].append(r['dates'][0]))
    bad_roster('duplicate-shift-refused',lambda r:r['shifts'].append(copy.deepcopy(r['shifts'][0])))
    bad_roster('boolean-clock-refused',lambda r:r['shifts'][0].update(start_hour=True))
    bad_roster('malformed-provenance-refused',lambda r:r.update(provenance=['synthetic']))
    bad_roster('malformed-assignment-refused',lambda r:r['assignments'].append([]))
    bad_roster('malformed-place-refused',lambda r:r['assignments'][0].update(place=[]))
    for value in (float('nan'),float('inf'),float('-inf')):
        r={'rules':{'H5':{'status':'HIGH','params':{'min_rest_hours':value,'boundary_inclusive':True,'day_after_night_forbidden':False}}}}
        check('nonfinite-rest-'+str(value)+'-refused',G.detect(roster,r)['run_status']=='ERROR')
    for name,r in [('rules-list',[]),('rule-spec-list',{'rules':{'H2':[]}}),('params-list',{'rules':{'H2':{'status':'HIGH','params':['bad']}}})]:
        try:ok=G.detect(roster,r)['run_status']=='ERROR'
        except Exception:ok=False
        check(name+'-refused',ok)
    null_rules={'rules':{'H1':{'status':'HIGH','params':{'min_rn_by_band':dict(low=0,normal=0,high=0,surge=0),'charge_counts_toward_h1':True,'missing_band_policy':'refuse'}},'H8':{'status':'HIGH','params':None}}}
    null_env=G.detect(roster,null_rules)
    check('h8-null-parameters-skipped',null_env['run_status']=='COMPLETED' and any(x['rule_id']=='H8' and x['ratified'] and x['scope']=='all' for x in null_env['rules_skipped']))
    null_set=base/'h8-null-set';M.make_set(str(null_set),1,1,'h8-null','both');null_path=base/'h8-null-rules.json';write(null_path,null_rules)
    null_seal=M.seal(str(null_set),str(null_path))
    check('h8-null-parameters-not-evaluated',set(M.verdicts(str(null_set),M.load_set(str(null_set)),null_seal).values())=={'not-evaluated'})
    output=base/'detector-output.json';output.write_text('preserve evidence',encoding='utf-8');prior=output.read_bytes()
    command=[sys.executable,'-B',str(ROOT/'detector/gapcheck.py'),'--rules',str(RULES),'--input',str(ROOT/'fixtures/LEGAL-PC-01.json')]
    p=subprocess.run(command+['--out',str(output)],capture_output=True,text=True)
    check('detector-output-preserved',p.returncode==2 and 'REFUSED' in p.stderr and output.read_bytes()==prior)
    new=base/'new-output.json';p=subprocess.run(command+['--out',str(new)],capture_output=True,text=True)
    check('fresh-detector-output-works',p.returncode==0 and json.loads(new.read_text())['run_status']=='COMPLETED')
    spec=importlib.util.spec_from_file_location('evidence_renderer',ROOT/'tools/render_evidence.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
    for name in ('../outside.py','/outside.py','C:outside.py','detector\\gapcheck.py','.git/config','docs/demo-results.json'):
        check('publication-source-path-refused-'+name,refused(lambda:renderer.source_path(name)))
    check('publication-safe-source-accepted',renderer.source_path('detector/gapcheck.py')==ROOT/'detector/gapcheck.py')
print(f'{sum(results)} PASS · {len(results)-sum(results)} FAIL')
if unverified:print('Unverified groups: '+str(len(unverified)))
sys.exit(1 if not all(results) else 0)
