"""F02/F03 synthetic HTTP/Store regressions; not native Codex evidence."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from waypoint.dependencies import effective_requirements
from waypoint.server import create_app
from test_stage2_store_api import READ, WRITE, TOKENS, event, plan_fixture


def order_plan(phase='start', scope='subtree'):
    plan = plan_fixture()
    spec = plan['edges']['NEEDS']['x_observability']
    spec.update(relation='order', phase=phase, target_scope=scope, why='Ordering context only')
    del spec['condition']
    return plan


def client_with_plan(tmp_path, plan):
    app = create_app(tmp_path, tokens=TOKENS, testing=True)
    client = TestClient(app)
    response = client.post('/api/p/synthetic/plans', headers=WRITE,
                           json={'plan': plan, 'request_id': 'conformance-initial'})
    assert response.status_code == 200, response.text
    return client, app.state.store


@pytest.mark.parametrize('phase', ['start', 'finish'])
def test_order_shared_http_projections_keep_context_without_readiness(tmp_path, phase):
    plan = order_plan(phase)
    client, store = client_with_plan(tmp_path, plan)
    with client:
        state = client.get('/api/p/synthetic/state', headers=READ).json()
        packet = client.get('/api/p/synthetic/packet/CHILD', headers=READ).json()
        api = client.get('/api/p/synthetic/prerequisites', headers=READ,
                         params={'node': 'CHILD', 'phase': phase}).json()
        records = state['node_views']['CHILD']['prerequisites'][phase]
        assert records == packet['prerequisites'][phase] == api['requirements']
        assert len(records) == 1
        record = records[0]
        assert (record['producer_id'], record['declared_target_id'], record['consumer_id']) == ('A', 'B', 'CHILD')
        assert record['inherited'] is True
        assert record['classification'] == 'order'
        assert record['state'] == record['availability'] == 'not_required'
        assert record['phase'] == phase and record['target_scope'] == 'subtree'
        assert record['why'] == 'Ordering context only'
        assert record['receipts'] == [] and record['requirement_fingerprint'] is None
        assert effective_requirements(plan, 'CHILD', phase) == []
        other = 'finish' if phase == 'start' else 'start'
        assert packet['prerequisites'][other] == []
        store.ingest([event('started-order-only', 'scope.set', nodes=['CHILD'])])
        assert store.db.execute('SELECT COUNT(*) FROM dependency_starts').fetchone()[0] == 0


def test_order_node_scope_is_not_inherited_and_mixed_requires_still_warns(tmp_path):
    plan = plan_fixture()
    plan['edges']['ORDER'] = copy.deepcopy(order_plan(scope='node')['edges']['NEEDS'])
    client, store = client_with_plan(tmp_path, plan)
    with client:
        parent = client.get('/api/p/synthetic/packet/B', headers=READ).json()
        child = client.get('/api/p/synthetic/packet/CHILD', headers=READ).json()
        assert {r['classification'] for r in parent['prerequisites']['start']} == {'requires', 'order'}
        assert {r['classification'] for r in child['prerequisites']['start']} == {'requires'}
        store.ingest([event('started-mixed', 'scope.set', nodes=['B'])])
        warning = client.get('/api/p/synthetic/packet/B', headers=READ).json()['dependency_warnings'][0]
        assert [r['edge_id'] for r in warning['requirements']] == ['NEEDS']


def test_explicit_workspace_override_basis_matches_effective_evaluation(tmp_path):
    plan = plan_fixture()
    plan['x_observability']['project_workspace_ref'] = 'shared-project'
    client, store = client_with_plan(tmp_path, plan)
    with client:
        requirement = effective_requirements(plan, 'CHILD')[0]
        store.ingest([event('override-proof', 'dependency.observation', {
            'edge_id': 'NEEDS', 'consumer_id': 'CHILD',
            'requirement_fingerprint': requirement['requirement_fingerprint'],
            'workspace_ref': 'override-base', 'availability': 'available',
            'occurred_at': '2026-10-17T10:00:00Z',
            'basis': {'kind': 'artifact', 'ref': 'synthetic-override-proof',
                      'explanation': 'Synthetic evidence of override-specific output'}}, nodes=['CHILD'])])
        default = client.get('/api/p/synthetic/prerequisites', headers=READ, params={'node': 'CHILD'}).json()
        override = client.get('/api/p/synthetic/prerequisites', headers=READ,
                              params={'node': 'CHILD', 'workspace': 'override-base'}).json()
        assert default['requirements'][0]['state'] == 'unknown'
        assert override['requirements'][0]['state'] == 'satisfied'
        refs = {'consumer': 'override-base', 'project': 'shared-project'}
        assert override['basis']['workspace_ref'] == override['requirements'][0]['workspace_ref'] == refs
        assert default['basis']['workspace_ref']['consumer'] == 'workspace1'


def test_node_local_workspace_basis_agrees_across_state_packet_and_api(tmp_path):
    plan = plan_fixture()
    plan['nodes']['CHILD']['x_observability']['workspace_ref'] = 'child-workspace'
    client, store = client_with_plan(tmp_path, plan)
    with client:
        state = client.get('/api/p/synthetic/state', headers=READ).json()
        packet = client.get('/api/p/synthetic/packet/CHILD', headers=READ).json()
        api = client.get('/api/p/synthetic/prerequisites', headers=READ, params={'node': 'CHILD'}).json()
        view = state['node_views']['CHILD']
        assert view['basis'] == packet['basis'] == api['basis']
        assert view['basis']['workspace_ref']['consumer'] == 'child-workspace'
        assert state['basis']['workspace_ref']['consumer'] == 'workspace1'
        assert view['prerequisites']['start'] == packet['prerequisites']['start'] == api['requirements']
        assert api['requirements'][0]['workspace_ref'] == view['basis']['workspace_ref']
        before = store.events_after('synthetic')['events']
        store.rebuild()
        assert store.events_after('synthetic')['events'] == before
        assert client.get('/api/p/synthetic/packet/CHILD', headers=READ).json() == packet


def test_authoring_packet_keeps_order_but_frontier_does_not_wait_for_it(tmp_path):
    spec = importlib.util.spec_from_file_location('conformance_roadmap', Path(__file__).resolve().parents[2] / 'roadmap/tools/roadmap.py')
    roadmap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(roadmap)
    client, store = client_with_plan(tmp_path, order_plan())
    with client:
        plan = store.plan('synthetic')['plan']
        plan['nodes']['CHILD']['x_roadmap'] = {'kind': 'packet'}
        text = roadmap.packet_text(plan, 'CHILD')
        assert 'Ordering context only' in text
        assert 'порядок (не условие готовности)' in text
        assert 'A → B; унаследовано через B; phase=start; scope=subtree' in text
        assert roadmap.frontier(plan)['ready'] == ['CHILD']
        assert roadmap.frontier(plan)['waiting'] == []


def test_resolve_items_rejects_bad_keys_and_keeps_scope_and_filter(tmp_path):
    client, store = client_with_plan(tmp_path, plan_fixture())
    with client:
        store.ingest([
            event('inside', 'item.upsert', {'item_id': 'inside', 'type': 'agentMessage', 'text': 'inside'}, nodes=['CHILD']),
            event('outside', 'item.upsert', {'item_id': 'outside', 'type': 'agentMessage', 'text': 'outside'}, nodes=['A']),
        ])
        path = '/api/p/synthetic/items/resolve'
        for keys in ['{', 'null', '{}', '[1]', '[[]]', json.dumps([['actor', 'inside']] * 33)]:
            assert client.get(path, headers=READ, params={'keys': keys}).status_code == 422
        keys = json.dumps([['actor', 'inside'], ['actor', 'outside']])
        response = client.get(path, headers=READ, params={'keys': keys, 'node': 'CHILD', 'categories': 'message'})
        assert response.status_code == 200
        assert [item['id'] for item in response.json()['items']] == ['inside']
        assert client.get(path, headers=READ, params={'keys': keys, 'node': 'CHILD', 'categories': 'command'}).json()['items'] == []
        assert client.get(path, headers=READ, params={'keys': '[]'}).json()['items'] == []
        assert client.get(path, params={'keys': keys}).status_code == 401
