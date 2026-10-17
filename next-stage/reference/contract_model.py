"""Executable design oracle, NOT the deployed Waypoint implementation.

No network, databases or agent calls. N01/N02/N04/N05 adopt/test these semantics
inside current project modules; they do not install a second runtime resolver.
"""
from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from typing import Any

CATEGORIES = frozenset({'message','explanation','plan','command','tool','change','test','agent','other'})

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def ancestry(plan: dict, node_id: str) -> list[str]:
    result, seen = [], set()
    current = node_id
    while current is not None:
        if current in seen: raise ValueError('parent_cycle')
        if current not in plan['nodes']: raise ValueError('missing_parent')
        seen.add(current); result.append(current)
        current = plan['nodes'][current].get('parent')
    return result

def condition_fingerprint(plan: dict, edge_id: str, consumer: str) -> str:
    edge = plan['edges'][edge_id]; spec = edge['x_observability']; condition = spec['condition']
    output = plan['nodes'][edge['from']]['x_observability']['outputs'][condition['output_id']]
    if output['revision'] != condition['revision']: raise ValueError('output_revision_mismatch')
    return fingerprint({'from':edge['from'],'declared_target':edge['to'],'consumer':consumer,
      'phase':spec['phase'],'target_scope':spec['target_scope'],'condition':condition,
      'definition':' '.join(output['definition'].split())})

def effective_requirements(plan: dict, node_id: str, phase: str = 'start') -> list[dict]:
    if phase not in {'start','finish'}: raise ValueError('invalid_phase')
    chain = ancestry(plan,node_id); result=[]
    for edge_id,edge in sorted(plan.get('edges',{}).items()):
        spec = edge.get('x_observability')
        if edge['to'] not in chain: continue
        if spec is None:
            # Legacy edge has unknown inheritance; retain as unresolved context,
            # never silently treat direct-only absence as readiness.
            result.append({'edge_id':edge_id,'producer_id':edge['from'],'consumer_id':node_id,
              'declared_target_id':edge['to'],'phase':phase,'inherited':edge['to']!=node_id,
              'classification':'legacy_unknown','requirement_fingerprint':None})
            continue
        if spec['relation']=='order' or spec['phase']!=phase: continue
        inherited=edge['to']!=node_id
        if inherited and spec['target_scope']!='subtree': continue
        result.append({'edge_id':edge_id,'producer_id':edge['from'],'consumer_id':node_id,
          'declared_target_id':edge['to'],'phase':phase,'inherited':inherited,
          'output_id':spec['condition']['output_id'],'condition_revision':spec['condition']['revision'],
          'requirement_fingerprint':condition_fingerprint(plan,edge_id,node_id),
          'classification':'requires','why':spec['why']})
    return result

def effective_cycle_nodes(plan: dict) -> list[str]:
    # Conservative dependency-cycle diagnostic, not an execution-permission gate.
    adjacency=defaultdict(set); indegree={n:0 for n in plan['nodes']}
    for node in plan['nodes']:
        for phase in ('start','finish'):
            for r in effective_requirements(plan,node,phase):
                if r['classification']!='requires': continue
                source=r['producer_id']
                if node not in adjacency[source]: adjacency[source].add(node); indegree[node]+=1
    pending=[n for n,d in indegree.items() if d==0]
    while pending:
        n=pending.pop()
        for consumer in adjacency[n]:
            indegree[consumer]-=1
            if indegree[consumer]==0: pending.append(consumer)
    return sorted(n for n,d in indegree.items() if d)

def evaluate_requirement(requirement: dict, observations: list[dict], workspace_ref: str) -> dict:
    if not requirement.get('requirement_fingerprint'):
        return {'state':'unknown','reason':'unclassified_legacy_edge','receipts':[]}
    candidates=[o for o in observations if o.get('requirement_fingerprint')==requirement['requirement_fingerprint']
       and o.get('workspace_ref')==workspace_ref and o.get('consumer_id')==requirement['consumer_id']]
    superseded={x for o in candidates for x in o.get('supersedes',[])}
    candidates=[o for o in candidates if o['event_id'] not in superseded]
    # Within one reporter the latest durable observation replaces its own previous
    # statement. Different reporters' conflicting current assertions remain visible.
    by_source={}
    for o in candidates:
        if not o.get('basis',{}).get('ref'): raise ValueError('missing_basis')
        if o['availability']=='waived' and not o['basis'].get('explanation'): raise ValueError('waiver_needs_reason')
        old=by_source.get(o['source'])
        if old is None or o['seq']>old['seq']: by_source[o['source']]=o
    current=list(by_source.values())
    if not current: return {'state':'unknown','reason':'no_current_matching_evidence','receipts':[]}
    claims={o['availability'] for o in current}
    states={'available':'satisfied','missing':'missing','waived':'waived'}
    if not claims<=states.keys(): raise ValueError('invalid_availability')
    return {'state':states[next(iter(claims))] if len(claims)==1 else 'conflict',
            'reason':'matched_evidence' if len(claims)==1 else 'contradictory_reporters',
            'receipts':sorted(o['event_id'] for o in current)}

def filtered_page(items: list[dict], *, project: str, categories: set[str]|None=None,
                  only_errors: bool=False, node_ids: set[str]|None=None,
                  boundary: tuple|None=None, limit: int=100) -> dict:
    """Pure paging oracle. Runtime must use indexed SQL, not this full list scan."""
    if categories is not None and not categories<=CATEGORIES: raise ValueError('unknown_category')
    if not 1<=limit<=500: raise ValueError('limit_out_of_bounds')
    unique={}
    for item in items:
        if item['project_id']!=project: continue
        k=(item['agent_id'],item['id'])
        if k not in unique or item.get('last_seq',0)>unique[k].get('last_seq',0): unique[k]=item
    def key(i): return i['first_seq'],i['agent_id'],i['id']
    found=[]
    for item in unique.values():
        if categories is not None and item.get('category','other') not in categories: continue
        if only_errors and not item.get('is_error',False): continue
        if node_ids is not None and not node_ids.intersection(item.get('node_ids',[])): continue
        if boundary is not None and key(item)>=boundary: continue
        found.append(item)
    found.sort(key=key,reverse=True)
    selected=found[:limit]
    return {'items':list(reversed(selected)), 'has_more':len(found)>limit,
            'before':key(selected[-1]) if selected and len(found)>limit else None}

def validate_profile(plan: dict) -> list[str]:
    obs=plan.get('x_observability',{})
    if obs.get('schema')!='waypoint.observability/1': raise ValueError('profile_missing')
    algorithms=obs.get('algorithms',{})
    for node_id,node in plan['nodes'].items():
        ancestry(plan,node_id)
        x=node.get('x_observability',{})
        intent=x.get('intent')
        if intent and any(not isinstance(intent.get(f),str) or not intent[f].strip() for f in ['summary','context','change']):
            raise ValueError('incomplete_intent')
        if set(x.get('algorithm_refs',[]))-set(algorithms): raise ValueError('missing_algorithm')
        for output in x.get('outputs',{}).values():
            if type(output.get('revision')) is not int or output['revision']<1: raise ValueError('bad_revision')
            if not output.get('definition','').strip(): raise ValueError('missing_output_definition')
    for edge_id,edge in plan['edges'].items():
        if edge['from'] not in plan['nodes'] or edge['to'] not in plan['nodes']: raise ValueError('missing_endpoint')
        spec=edge.get('x_observability')
        if spec is None: continue
        if spec.get('relation') not in {'requires','order'}: raise ValueError('relation')
        if spec.get('phase') not in {'start','finish'} or spec.get('target_scope') not in {'node','subtree'}: raise ValueError('scope')
        if not spec.get('why','').strip(): raise ValueError('missing_reason')
        if spec['relation']=='requires': condition_fingerprint(plan,edge_id,edge['to'])
    return effective_cycle_nodes(plan)

def compare_measurements(baseline: dict, candidate: dict) -> dict:
    fields=['metric','unit','method','environment_ref','dataset_ref','workload_ref','semantic_revision','direction']
    mismatch=[f for f in fields if not baseline.get(f) or baseline.get(f)!=candidate.get(f)]
    if mismatch:return {'state':'not_comparable','reasons':mismatch}
    if baseline.get('correctness')!='passed' or candidate.get('correctness')!='passed':
        return {'state':'not_established','reasons':['correctness_not_confirmed']}
    for m in (baseline,candidate):
        if type(m.get('n')) is not int or m['n']<1: raise ValueError('sample_count')
        if isinstance(m.get('value'),bool) or not isinstance(m.get('value'),(int,float)): raise ValueError('measurement_value')
        import math
        if not math.isfinite(m['value']): raise ValueError('measurement_value')
    a,b=baseline['value'],candidate['value']
    better=b<a if candidate['direction']=='lower' else b>a if candidate['direction']=='higher' else None
    if better is None:raise ValueError('direction')
    return {'state':'unchanged' if a==b else 'improved' if better else 'regressed',
            'baseline':a,'candidate':b,'unit':candidate['unit'],
            'note':'Only this metric under matching conditions, not overall algorithm optimality.'}
