"""Exact visible-window reconciliation, independent of discovery pagination."""
import pytest
from waypoint.domain import ContractError
from waypoint.store import Store
from test_core import graph,event


def test_resolve_exact_keys_filters_membership_and_machine_facets(tmp_path):
    store=Store(tmp_path/'db.sqlite');store.import_plan(graph(),None,'initial')
    try:
        for i in range(40):
            store.ingest([event('item-'+str(i),'item.upsert',{'item_id':str(i),'type':'agentMessage','text':'old'},nodes=['W1'])])
        # New history crowds out old rows from the ordinary tail.
        for i in range(90):
            store.ingest([event('later-'+str(i),'item.upsert',{'item_id':'new-'+str(i),'type':'agentMessage','text':'new'},nodes=['W1'])])
        assert '5' not in {x['id'] for x in store.items('p',node='W1',limit=40)['items']}
        keys=[['codex/one','5'],['codex/one','6'],['codex/one','7']]
        assert {x['id'] for x in store.items('p',node='W1',categories=['message'],identities=keys)['items']}=={'5','6','7'}
        store.ingest([event('correct','item.upsert',{'item_id':'5','type':'commandExecution','text':'corrected','state':'failed'},nodes=['W1'])])
        store.ingest([event('move','item.link',{'item_id':'6'},nodes=['W2'])])
        assert [x['id'] for x in store.items('p',node='W1',deep=False,categories=['message'],identities=keys)['items']]==['7']
        assert [x['id'] for x in store.items('p',node='W1',deep=False,categories=['command'],only_errors=True,identities=keys)['items']]==['5']
        assert store.items('p',node='W1',identities=[])['items']==[]
        assert store.items('p',agent='other',identities=keys)['items']==[]
        with pytest.raises(ContractError):store.items('p',identities=keys,page_cursor='wrong')
    finally:store.close()
