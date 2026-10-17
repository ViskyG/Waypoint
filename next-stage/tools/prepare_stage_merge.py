#!/usr/bin/env python3
"""Prepare a guarded stage addition from a fresh exported plan. NEVER calls services."""
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def prepare(export: dict,stage: dict) -> dict|None:
    current=export.get('plan'); version=export.get('version') or export.get('base_version')
    if not isinstance(current,dict) or not isinstance(version,str) or not version: raise ValueError('Need fresh {version,plan} or {base_version,plan} export')
    if export.get('version') and export.get('base_version') and export['version']!=export['base_version']:raise ValueError('Conflicting export base versions')
    if current.get('project_id')!=stage['project_id']: raise ValueError('Project mismatch; no implicit copy between projects')
    if current.get('schema')!='waypoint.plan/1':raise ValueError('Unsupported native schema')
    delivery=stage['x_roadmap']['delivery_id']; stage_hash=digest(stage)
    existing=current.get('x_roadmap',{}).get('stage_imports',{}).get(delivery)
    if existing:
        if existing['input_sha256']==stage_hash:return None  # retain subsequent live edits
        raise ValueError('Delivery ID already used with different content')
    profile=current.get('x_observability',{}).get('schema')
    if profile not in (None,'waypoint.observability/1'):raise ValueError('Unknown newer profile; reconcile instead of downgrading')
    policy=current.get('x_roadmap',{}).get('resource_policy')
    if policy not in (None,'MIXED'):raise ValueError('Different current resource policy; do not replace it')
    result=copy.deepcopy(current)
    for collection in ['nodes','edges']:
        target=result.setdefault(collection,{})
        for k,v in stage[collection].items():
            if k in target and target[k]!=v:raise ValueError(f'Conflicting {collection} ID: {k}')
            target.setdefault(k,copy.deepcopy(v))
    if 'WPT-NEXT' not in current['nodes']:
        roots=[n.get('layout',{}).get('x',0) for n in current['nodes'].values() if n.get('parent') is None]
        result['nodes']['WPT-NEXT']['layout']['x']=max(roots,default=-440)+520
    x=result.setdefault('x_observability',{})
    x.setdefault('schema','waypoint.observability/1')
    x.setdefault('purpose',stage['x_observability']['purpose'])
    alg=x.setdefault('algorithms',{})
    for k,v in stage['x_observability']['algorithms'].items():
        if k in alg and alg[k]!=v:raise ValueError(f'Conflicting algorithm ID: {k}')
        alg.setdefault(k,copy.deepcopy(v))
    result.setdefault('x_roadmap',{}).setdefault('stage_imports',{})[delivery]={'input_sha256':stage_hash,'source_base_version':version}
    rid='waypoint-stage2-'+digest([version,stage_hash])[:24]
    return {'plan':result,'base_version':version,'request_id':rid,'merge':False}
def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--export',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
    a.add_argument('--stage',type=Path,default=ROOT/'roadmap/ROADMAP.plan.json');args=a.parse_args()
    try:
        body=prepare(json.loads(args.export.read_text()),json.loads(args.stage.read_text()))
        if body is None:print('ALREADY_IMPORTED: no file written; preserve current stage edits.');return
        if args.out.exists():raise ValueError('Output exists; choose a new path to avoid overwriting a prepared request')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x',encoding='utf-8') as f:json.dump(body,f,ensure_ascii=False,indent=2);f.write('\n')
        print('PREPARED_ONLY:',args.out,'base=',body['base_version'],'request=',body['request_id'])
    except (OSError,ValueError,KeyError,TypeError) as e:a.exit(2,str(e)+'\n')
if __name__=='__main__':main()
