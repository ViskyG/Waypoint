"""F04 regressions on synthetic reports; not a native Codex connectivity check."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import shutil
import subprocess

import pytest

from waypoint.source_health import aggregate_source_health, source_health, source_is_connected

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def report(age=0, state='connected'):
    return {'source_key': 'synthetic', 'state': state,
            'at': (NOW - timedelta(seconds=age)).isoformat()}


@pytest.mark.parametrize('age,state', [(0, 'connected'), (24.999, 'connected'),
                                      (25, 'stale'), (100000, 'stale')])
def test_health_freshness_boundary_preserves_report(age, state):
    original = report(age)
    result = source_health(original, NOW)
    assert result['state'] == state
    assert result['reported_state'] == original['state'] == 'connected'
    assert result['reported_at'] == result['at'] == original['at']
    assert result['age_seconds'] == age
    assert source_is_connected(original, NOW) == (state == 'connected')
    assert original == report(age)  # Projection never rewrites the receipt.
    assert source_health(result, NOW) == result  # Safe to consume normalized state.


@pytest.mark.parametrize('timestamp', [None, '', 'not-a-time', '2026-10-17',
    '2026-10-17T11:59:59', '2026-10-17T12:00:00.001Z', 42, []])
def test_unusable_or_future_timestamp_never_attests_connectivity(timestamp):
    result = source_health({'state': 'connected', 'at': timestamp}, NOW)
    assert result['state'] == result['freshness'] == 'unknown'
    assert result['age_seconds'] is None
    assert not source_is_connected(result, NOW)


def test_timezone_and_aggregate_uncertainty():
    offset = {'state': 'connected', 'at': '2026-10-17T15:59:59+04:00'}
    assert source_health(offset, NOW)['age_seconds'] == 1
    assert aggregate_source_health([], NOW)['state'] == 'unknown'
    assert aggregate_source_health([report(1, 'disconnected')], NOW)['state'] == 'disconnected'
    assert aggregate_source_health([report(1, 'disconnected'), report(30)], NOW)['state'] == 'stale'
    assert aggregate_source_health([report(1, 'disconnected'), {'state': 'connected'}], NOW)['state'] == 'unknown'
    assert aggregate_source_health([report(1), report(30)], NOW)['state'] == 'connected'
    assert source_health(report(1, 'unrecognized'), NOW)['state'] == 'unknown'


def test_demo_remains_explicitly_fictional_and_never_connected():
    original = {'source_key': 'demo', 'state': 'demo', 'at': '2020-01-01T00:00:00Z'}
    assert source_health(original, NOW)['state'] == 'demo'
    assert not source_is_connected(original, NOW)
    assert aggregate_source_health([original], NOW)['state'] == 'demo'


def test_catalogue_shows_effective_state_and_report_age_without_json():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node unavailable for bounded catalogue rendering check')
    web = Path(__file__).resolve().parents[1] / 'waypoint/web'
    script = web / 'projects.js'
    harness = r"""
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag=tag; this.children=[]; this.dataset={}; this.textContent=''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; }
}
global.window={};
global.document={documentElement:{},createElement:tag=>new Element(tag), createTextNode:text=>({textContent:text,children:[]})};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
window.WaypointUI.setLanguage('ru');
vm.runInThisContext(fs.readFileSync(process.argv[2],'utf8'));
const container=new Element('div');
window.WaypointUI.mountProjectCatalogue(container, [{project_id:'synthetic',source_health:{state:'stale',sources:[
 {source_key:'observer',state:'stale',reported_state:'connected',reported_at:'2020-01-01T00:00:00Z',age_seconds:86400}
]}}], {onOpenProject:()=>{}});
function texts(n) { return [n.textContent, ...n.children.flatMap(texts)]; }
process.stdout.write(JSON.stringify(texts(container)));
"""
    rendered = json.loads(subprocess.run([node, '-e', harness, str(web / 'i18n.js'), str(script)],
        check=True, capture_output=True, text=True).stdout)
    assert 'Источники: данные устарели' in rendered
    assert any('сообщение: подключён, 1 дн назад' in text for text in rendered)
    assert ' · 2020-01-01T00:00:00Z' in rendered
    assert not any('"sources"' in text or '"state"' in text for text in rendered)


def test_api_old_source_is_stale_and_counts_unknown(tmp_path):
    """Production HTTP projections, synthetic DB; run after read-model integration."""
    from fastapi.testclient import TestClient
    from waypoint.server import create_app
    from test_stage2_store_api import TOKENS, READ, WRITE, event, plan_fixture
    from waypoint.domain import now

    app = create_app(tmp_path, tokens=TOKENS, testing=True)
    with TestClient(app) as client:
        assert client.post('/api/p/synthetic/plans', headers=WRITE,
            json={'plan': plan_fixture(), 'request_id': 'health-fixture'}).status_code == 200
        app.state.store.ingest([
            event('old-health', 'source.health', {'source_key': 'synthetic', 'state': 'connected'}, at='2020-01-01T00:00:00Z'),
            event('actor-meta', 'agent.upsert'),
            event('actor-running', 'agent.activity', {'state': 'running'}),
            event('actor-scope', 'scope.set', nodes=['B']),
        ])
        summary = client.get('/api/projects?summary=true', headers=READ).json()[0]
        assert summary['source_health']['state'] == 'stale'
        assert summary['source_health']['sources'][0]['reported_state'] == 'connected'
        assert datetime.fromisoformat(summary['source_health']['sources'][0]['reported_at']) == datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert summary['distinct_active_agents'] is None
        assert summary['distinct_active_blocks'] is None
        state = client.get('/api/p/synthetic/state', headers=READ).json()
        assert state['sources'][0]['state'] == 'stale'
        assert state['node_views']['B']['activity']['distinct_active_agents'] == 0
        # A subsequent genuine fresh health receipt restores the ordinary path.
        app.state.store.ingest([event('fresh-health', 'source.health',
            {'source_key': 'synthetic', 'state': 'connected'}, at=now())])
        summary = client.get('/api/projects?summary=true', headers=READ).json()[0]
        assert summary['source_health']['state'] == 'connected'
        assert summary['distinct_active_agents'] == summary['distinct_active_blocks'] == 1
