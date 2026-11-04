"""Publish synthetic raw answers with an allowlist of reproducibility metadata."""
from pathlib import Path, PureWindowsPath
import argparse,hashlib,json,re

def projection(record):
    meta=record['metadata'];identity=meta.get('effective_model_identity',{})
    requested=identity.get('requested',{});settings=meta.get('effective_settings',{})
    effective=settings.get('effective',{})
    output={k:record[k] for k in ('rater','request_id','text','error')}
    output['metadata']={
        'finish_reason':meta.get('finish_reason'),
        'elapsed_seconds':meta.get('elapsed_seconds'),
        'usage':meta.get('usage'),
        'model':{k:requested[k] for k in ('studio_id','bytes','snapshot','sha256') if k in requested},
        'reported_model_file':PureWindowsPath(str(identity.get('reported',''))).name,
        'effective_settings':{k:effective[k] for k in ('gguf_variant','context_length','cache_type_kv','parallel_slots','gpu_layers','gpu_memory_mode','engine','speculative_type','spec_draft_n_max','reasoning_budget') if k in effective},
        'drafter':{k:settings.get('drafter',{})[k] for k in ('spec_drafter_kind','spec_fallback_reason') if k in settings.get('drafter',{})},
        'generation_parameters_source':'RATER-RUN-CONTRACT.json; requested values are not relabeled as API-echoed effective values',
        'raw_text_sha256':hashlib.sha256(record['text'].encode('utf8')).hexdigest(),
    }
    rendered=json.dumps(output)
    # Refuse unexpected private material; never silently edit an observation.
    if re.search(r'(?i)(?:[a-z]:\\\\|/Users/|/home/|bearer\s|ghp_[a-z0-9]|github_pat_)',rendered):
        raise ValueError('Unexpected host path or credential marker in public projection')
    return output

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args()
    records=[json.loads(line) for line in args.input.read_text(encoding='utf8').splitlines() if line.strip()]
    projected=[projection(r) for r in records]
    assert all(a['text']==b['text'] and a['error']==b['error'] for a,b in zip(records,projected))
    data=''.join(json.dumps(r,separators=(',',':'))+'\n' for r in projected)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8') as f:f.write(data)
    print(json.dumps({'records':len(projected),'assistant_texts_unchanged':True,'errors_unchanged':True,
        'source_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
        'public_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':main()
