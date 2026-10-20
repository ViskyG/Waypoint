"""Shared read-only projections for Map, Plan, packet and catalogue."""
from __future__ import annotations
import json
from .domain import ContractError, descendants
from .dependencies import effective_relations, evaluate_availability
from .algorithm_evidence import algorithm_views
from .source_health import aggregate_source_health, source_is_connected

PROJECTION_VERSION='observability/1'
CAPABILITIES=['observability_profile_1','effective_dependencies_1','typed_items_1','project_summary_1','algorithm_evidence_1']

def workspace_basis(plan,node=None,workspace=None):
    profile=plan.get('x_observability',{})
    local=plan['nodes'].get(node,{}).get('x_observability',{}) if node else {}
    return {'consumer':workspace or local.get('workspace_ref') or profile.get('workspace_ref'), 'project':profile.get('project_workspace_ref')}

def basis(store,document,node=None,workspace=None):
    project=document['plan']['project_id']
    seq=store.db.execute('SELECT COALESCE(MAX(seq),0) FROM events WHERE project=?',(project,)).fetchone()[0]
    return {'plan_version':document['version'],'cursor':seq,'projection_version':PROJECTION_VERSION,'workspace_ref':workspace_basis(document['plan'],node,workspace)}

def evaluated_relations(plan,node,phase,observations,workspace=None):
    """All applicable context, with the exact workspace used for evaluation."""
    refs=workspace_basis(plan,node,workspace)
    return [{**r,**evaluate_availability(r,observations,refs),'workspace_ref':refs}
            for r in effective_relations(plan,node,phase)]

def prerequisite_view(store,document,node,phase='start',workspace=None,before=None):
    plan=document['plan']; observations=store.observations(plan['project_id'],'dependency',before=before)
    return evaluated_relations(plan,node,phase,observations,workspace)

def actor_active(actor,sources):
    if actor.get('activity') not in {'running','active'} or actor.get('activity_historical'):return False
    if actor.get('activity_source')=='demo':return True
    health=next((s for s in sources if s.get('source_key')==actor.get('activity_source')),None)
    return bool(health and source_is_connected(health))

def activity_views(plan,agents,scopes,sources):
    active={a['id'] for a in agents if actor_active(a,sources)}
    associated={n:set() for n in plan['nodes']}
    for scope in scopes:
        for node in scope.get('node_ids',[]):
            if node in associated:associated[node].add(scope['agent_id'])
    by_node={}
    for node in plan['nodes']:
        children=descendants(plan,node)-{node}
        direct=associated[node];deep=set().union(*(associated[c] for c in children)) if children else set()
        scoped={n for n in children|{node} if associated[n]&active}
        leaves={n for n in scoped if not (descendants(plan,n)-{n})&scoped}
        working=(direct|deep)&active
        by_node[node]={'direct_agent_ids':sorted(direct),'descendant_agent_ids':sorted(deep),'active_agent_ids':sorted(working),'active_leaf_ids':sorted(leaves),'distinct_active_agents':len(working),'distinct_active_leaves':len(leaves)}
    return by_node

def augment_state(store,state):
    from .warning_history import dependency_history
    plan=state['plan'];project=plan['project_id'];document={'plan':plan,'version':state['version']}
    shared_basis=basis(store,document)
    sources=aggregate_source_health(state['sources'])['sources']
    active=activity_views(plan,state['agents'],state['scopes'],sources)
    statuses={x['id']:x for x in state['node_states']}
    # Read once per consistent Store lock, never once per card/transcript.
    observations=store.observations(project,'dependency')
    views={}
    for node,definition in plan['nodes'].items():
        extension=definition.get('x_observability',{}); intent=extension.get('intent')
        prerequisites={phase:evaluated_relations(plan,node,phase,observations) for phase in ('start','finish')}
        views[node]={'id':node,'intent':intent or None,'description_incomplete':not intent,'status':statuses.get(node,{}),'activity':active[node],'prerequisites':prerequisites,'basis':{**shared_basis,'workspace_ref':workspace_basis(plan,node)},**dependency_history(store,project,node),'algorithm_refs':extension.get('algorithm_refs',[])}
    algorithm_cursor=store.db.execute('SELECT MAX(seq) FROM algorithm_facts WHERE project=?',(project,)).fetchone()[0] or 0
    return {**state,'sources':sources,'basis':shared_basis,'node_views':views,'algorithm_cursor':algorithm_cursor,'purpose':plan.get('x_observability',{}).get('purpose'),'capabilities':CAPABILITIES}

def project_summaries(store):
    summaries=[]
    for info in store.db.execute('SELECT project,title,purpose,version FROM project_info ORDER BY project LIMIT 1000').fetchall():
        project=info['project']
        def rows(table):return [json.loads(r[0]) for r in store.db.execute('SELECT body FROM '+table+' WHERE project=?',(project,))]
        sources=rows('source_health');agents=rows('agents');scopes=rows('scopes')
        health=aggregate_source_health(sources)
        active={a['id'] for a in agents if actor_active(a,sources)}
        nodes={n for scope in scopes if scope['agent_id'] in active for n in scope.get('node_ids',[])}
        # Metadata memberships plus parent IDs only; no item bodies/transcripts.
        plan=store.plan(project)['plan']
        leaves={n for n in nodes if not (descendants(plan,n)-{n})&nodes}
        latest=store.db.execute('SELECT MAX(observed_at) FROM events WHERE project=?',(project,)).fetchone()[0]
        known=health['state'] in {'connected','disconnected'}
        summaries.append({'project_id':project,'title':info['title'],'version':info['version'],'purpose':info['purpose'],'distinct_active_agents':len(active) if known else None,'distinct_active_blocks':len(leaves) if known else None,'last_observed_at':latest,'source_health':health})
    return summaries

def algorithms(store,project,node=None,deep=False,version=None):
    document=store.plan(project,version)
    # Definitions/associations are plan-sized. Evidence summary is a SQL
    # aggregate over compact metadata; no observation bodies enter this list.
    records=algorithm_views(document['plan'],[],node,deep)
    for record in records:
        record.update(store.algorithm_summary(project,record['id'],record['definition']),
                      evidence_scope='summary',comparisons_scope='summary')
    return {'basis':basis(store,document),'algorithms':records}

def algorithm(store,project,aid,version=None,before=None,limit=100):
    document=store.plan(project,version);plan=document['plan']
    definition=plan.get('x_observability',{}).get('algorithms',{}).get(aid)
    if definition is None:raise ContractError('not_found','Algorithm not found')
    page=store.algorithm_page(project,aid,before,limit)
    page_ids={event['event_id'] for event in page['evidence']}
    references=set()
    for event in page['evidence']:
        comparison=event['payload'].get('comparison')
        if comparison:references.update(comparison[key] for key in ('baseline_observation_id','candidate_observation_id'))
    referenced=store.algorithm_observations_by_id(project,aid,references-page_ids)
    # Preserve historical baseline revisions while projecting comparisons only
    # for this page. Reference lookups cannot add hidden rows to the response.
    scoped_plan={**plan,'x_observability':{**plan.get('x_observability',{}),'algorithms':{aid:definition}}}
    record=algorithm_views(scoped_plan,[*page['evidence'],*referenced])[0]
    record['evidence']=[event for event in record['evidence'] if event['event_id'] in page_ids]
    record['comparisons']=[comparison for comparison in record['comparisons'] if comparison['event_id'] in page_ids]
    record.update(store.algorithm_summary(project,aid,definition),has_more=page['has_more'],
                  before=page['before'],evidence_scope='page',comparisons_scope='page')
    return {'basis':basis(store,document),'algorithm':record}
