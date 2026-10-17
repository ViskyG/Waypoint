"""Bounded synthetic integration checks; not evidence of a live Codex connection."""
from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from waypoint.dependencies import effective_requirements
from waypoint.domain import canonical, digest, now, validate_event, validate_plan
from waypoint.server import create_app
from waypoint.store import DDL, Store
from test_observability import profile_fixture

READ = {"authorization": "Bearer synthetic-stage2-read-key"}
WRITE = {"authorization": "Bearer synthetic-stage2-write-key"}
TOKENS = {"read": "synthetic-stage2-read-key", "write": "synthetic-stage2-write-key"}


def plan_fixture():
    p = profile_fixture()
    p['x_observability']['workspace_ref'] = 'workspace1'
    return p


def event(eid, kind, payload=None, nodes=(), agent='actor', source='synthetic', at='2026-10-17T10:00:00Z'):
    return {'event_id': eid, 'project_id': 'synthetic', 'source': source, 'kind': kind,
            'agent_id': agent, 'at': at, 'node_ids': list(nodes), 'payload': payload or {}}


def evidence(eid='evidence', *, availability='available', source='reporter', workspace='workspace1'):
    requirement = effective_requirements(plan_fixture(), 'CHILD')[0]
    return event(eid, 'dependency.observation', {'edge_id': 'NEEDS', 'consumer_id': 'CHILD',
        'requirement_fingerprint': requirement['requirement_fingerprint'], 'workspace_ref': workspace,
        'availability': availability, 'occurred_at': '2026-10-17T09:59:00Z',
        'basis': {'kind': 'artifact', 'ref': 'synthetic-artifact', 'explanation': 'Synthetic integration fixture'}},
        nodes=['CHILD'], source=source, at='2026-10-17T10:05:00Z')


@pytest.fixture
def api(tmp_path):
    app = create_app(tmp_path, tokens=TOKENS, testing=True)
    with TestClient(app) as client:
        response = client.post('/api/p/synthetic/plans', headers=WRITE,
                               json={'plan': plan_fixture(), 'request_id': 'stage2-initial'})
        assert response.status_code == 200
        yield client, app.state.store


def make_schema2(path: Path):
    """Construct the actual prior schema shape, not a downgraded schema3 DB."""
    db = sqlite3.connect(path)
    db.executescript(DDL)
    db.execute("INSERT INTO meta VALUES('schema','2')")
    db.execute('CREATE TABLE item_targets(project TEXT NOT NULL,agent TEXT NOT NULL,item TEXT NOT NULL,target_kind TEXT NOT NULL,target_id TEXT NOT NULL,first_seq INTEGER NOT NULL,PRIMARY KEY(project,agent,item,target_kind,target_id))')
    db.execute('CREATE INDEX target_lookup ON item_targets(project,target_kind,target_id,first_seq DESC,agent,item)')
    plan = validate_plan(plan_fixture())[0]
    db.execute('INSERT INTO plans VALUES(?,?,?,?,?,?,?)', ('legacy-v1', 'synthetic', 1, None, digest(plan), '2026-10-17T10:00:00Z', canonical(plan)))
    db.execute('INSERT INTO heads VALUES(?,?)', ('synthetic', 'legacy-v1'))
    native = validate_event(event('old-item', 'item.upsert', {'item_id': 'old', 'type': 'commandExecution',
        'text': 'prior accepted output', 'state': 'failed'}, nodes=['CHILD']))
    db.execute('INSERT INTO events(event_id,hash,project,source,kind,agent,at,body) VALUES(?,?,?,?,?,?,?,?)',
        (native['event_id'], digest(native), native['project_id'], native['source'], native['kind'], native['agent_id'], native['at'], canonical(native)))
    db.execute('INSERT INTO event_plan VALUES(1,?)', ('legacy-v1',))
    item = {**native['payload'], 'id': 'old', 'agent_id': 'actor', 'node_ids': ['CHILD'], 'edge_ids': [],
            'first_seq': 1, 'last_seq': 1, 'attribution': 'explicit', 'at': native['at'],
            'updated_at': native['at'], 'source': native['source'], 'observed_sources': [native['source']],
            'plan_version': 'legacy-v1'}
    db.execute('INSERT INTO items VALUES(?,?,?,?,?,?)', ('synthetic', 'actor', 'old', 1, 1, canonical(item)))
    db.execute('INSERT INTO item_targets VALUES(?,?,?,?,?,?)', ('synthetic', 'actor', 'old', 'node', 'CHILD', 1))
    db.execute('CREATE TABLE unrelated_extension(value TEXT)')
    db.execute("INSERT INTO unrelated_extension VALUES('preserve me')")
    db.commit()
    ledger = db.execute('SELECT seq,event_id,hash,body FROM events').fetchall()
    db.close()
    return ledger


def test_schema2_migration_retains_ledger_receipt_unknown_and_rebuilds(tmp_path):
    path = tmp_path / 'prior.sqlite'
    original = make_schema2(path)
    store = Store(path)
    assert store.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0] == '3'
    assert [tuple(r) for r in store.db.execute('SELECT seq,event_id,hash,body FROM events')] == original
    assert store.events_after('synthetic')['events'][0]['observed_at'] is None
    assert store.items('synthetic', categories='command', only_errors=True)['items'][0]['id'] == 'old'
    store.ingest([event('new-status', 'node.status', {'status': 'working'}, nodes=['CHILD'])])
    assert store.events_after('synthetic')['events'][-1]['observed_at'] is not None
    before = store.items('synthetic')['items']
    assert store.rebuild()['replayed'] == 2
    assert store.items('synthetic')['items'] == before
    assert store.db.execute('SELECT value FROM unrelated_extension').fetchone()[0] == 'preserve me'
    assert store.events_after('synthetic')['events'][0]['observed_at'] is None
    store.close()
    reopened = Store(path)
    assert reopened.items('synthetic', categories='command', only_errors=True)['items'] == before
    assert reopened.events_after('synthetic')['events'][0]['observed_at'] is None
    reopened.close()


def test_interrupted_schema2_migration_rolls_back_and_retry_preserves_input(tmp_path, monkeypatch):
    path = tmp_path / 'prior.sqlite'
    original = make_schema2(path)
    def fail_backfill(self, project, item):
        raise RuntimeError('synthetic interruption')
    with monkeypatch.context() as patch:
        patch.setattr(Store, '_index_facet', fail_backfill)
        with pytest.raises(RuntimeError, match='synthetic interruption'):
            Store(path)
    db = sqlite3.connect(path)
    assert db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0] == '2'
    assert 'observed_at' not in {r[1] for r in db.execute('PRAGMA table_info(events)')}
    assert db.execute("SELECT name FROM sqlite_master WHERE name='item_facets'").fetchone() is None
    assert db.execute('SELECT seq,event_id,hash,body FROM events').fetchall() == original
    db.close()
    store = Store(path)
    assert store.items('synthetic', categories='command')['items'][0]['id'] == 'old'
    store.close()


def checked_projection(client):
    packet = client.get('/api/p/synthetic/packet/CHILD', headers=READ).json()
    state = client.get('/api/p/synthetic/state', headers=READ).json()
    requirements = client.get('/api/p/synthetic/prerequisites?node=CHILD', headers=READ).json()
    assert packet['basis'] == state['basis'] == requirements['basis']
    assert packet['prerequisites']['start'] == state['node_views']['CHILD']['prerequisites']['start'] == requirements['requirements']
    assert packet['predecessors'] == []  # Historical direct-only field is compatible.
    assert packet['prerequisites']['start'][0]['declared_target_id'] == 'B'
    return packet, state


def test_api_shared_dependencies_late_evidence_conflict_workspace_and_rebuild(api):
    client, store = api
    packet, _ = checked_projection(client)
    assert packet['prerequisites']['start'][0]['state'] == 'unknown'
    store.ingest([event('status-done', 'node.status', {'status': 'done'}, nodes=['A']),
                  event('early-scope', 'scope.set', nodes=['CHILD'])])
    packet, state = checked_projection(client)
    warning = packet['dependency_warnings'][0]
    assert warning['code'] == 'started_without_confirmed_prerequisite'
    assert warning['requirements'][0]['state'] == 'unknown'
    assert state['scopes'][0]['node_ids'] == ['CHILD']
    assert warning['observed_at'] is not None
    receipt = store.ingest([evidence()])['receipts'][0]['seq']
    packet, _ = checked_projection(client)
    assert packet['prerequisites']['start'][0]['state'] == 'satisfied'
    assert packet['dependency_warnings'][0] == warning
    assert warning['basis']['cursor'] < receipt
    assert client.get('/api/p/synthetic/prerequisites?node=CHILD&workspace=another-base', headers=READ).json()['requirements'][0]['state'] == 'unknown'
    store.ingest([evidence('contradiction', availability='missing', source='second-reporter')])
    packet, _ = checked_projection(client)
    assert packet['prerequisites']['start'][0]['state'] == 'conflict'
    before = copy.deepcopy(packet)
    store.rebuild()
    assert client.get('/api/p/synthetic/packet/CHILD', headers=READ).json() == before


def test_items_filter_before_limit_and_explicit_error_only(api):
    client, store = api
    values = [event('rare-old', 'item.upsert', {'item_id': 'rare', 'type': 'agentMessage', 'text': 'mentions error but successful'}, nodes=['CHILD'])]
    values += [event(f'cmd-{i}', 'item.upsert', {'item_id': f'cmd-{i}', 'type': 'commandExecution',
        'text': 'synthetic stdout', 'state': 'failed' if i == 501 else 'completed'}, nodes=['CHILD']) for i in range(502)]
    for start in range(0, len(values), 500):
        store.ingest(values[start:start+500])
    read = lambda **query: client.get('/api/p/synthetic/items', headers=READ, params=query)
    rare = read(node='B', deep=True, categories='message', limit=1).json()
    assert [i['id'] for i in rare['items']] == ['rare']
    assert read(categories='none').json()['items'] == []
    failed = read(only_errors=True).json()['items']
    assert [i['id'] for i in failed] == ['cmd-501']
    assert failed[0]['category'] == 'command' and failed[0]['native_type'] == 'commandExecution'
    assert read(categories='unknown').status_code == 422
    assert read(categories='message', only_errors=True).json()['items'] == []


def test_item_cursor_total_order_scope_binding_and_page_corrections(api):
    client, store = api
    store.ingest([event(f'tie-{i}', 'item.upsert', {'item_id': f'i{i}', 'type': 'agentMessage', 'text': str(i)},
                        agent='actor-a' if i < 2 else 'actor-b', nodes=['B', 'CHILD']) for i in range(4)])
    # Deliberately synthetic equal-seq projection fixture tests the complete key.
    # This is a paging contract check, not a provider-native event claim.
    for row in store.db.execute('SELECT project,agent,id,body FROM items').fetchall():
        item = json.loads(row['body']); item['first_seq'] = 2
        store.db.execute('UPDATE items SET first_seq=2,body=? WHERE project=? AND agent=? AND id=?',
                         (canonical(item), row['project'], row['agent'], row['id']))
        store.db.execute('UPDATE item_facets SET first_seq=2 WHERE project=? AND agent=? AND item=?',
                         (row['project'], row['agent'], row['id']))
    params = {'node': 'B', 'deep': True, 'categories': 'message', 'limit': 1}
    first = client.get('/api/p/synthetic/items', headers=READ, params=params).json()
    assert [i['id'] for i in first['items']] == ['i3']
    token = first['page_cursor']
    ids = ['i3']
    while token:
        page = client.get('/api/p/synthetic/items', headers=READ, params={**params, 'page_cursor': token}).json()
        ids += [i['id'] for i in page['items']]
        token = page['page_cursor']
    assert ids == ['i3', 'i2', 'i1', 'i0']  # Deep association did not duplicate identities.
    for changed in ({'categories': 'command'}, {'node': 'CHILD'}, {'deep': False}, {'agent': 'actor-a'},
                    {'outside': True}, {'only_errors': True}, {'before': 999}):
        response = client.get('/api/p/synthetic/items', headers=READ, params={**params, **changed, 'page_cursor': first['page_cursor']})
        assert response.status_code == 422 and response.json()['error'] == 'cursor_scope_mismatch'
    malformed = client.get('/api/p/synthetic/items', headers=READ, params={**params, 'page_cursor': '%%%bad'})
    assert malformed.status_code == 422
    store.ingest([event('correct-visible', 'item.upsert', {'item_id': 'i3', 'type': 'commandExecution'}, agent='actor-b', nodes=['CHILD'])])
    visible = client.get('/api/p/synthetic/items', headers=READ, params={**params, 'limit': 10}).json()['items']
    assert [i['id'] for i in visible] == ['i0', 'i1', 'i2']
    assert store.events_after('synthetic')['events'][-1]['event_id'] == 'correct-visible'


def test_outside_query_is_bound_to_resolved_plan_membership(api):
    client, store = api
    old_version = store.head('synthetic')
    store.ingest([event('scoped-item', 'item.upsert', {'item_id': 'scoped', 'type': 'agentMessage'}, nodes=['CHILD']),
                  event('unassigned-item', 'item.upsert', {'item_id': 'unassigned', 'type': 'agentMessage', 'historical': True})])
    current = store.plan('synthetic')['plan']
    del current['nodes']['CHILD']
    store.import_plan(current, old_version, 'remove-child')
    current_items = client.get('/api/p/synthetic/items?outside=true', headers=READ).json()['items']
    assert {i['id'] for i in current_items} == {'scoped', 'unassigned'}
    historical = client.get('/api/p/synthetic/items', headers=READ, params={'outside': True, 'version': old_version}).json()['items']
    assert [i['id'] for i in historical] == ['unassigned']


def test_project_summary_deduplicates_active_agents_and_never_loads_transcripts(api, monkeypatch):
    client, store = api
    unknown = client.get('/api/projects?summary=true', headers=READ).json()[0]
    assert unknown['distinct_active_agents'] is None and unknown['source_health']['state'] == 'unknown'
    timestamp = now()
    values = [event('health', 'source.health', {'source_key': 'synthetic', 'state': 'connected'}, at=timestamp)]
    for actor in ('actor', 'child-actor'):
        values += [event(actor+'-meta', 'agent.upsert', {'parent_id': 'actor' if actor != 'actor' else None}, agent=actor, at=timestamp),
                   event(actor+'-active', 'agent.activity', {'state': 'running'}, agent=actor, at=timestamp),
                   event(actor+'-scope', 'scope.set', agent=actor, nodes=['B', 'CHILD'], at=timestamp)]
    store.ingest(values)
    def forbidden(*args, **kwargs):
        raise AssertionError('Catalogue must not fetch transcript windows')
    monkeypatch.setattr(store, 'items', forbidden)
    statements = []
    store.db.set_trace_callback(statements.append)
    summary = client.get('/api/projects?summary=true', headers=READ).json()[0]
    store.db.set_trace_callback(None)
    assert summary['distinct_active_agents'] == 2 and summary['distinct_active_blocks'] == 1
    assert summary['purpose'] == 'Exercise contracts' and summary['last_observed_at']
    assert not any('from items' in s.lower() or 'from item_facets' in s.lower() for s in statements)
    assert 'messages' not in summary and 'items' not in summary
    assert client.get('/api/projects', headers=READ).json()[0].keys() == {'project_id', 'version', 'title'}


def test_new_routes_preserve_auth_origin_and_observer_boundary(api):
    client, _ = api
    for route in ('/api/projects?summary=true', '/api/p/synthetic/prerequisites?node=CHILD', '/api/p/synthetic/algorithms'):
        assert client.get(route).status_code == 401
        assert client.get(route, headers={**READ, 'origin': 'https://unrelated.invalid'}).status_code == 403
    capabilities = client.get('/api/health', headers=READ).json()['capabilities']
    assert {'observability_profile_1', 'effective_dependencies_1', 'typed_items_1', 'project_summary_1', 'algorithm_evidence_1'} <= set(capabilities)
    assert client.post('/api/p/synthetic/events', headers=READ, json={'events': []}).status_code == 401


def test_facet_indexes_and_identity_link_rebuild_are_consistent(api):
    _, store = api
    store.ingest([event('wrong-owner', 'item.upsert', {'item_id': 'native-test', 'type': 'testResult',
        'state': 'failed', 'text': 'synthetic explicit failure'}, agent='old-owner', nodes=['CHILD'])])
    statements = []
    store.db.set_trace_callback(statements.append)
    store.items('synthetic', categories='test')
    store.items('synthetic', only_errors=True)
    store.db.set_trace_callback(None)
    queries = [sql for sql in statements if sql.startswith('SELECT f.agent,')]
    assert len(queries) == 2
    plans = [' '.join(str(row[3]) for row in store.db.execute('EXPLAIN QUERY PLAN ' + sql)) for sql in queries]
    assert 'facet_category' in plans[0] and 'facet_errors' in plans[1]
    store.ingest([event('correct-owner', 'item.identity_corrected', {'item_id': 'native-test',
        'previous_agent_id': 'old-owner', 'basis': 'Synthetic verified identity correction'}, agent='new-owner')])
    assert store.items('synthetic', agent='old-owner', categories='test')['items'] == []
    corrected = store.items('synthetic', outside=True, categories='test', only_errors=True)['items']
    assert len(corrected) == 1 and corrected[0]['agent_id'] == 'new-owner'
    assert store.items('synthetic', node='B', categories='test')['items'] == []
    store.ingest([event('link-correct-owner', 'item.link', {'item_id': 'native-test'}, agent='new-owner', nodes=['CHILD'])])
    before = store.items('synthetic', node='B', categories='test', only_errors=True)['items']
    assert len(before) == 1
    store.rebuild()
    assert store.items('synthetic', node='B', categories='test', only_errors=True)['items'] == before
    assert store.items('synthetic', outside=True, categories='test')['items'] == []
