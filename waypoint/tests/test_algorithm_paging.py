"""Bounded synthetic Store/API evidence; never real Codex receipts."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from waypoint.algorithm_evidence import algorithm_views
from waypoint.read_models import algorithm, algorithms
from waypoint.server import create_app
from waypoint.store import Store


def graph():
    source = json.loads((Path(__file__).resolve().parents[2] / 'next-stage/roadmap/ROADMAP.plan.json').read_text())
    definition = copy.deepcopy(source['x_observability']['algorithms']['ALG-MERGE'])
    definition.update(id='merge', definition_revision=1)
    definition['implementation']['revision'] = 'current-code'
    other = copy.deepcopy(definition); other['id'] = 'other'
    return {'schema':'waypoint.plan/1','project_id':'p','title':'Synthetic algorithm pages',
            'nodes':{'N':{'title':'N','x_observability':{'algorithm_refs':['merge']}}},'edges':{},
            'x_observability':{'schema':'waypoint.observability/1','algorithms':{'merge':definition,'other':other}}}


def observation(eid, *, aid='merge', revision='current-code', outcome='not_run', measurement=None,
                kind='correctness', comparison=None, definition_revision=1, note='Synthetic paging fixture'):
    return {'event_id':eid,'project_id':'p','source':'synthetic-paging','kind':'algorithm.observation',
            'at':'2026-10-20T12:00:00Z','node_ids':[],'edge_ids':[],
            'payload':{'algorithm_id':aid,'definition_revision':definition_revision,
                'implementation_ref':revision,'observation_kind':kind,
                'correctness':{'outcome':outcome,'evidence_refs':['fixture:'+eid] if outcome!='not_run' else []},
                'measurement':measurement,'comparison':comparison,'note':note}}


def measurement(value):
    return {'metric':'latency','unit':'ms','statistic':'median','method':'synthetic',
            'environment_ref':'env','dataset_ref':'data','workload_ref':'work',
            'semantic_revision':'same-behavior','n':5,'value':value,'direction':'lower'}


@pytest.fixture
def store(tmp_path):
    result=Store(tmp_path/'db.sqlite'); result.import_plan(graph(),None,'initial')
    yield result
    result.close()


def test_every_page_reachable_and_full_history_flags_do_not_use_last_hundred(store):
    events=[observation('early-failure',outcome='failed'),
            observation('early-integration',kind='integration',outcome='passed',measurement=measurement(10))]
    events += [observation('other-'+str(i),aid='other') for i in range(80)]
    events += [observation('record-'+str(i)) for i in range(235)]
    store.ingest(events)
    before=None; seen=[]; sizes=[]
    while True:
        record=algorithm(store,'p','merge',before=before,limit=100)['algorithm']
        assert record['tested']=='failed' and record['measured'] and record['installed']
        assert record['correctness_conflict'] is True
        assert record['correctness_counts']=={'passed':1,'failed':1,'not_run':235}
        assert record['evidence_count']==237 and record['current_evidence_count']==237
        assert record['evidence_scope']=='page'
        seqs=[event['seq'] for event in record['evidence']]
        assert seqs==sorted(seqs)
        sizes.append(len(seqs)); seen.extend(event['event_id'] for event in record['evidence'])
        if not record['has_more']:
            assert record['before'] is None
            break
        assert record['before']==min(seqs)
        before=record['before']
    assert sizes==[100,100,37]
    assert len(set(seen))==237
    assert set(seen)=={event['event_id'] for event in events if event['payload']['algorithm_id']=='merge'}
    assert algorithm(store,'p','merge',before=-1)['algorithm']['evidence']==[]


def test_page_comparisons_resolve_older_revisions_and_do_not_cross_algorithms(store):
    baseline=observation('baseline',revision='old-code',outcome='passed',measurement=measurement(12))
    candidate=observation('candidate',outcome='passed',measurement=measurement(8))
    store.ingest([baseline,candidate,observation('other-baseline',aid='other',outcome='passed',measurement=measurement(15))])
    store.ingest([observation('padding-'+str(i)) for i in range(130)])
    def comparison(a,b):
        return {'baseline_observation_id':a,'candidate_observation_id':b,'constraints':{},'claim':'Synthetic metric comparison'}
    store.ingest([observation('comparison',comparison=comparison('baseline','candidate')),
                  observation('foreign-comparison',comparison=comparison('other-baseline','candidate')),
                  observation('old-comparison',revision='old-code',comparison=comparison('baseline','candidate'))])
    record=algorithm(store,'p','merge',limit=3)['algorithm']
    assert {e['event_id'] for e in record['evidence']}=={'comparison','foreign-comparison','old-comparison'}
    projected={e['event_id']:e for e in record['comparisons']}
    assert projected['comparison']['state']=='improved'
    assert projected['comparison']['baseline_freshness']=='stale'
    assert projected['comparison']['candidate_freshness']=='current'
    assert projected['foreign-comparison']['state']=='not_comparable'
    assert projected['foreign-comparison']['reasons']==['observation_not_found']
    assert projected['old-comparison']['freshness']=='stale'
    assert record['comparisons_summary']=={'total':3,'current':2,'stale':1,'unresolved':1}
    old_page=algorithm(store,'p','merge',before=record['before'],limit=100)['algorithm']
    assert old_page['comparisons']==[]
    assert old_page['comparisons_summary']==record['comparisons_summary']


def test_registry_and_detail_select_before_body_reads_with_bounded_output(store):
    store.ingest([observation('large-'+str(i),note='x'*16000) for i in range(220)])
    queries=[]; store.db.set_trace_callback(queries.append)
    try:
        registry=algorithms(store,'p',node='N')
        assert len(registry['algorithms'])==1
        record=registry['algorithms'][0]
        assert record['evidence_count']==220
        assert record['evidence']==[] and record['comparisons']==[]
        assert record['evidence_scope']=='summary' and record['comparisons_scope']=='summary'
        assert len(json.dumps(registry))<15000
        assert not any('SELECT body FROM algorithm_evidence' in query for query in queries)
        queries.clear()
        detail=algorithm(store,'p','merge',limit=7)['algorithm']
        assert len(detail['evidence'])==7
        body_queries=[q for q in queries if 'SELECT body FROM algorithm_evidence' in q]
        assert len(body_queries)==1 and 'event_id IN (' in body_queries[0]
        assert len(body_queries[0].split('event_id IN (')[1].split(','))==7
        id_select=next(q for q in queries if 'SELECT event_id,seq FROM algorithm_evidence' in q)
        assert 'algorithm=' in id_select and 'LIMIT 8' in id_select
        plan=store.db.execute('EXPLAIN QUERY PLAN SELECT event_id,seq FROM algorithm_evidence WHERE project=? AND algorithm=? AND seq<? ORDER BY seq DESC LIMIT ?',('p','merge',1000,8)).fetchall()
        assert any('algorithm_lookup' in row['detail'] for row in plan)
    finally:
        store.db.set_trace_callback(None)


def test_summary_matches_historical_definition_freshness_and_conflicts(store):
    definition=graph()['x_observability']['algorithms']['merge']
    events=[observation('string-current',outcome='passed'),
            observation('object-current',revision=copy.deepcopy(definition['implementation']),outcome='failed'),
            observation('old-definition',definition_revision=2,outcome='passed',measurement=measurement(1)),
            observation('old-code',revision='old-code',kind='integration',outcome='passed')]
    store.ingest(events)
    stored=store.observations('p','algorithm')
    previous=store.head('p')
    expected=algorithm_views(store.plan('p')['plan'],stored)[0]
    record=algorithm(store,'p','merge',limit=1)['algorithm']
    for key in ('tested','measured','installed'):
        assert record[key]==expected[key]
    assert record['correctness_conflict'] is True
    assert record['current_evidence_count']==2 and record['stale_evidence_count']==2
    changed=graph(); changed['x_observability']['algorithms']['merge']['implementation']['revision']='new-code'
    store.import_plan(changed,previous,'changed')
    assert algorithm(store,'p','merge')['algorithm']['tested']=='not_run'
    assert algorithm(store,'p','merge',version=previous)['algorithm']['tested']=='failed'


def test_additive_schema3_backfill_restart_and_rebuild_preserve_immutable_history(tmp_path):
    path=tmp_path/'db.sqlite'; store=Store(path); store.import_plan(graph(),None,'initial')
    store.ingest([observation('old-failure',outcome='failed'),observation('old-pass',outcome='passed')],
                 cursor={'source_key':'synthetic','offset':42})
    before=[tuple(row) for row in store.db.execute('SELECT seq,event_id,hash,body FROM events ORDER BY seq')]
    version=store.head('p')
    store.db.execute('DROP TABLE algorithm_facts')
    store.db.execute("DELETE FROM meta WHERE key='algorithm_facts_projection'")
    store.close()
    for _ in range(2):
        store=Store(path)
        assert store.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0]=='3'
        assert store.db.execute('SELECT COUNT(*) FROM algorithm_facts').fetchone()[0]==2
        assert algorithm(store,'p','merge')['algorithm']['correctness_conflict'] is True
        assert store.head('p')==version and store.cursor('synthetic')['offset']==42
        assert [tuple(row) for row in store.db.execute('SELECT seq,event_id,hash,body FROM events ORDER BY seq')]==before
        store.rebuild()
        assert store.db.execute('SELECT COUNT(*) FROM algorithm_facts').fetchone()[0]==2
        store.close()



def test_schema3_legacy_write_and_rebuild_reconcile_missing_and_orphan_facts(tmp_path, monkeypatch):
    path=tmp_path/'db.sqlite'; store=Store(path); store.import_plan(graph(),None,'initial')
    store.ingest([observation('existing-pass',outcome='passed')])
    assert store.db.execute("SELECT value FROM meta WHERE key='algorithm_facts_projection'").fetchone()[0]=='1'
    # Reproduce the old schema-3 projection writer: accepted immutable ledger,
    # event-plan and algorithm_evidence are updated, additive facts are unknown.
    # The persistent projection marker remains '1', as with the old binary.
    store._algorithm_facts_ready=False
    store.ingest([observation('legacy-failure',outcome='failed')],
                 cursor={'source_key':'legacy-fixture','offset':99})
    assert store.db.execute("SELECT value FROM meta WHERE key='algorithm_facts_projection'").fetchone()[0]=='1'
    assert store.db.execute("SELECT COUNT(*) FROM algorithm_facts WHERE event_id='legacy-failure'").fetchone()[0]==0
    # A stale projection can contain an orphan after a legacy rebuild. Equal
    # table counts deliberately rule out a count-only startup reconciliation.
    store._index_algorithm_fact({**observation('orphan-fact'), 'seq':999})
    assert store.db.execute('SELECT COUNT(*) FROM algorithm_facts').fetchone()[0]==2
    assert store.db.execute('SELECT COUNT(*) FROM algorithm_evidence').fetchone()[0]==2
    ledger=[tuple(row) for row in store.db.execute('SELECT seq,event_id,hash,body FROM events ORDER BY seq')]
    version=store.head('p');store.close()
    indexed=[];original=Store._index_algorithm_fact
    def record_index(self,event):
        indexed.append(event['event_id']);return original(self,event)
    monkeypatch.setattr(Store,'_index_algorithm_fact',record_index)
    for expected in [['legacy-failure'],[]]:
        store=Store(path)
        assert indexed==expected
        indexed.clear()
        assert store.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0]=='3'
        assert {row[0] for row in store.db.execute('SELECT event_id FROM algorithm_facts')}=={'existing-pass','legacy-failure'}
        summary=algorithms(store,'p',node='N')['algorithms'][0]
        assert summary['evidence_count']==2 and summary['tested']=='failed' and summary['correctness_conflict']
        assert store.head('p')==version and store.cursor('legacy-fixture')['offset']==99
        assert [tuple(row) for row in store.db.execute('SELECT seq,event_id,hash,body FROM events ORDER BY seq')]==ledger
        store.close()


def test_authenticated_api_preserves_page_contract(tmp_path):
    app=create_app(tmp_path,tokens={'read':'synthetic-read','write':'synthetic-write'},testing=True)
    app.state.store.import_plan(graph(),None,'initial')
    app.state.store.ingest([observation('api-'+str(i)) for i in range(103)])
    with TestClient(app) as client:
        headers={'Authorization':'Bearer synthetic-read'}
        assert client.get('/api/p/p/algorithms').status_code==401
        registry=client.get('/api/p/p/algorithms?node=N',headers=headers).json()
        assert registry['algorithms'][0]['evidence_count']==103
        assert registry['algorithms'][0]['evidence']==[]
        page=client.get('/api/p/p/algorithms/merge?limit=100',headers=headers).json()['algorithm']
        assert len(page['evidence'])==100 and page['has_more']
        old=client.get('/api/p/p/algorithms/merge',params={'before':page['before'],'limit':100},headers=headers).json()['algorithm']
        assert len(old['evidence'])==3 and not old['has_more'] and old['before'] is None
        assert not {e['event_id'] for e in page['evidence']} & {e['event_id'] for e in old['evidence']}
        assert client.get('/api/p/p/algorithms/missing',headers=headers).status_code==404
