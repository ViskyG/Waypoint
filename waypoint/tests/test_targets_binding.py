"""C05 contracts: SQLite migration/query/rollback and local caller identity."""
import copy
import json
import pytest
from waypoint.store import Store
from waypoint.domain import ContractError
from waypoint.cli import main, parser
from test_core import event, graph


def test_schema_one_migration_link_reopen_rebuild(tmp_path):
    path = tmp_path / 'old.db'
    s = Store(path); s.import_plan(graph(), None, 'initial')
    s.ingest([event('old', 'item.upsert', {'item_id':'i','text':'old'}, nodes=['W1'], edge_ids=['E1'])])
    s.db.execute('DROP TABLE item_targets'); s.db.execute("UPDATE meta SET value='1'")
    s.close(); s = Store(path)
    assert s.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0] == '2'
    assert len(s.items('p', node='W1', edge='E1')['items']) == 1
    s.ingest([event('link','item.link',{'item_id':'i'},nodes=['W2'])])
    assert s.items('p',node='W1',deep=False)['items'] == []
    expected = s.items('p',node='W2')['items']
    s.close(); s = Store(path)
    assert s.items('p',node='W2')['items'] == expected
    s.rebuild()
    assert s.items('p',node='W2')['items'] == expected
    query = "EXPLAIN QUERY PLAN SELECT agent,item,first_seq FROM item_targets WHERE project='p' AND target_kind='node' AND target_id='W2' ORDER BY first_seq DESC LIMIT 10"
    assert any('target_lookup' in str(tuple(row)) for row in s.db.execute(query))
    s.close()


def test_index_changes_rollback_with_ledger(tmp_path):
    s=Store(tmp_path/'db');s.import_plan(graph(),None,'initial')
    e=event('one','item.upsert',{'item_id':'i','text':'before'},nodes=['W1'])
    s.ingest([e],{'source_key':'source','offset':1})
    bad=copy.deepcopy(e);bad['payload']['text']='changed'
    with pytest.raises(ContractError):
        s.ingest([event('move','item.link',{'item_id':'i'},nodes=['W2']),bad],{'source_key':'source','offset':2})
    assert len(s.items('p',node='W1',deep=False)['items'])==1
    assert not s.items('p',node='W2')['items']
    assert s.cursor('source')['offset']==1
    s.close()


def test_chunked_descendants_many_targets_and_stable_page(tmp_path):
    s=Store(tmp_path/'db');g=graph()
    for i in range(1100):g['nodes']['N'+str(i)]={'title':str(i),'parent':'W1'}
    s.import_plan(g,None,'initial')
    s.ingest([event(str(i),'item.upsert',{'item_id':str(i),'text':'payload'},nodes=['N'+str(i), 'W2'],edge_ids=['E1']) for i in range(40)])
    a=s.items('p',node='W1',edge='E1',limit=13)
    b=s.items('p',node='W1',edge='E1',limit=13,before=a['before'])
    assert len(a['items'])==len(b['items'])==13 and a['has_more']
    assert len({x['id'] for x in a['items']+b['items']})==26
    assert [int(x['id']) for x in a['items']]==list(range(27,40))
    assert isinstance(a['cursor'],int)
    s.close()


def test_native_focus_watermark_and_straddling_item(tmp_path):
    s=Store(tmp_path/'db');s.import_plan(graph(),None,'initial')
    boundary={'source_key':'ipc:p:one','generation':'g','revision':10}
    s.ingest([event('f',payload={'source_boundary':boundary},nodes=['W1','W2'],edge_ids=['E1'])])
    def item(i,first,gen='g'):
        return event(i,'item.upsert',{'item_id':i,'text':'text','source_key':'ipc:p:one','source_generation':gen,'source_first_revision':first,'source_revision':20})
    s.ingest([item('straddle',9),item('new',11),item('restart',21,'new-generation')])
    values={x['id']:x for x in s.items('p')['items']}
    assert values['new']['node_ids']==['W1','W2'] and values['new']['edge_ids']==['E1']
    assert values['straddle']['attribution']==values['restart']['attribution']=='unassigned'
    s.ingest([event('focus2',nodes=['W2']), event('rev','item.upsert',item('new',11)['payload'])])
    assert next(x for x in s.items('p')['items'] if x['id']=='new')['node_ids']==['W1','W2']
    s.rebuild()
    assert next(x for x in s.items('p')['items'] if x['id']=='straddle')['attribution']=='unassigned'
    s.close()


def test_binding_rejects_inherited_parent_and_ignores_wp_agent(tmp_path,monkeypatch,capsys):
    meta=tmp_path/'rollout.jsonl';meta.write_text(json.dumps({'type':'session_meta','payload':{'id':'child','session_id':'shared'}})+'\n')
    binding=tmp_path/'binding.json'
    monkeypatch.setenv('CODEX_THREAD_ID','child');monkeypatch.setenv('WP_AGENT','codex/parent')
    assert parser().parse_args(['focus','W1']).agent is None
    assert main(['--project','p','bind','--rollout',str(meta),'--output',str(binding)])==0
    assert json.loads(binding.read_text())['agent_id']=='codex/child'
    monkeypatch.setenv('CODEX_THREAD_ID','parent')
    assert main(['--project','p','--binding',str(binding),'focus','W1'])==2
    assert 'binding_identity' in capsys.readouterr().err


def test_historical_child_activity_cannot_regress_newer_ipc(tmp_path):
    s=Store(tmp_path/'db');s.import_plan(graph(),None,'initial')
    s.ingest([event('active','agent.activity',{'state':'running','reported_by':'threadRuntimeStatus'},at='2026-10-17T10:00:00Z',source='codex-ipc')])
    s.ingest([event('past','agent.activity',{'state':'idle','historical':True,'reported_by':'event_msg.task_complete'},at='2026-10-17T09:00:00Z',source='codex-rollout')])
    actor=s.state('p')['agents'][0]
    assert actor['activity']=='running' and not actor['activity_historical']
    s.ingest([event('child-start','agent.activity',{'state':'running','historical':True,'reported_by':'event_msg.task_started'},agent='codex/child',source='codex-rollout')])
    child=next(a for a in s.state('p')['agents'] if a['id']=='codex/child')
    assert child['activity']=='running' and child['activity_historical']
    s.rebuild()
    assert next(a for a in s.state('p')['agents'] if a['id']=='codex/one')['activity']=='running'
    s.close()


def test_explicit_native_identity_correction_preserves_ledger_and_rebuild(tmp_path):
    s=Store(tmp_path/'db');s.import_plan(graph(),None,'initial')
    s.ingest([event('wrong','item.upsert',{'item_id':'native','text':'original','state':'completed'},nodes=['W1'],source='codex-rollout/source')])
    before=s.items('p')['items'][0]['first_seq']
    s.ingest([event('right','item.upsert',{'item_id':'native','text':'original','state':'completed'},agent='codex/child',source='codex-rollout/source')])
    correction=event('correct','item.identity_corrected',{'item_id':'native','previous_agent_id':'codex/one','basis':'Verified child thread_settings_applied.thread_id boundary'},agent='codex/child')
    s.ingest([correction]);s.ingest([correction])
    items=s.items('p')['items']
    assert len(items)==1 and items[0]['agent_id']=='codex/child'
    assert items[0]['first_seq']==before and items[0]['node_ids']==[]
    assert items[0]['identity_corrections'][0]['node_ids']==['W1']
    assert any(e['event_id']=='wrong' and e['agent_id']=='codex/one' for e in s.events_after('p')['events'])
    s.rebuild()
    assert s.items('p')['items']==items
    assert not s.items('p',node='W1')['items']
    s.close()


def test_identity_correction_conflict_rolls_back(tmp_path):
    s=Store(tmp_path/'db');s.import_plan(graph(),None,'initial')
    s.ingest([event('actual','item.upsert',{'item_id':'native','text':'original'},nodes=['W1'],source='codex-ipc/source')])
    with pytest.raises(ContractError,match='Direct native IPC'):
        s.ingest([event('move','item.identity_corrected',{'item_id':'native','previous_agent_id':'codex/one','basis':'Unreconciled source'},agent='codex/child')])
    assert len(s.items('p',node='W1')['items'])==1
    assert all(e['event_id']!='move' for e in s.events_after('p')['events'])
    s.close()
