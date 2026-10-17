#!/usr/bin/env python3
"""Record a reviewed local result and explicit output receipts, preserving history.

Requires a fresh export and evidence file in this working copy. Never marks an
external input available and never invokes an executor. Network submission is an
explicit separate CLI step: wp emit <prepared-bundle>.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'waypoint'))
from waypoint.dependencies import effective_requirements
from waypoint.domain import now, digest
from waypoint.read_models import workspace_basis

def prepare(export,packet,evidence,actor):
    plan=export['plan'];version=export['version']
    if packet not in plan['nodes'] or not packet.startswith('WPT-N'):raise ValueError('Expected stage2 packet')
    path=(ROOT/evidence).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('Existing local evidence required')
    revision='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
    at=now();events=[]
    def event(kind,payload,nodes):
        eid='stage2-'+digest([version,packet,evidence,revision,kind,payload,nodes])[:40]
        events.append({'event_id':eid,'project_id':plan['project_id'],'source':'stage2-acceptance','kind':kind,'agent_id':actor,'at':at,'node_ids':nodes,'payload':payload})
    for consumer in plan['nodes']:
        for phase in ('start','finish'):
            for req in effective_requirements(plan,consumer,phase):
                if req['producer_id']!=packet or req['classification']!='requires':continue
                workspace=workspace_basis(plan,consumer).get(req['workspace_policy'])
                if not workspace:raise ValueError('Availability requires explicit actual workspace')
                event('dependency.observation',{'edge_id':req['edge_id'],'consumer_id':consumer,'requirement_fingerprint':req['requirement_fingerprint'],'workspace_ref':workspace,'availability':'available','basis':{'kind':'artifact','ref':evidence,'revision':revision,'explanation':'Reviewed concrete packet result exists in this installed working copy; completion status alone is not the basis.'},'occurred_at':at},[consumer])
    event('node.result',{'summary':'Target verified; '+evidence,'evidence_ref':evidence,'evidence_revision':revision,'plan_version':version},[packet])
    event('node.status',{'status':'done','explanation':'Verified concrete result: '+evidence},[packet])
    return {'events':events}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--export',type=Path,required=True);p.add_argument('--packet',required=True);p.add_argument('--evidence',required=True);p.add_argument('--actor',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=prepare(json.loads(a.export.read_text()),a.packet,a.evidence,a.actor)
    with a.out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    a.out.chmod(0o600);print(json.dumps({'packet':a.packet,'prepared_events':len(result['events']),'submitted':False}))
