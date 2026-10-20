"""Incident grouping preserves evidence identity and raw repeated observations."""
import copy
import json
from waypoint.warning_history import dependency_incidents, dependency_history
from waypoint.store import Store

def warning(seq,receipt='missing-1',workspace='copy-1'):
    return {'seq':seq,'node_id':'N','agent_id':'A','observed_at':'2026-10-20T10:00:00Z','requirements':[{'edge_id':'E','producer_id':'P','requirement_fingerprint':'a'*64,'availability':'missing','receipts':[receipt],'workspace_ref':{'consumer':workspace}}]}

def test_repeats_one_period_but_new_missing_basis_is_new_incident():
    records=[warning(1),warning(2),warning(5,'missing-2'),warning(6,'missing-2'),warning(9,'missing-2','copy-2')]
    original=copy.deepcopy(records)
    groups=dependency_incidents(list(reversed(records)))
    assert [g['receipt_count'] for g in groups]==[1,2,2]
    assert [(g['first_seq'],g['last_seq']) for g in groups]==[(9,9),(5,6),(1,2)]
    assert len({g['incident_id'] for g in groups})==3
    assert records==original
    assert dependency_incidents([])==[]

def test_summary_streams_once_then_reads_only_new_metadata_with_bounded_output(tmp_path):
    store=Store(tmp_path/'db.sqlite')
    try:
        for seq in range(1, 602):
            row=warning(seq, 'basis-'+str(seq//2))
            store.db.execute('INSERT INTO dependency_starts VALUES(?,?,?,?)', ('p',seq,'N',json.dumps(row)))
        queries=[];store.db.set_trace_callback(queries.append)
        result=dependency_history(store,'p','N')
        assert result['dependency_warning_count']==601
        assert result['dependency_incident_count']==301
        assert len(result['dependency_incidents'])==20 and result['dependency_incidents_has_more']
        assert len(result['dependency_warnings'])==20
        assert all('LIMIT 200' in q for q in queries if 'SELECT body FROM dependency_starts' in q)
        queries.clear()
        assert dependency_history(store,'p','N')==result
        assert not any('SELECT body FROM dependency_starts' in q for q in queries)
        # Returned structures cannot mutate the cached provenance.
        result['dependency_incidents'][0]['receipt_count']=999
        row=warning(602,'basis-301');store.db.execute('INSERT INTO dependency_starts VALUES(?,?,?,?)',('p',602,'N',json.dumps(row)))
        queries.clear();updated=dependency_history(store,'p','N')
        assert updated['dependency_incident_count']==302 and updated['dependency_warning_count']==602
        assert updated['dependency_incidents'][0]['receipt_count']==1
        reads=[q for q in queries if 'SELECT body FROM dependency_starts' in q]
        assert len(reads)==1 and 'seq>601' in reads[0]
        store.db.execute("DELETE FROM dependency_starts WHERE project='p'")
        assert dependency_history(store,'p','N')['dependency_warning_count']==0
    finally:
        store.close()
