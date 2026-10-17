from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from waypoint.domain import ContractError, validate_plan, validate_event, three_way
from waypoint.store import Store
from waypoint.server import create_app
from waypoint.demo import fixture, seed
from waypoint.spool import queue, drain
from waypoint.cli import main


def graph():
    return {"schema": "waypoint.plan/1", "project_id": "p", "title": "Test", "nodes": {"W1": {"title": "Root", "assignment": "do", "tests": {"T1": {"label": "case"}}}, "W2": {"title": "Child", "parent": "W1"}}, "edges": {"E1": {"from": "W1", "to": "W2"}}}


def event(i, kind="scope.set", payload=None, agent="codex/one", nodes=None, **extra):
    return {"event_id": str(i), "project_id": "p", "source": "test", "agent_id": agent, "kind": kind, "at": "2026-10-16T12:00:00Z", "node_ids": nodes or [], "payload": payload or {}, **extra}


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.import_plan(graph(), None, "initial")
    yield s
    s.close()


def test_plan_preserves_many_predecessors_and_non_gate_cycle():
    g = graph(); g["edges"]["E2"] = {"from": "W2", "to": "W1"}
    result, warnings = validate_plan(g)
    assert warnings[0]["code"] == "dependency_cycle"
    assert result["nodes"]["W1"]["parent"] is None


@pytest.mark.parametrize("changes,code", [({"W1": {"parent": "W2"}}, "parent_cycle"), ({"W2": {"parent": "missing"}}, "missing_parent")])
def test_nesting_invalid_is_storage_error(changes,code):
    g=graph()
    for k,v in changes.items():g["nodes"][k].update(v)
    with pytest.raises(ContractError) as err:validate_plan(g)
    assert err.value.code==code


def test_merge_disjoint_and_conflicting(store):
    base=store.head("p"); a=graph();b=graph()
    a["nodes"]["W1"]["title"]="A"
    b["nodes"]["W2"]["title"]="B"
    r=store.import_plan(a,base,"edit-a")
    merged=store.import_plan(b,base,"edit-b",True)
    assert store.plan("p")["plan"]["nodes"]["W1"]["title"]=="A"
    assert store.plan("p")["plan"]["nodes"]["W2"]["title"]=="B"
    b["nodes"]["W1"]["title"]="competing"
    with pytest.raises(ContractError,match="Competing"):store.import_plan(b,base,"edit-c",True)
    assert store.head("p")==merged["version"]


def test_delete_vs_new_reference_conflict(store):
    base=store.head("p");a=graph();del a["nodes"]["W2"];a["edges"]={}
    store.import_plan(a,base,"delete")
    b=graph();b["nodes"]["W3"]={"title":"new","parent":"W2"}
    with pytest.raises(ContractError) as error:store.import_plan(b,base,"add-ref",True)
    assert error.value.code=="merge_reference_conflict"


def test_plan_request_receipt_and_unknown_status(store):
    original=graph(); reply=store.import_plan(original,None,"initial")
    assert reply["ordinal"]==1
    changed=graph();changed["title"]="new"
    with pytest.raises(ContractError):store.import_plan(changed,None,"initial")
    store.ingest([event("a","node.status",{"status":"Занимаюсь неизвестным случаем"},nodes=["OFF-MAP"])])
    assert store.state("p")["node_states"][0]["id"]=="OFF-MAP"


def test_transaction_cursor_and_replay(store):
    e=event("a",nodes=["W1"]);cursor={"source_key":"s","offset":40}
    first=store.ingest([e],cursor)
    again=store.ingest([e],cursor)
    assert first["receipts"][0]["created"] and not again["receipts"][0]["created"]
    bad=event("a",nodes=["W2"])
    with pytest.raises(ContractError):store.ingest([event("b"),bad],{"source_key":"s","offset":100})
    assert store.cursor("s")["offset"]==40
    assert all(e["event_id"]!="b" for e in store.events_after("p")["events"])


def test_done_does_not_erase_failed_tests(store):
    store.ingest([event("s","node.status",{"status":"done"},nodes=["W1"]),event("t","test.result",{"test_id":"T1","run_id":"run","outcome":"failed"},nodes=["W1"])])
    s=store.state("p")
    assert s["node_states"][0]["status"]=="done" and s["checks"][0]["outcome"]=="failed"


def test_parent_completion_does_not_complete_child(store):
    store.ingest([event("a","agent.upsert",{"name":"root"}),event("b","agent.upsert",{"parent_id":"codex/one","session_id":"shared"},agent="codex/two"),event("c","agent.activity",{"state":"running"},agent="codex/two"),event("d","agent.activity",{"state":"completed"})])
    actors={a["id"]:a for a in store.state("p")["agents"]}
    assert actors["codex/two"]["activity"]=="running"


def test_focus_historical_and_multinode(store):
    store.ingest([event("f",nodes=["W1","W2"]), event("live","item.upsert",{"item_id":"i","text":"live"}), event("hist","item.upsert",{"item_id":"h","text":"history","historical":True}),event("early","item.upsert",{"item_id":"e","text":"earlier"},at="2026-10-16T13:00:00+02:00")])
    items={i["id"]:i for i in store.items("p")["items"]}
    assert items["i"]["node_ids"]==["W1","W2"]
    assert items["h"]["attribution"]==items["e"]["attribution"]=="unassigned"
    store.ingest([event("link","item.link",{"item_id":"h"},nodes=["W2"])])
    assert any(i["id"]=="h" for i in store.items("p",node="W1",deep=True)["items"])


def test_history_never_regresses_live_completed_item(store):
    store.ingest([event("a","item.upsert",{"item_id":"i","text":"finished","state":"completed"}),event("b","item.upsert",{"item_id":"i","text":"old","state":"running","historical":True},source="old-file")])
    i=store.items("p")["items"][0]
    assert i["text"]=="finished" and i["state"]=="completed"
    assert i["observed_sources"]==["test","old-file"]


def test_retired_node_ghost(store):
    store.ingest([event("f",nodes=["W2"])])
    g=graph();del g["nodes"]["W2"];g["edges"]={}
    store.import_plan(g,store.head("p"),"retire")
    assert store.state("p")["ghosts"]["W2"]["retired"]


def test_timestamp_required_and_timezone_normalized():
    e=event("x");del e["at"]
    with pytest.raises(ContractError):validate_event(e)
    assert validate_event(event("x",at="2026-10-16T13:00:00+01:00"))["at"].startswith("2026-10-16T12:00:00")


def test_item_pagination_is_stable(store):
    store.ingest([event(str(i),"item.upsert",{"item_id":f"i{i}","text":str(i)},nodes=["W1"]) for i in range(15)])
    a=store.items("p",node="W1",limit=5);b=store.items("p",node="W1",limit=5,before=a["before"])
    assert a["has_more"] and b["has_more"]
    assert not set(i["id"] for i in a["items"])&set(i["id"] for i in b["items"])


def test_spool_replay_and_rejection(tmp_path,store):
    receipt=queue(tmp_path,[event("queued",nodes=["W1"])])
    assert len(receipt)==32
    assert drain(tmp_path,store)=={"accepted":1,"rejected":0}
    assert drain(tmp_path,store)["accepted"]==0
    (tmp_path/"outbox"/"invalid.json").write_text('{"events":[{}]}')
    assert drain(tmp_path,store)["rejected"]==1


def test_api_read_write_capabilities_and_origin(tmp_path):
    tokens={"read":"read-"+"a"*40,"write":"write-"+"b"*40}
    app=create_app(tmp_path,tokens=tokens,testing=True)
    with TestClient(app) as c:
        assert c.get("/api/projects").status_code==401
        read={"Authorization":"Bearer "+tokens["read"]};write={"Authorization":"Bearer "+tokens["write"]}
        assert c.post("/api/p/p/plans",headers=read,json={}).status_code==401
        r=c.post("/api/p/p/plans",headers=write,json={"plan":graph(),"request_id":"x"})
        assert r.status_code==200,r.text
        assert c.get("/api/p/p/state",headers=read).json()["plan"]["title"]=="Test"
        assert c.get("/api/projects",headers={**read,"Origin":"https://evil.invalid"}).status_code==403
        assert c.get("/api/projects",headers={**read,"Host":"evil.invalid"}).status_code==403
        assert c.post("/api/p/p/events",headers=write,json={"events":[event("a",nodes=["X"])]}).status_code==200
        assert c.post("/api/p/p/plans",headers=write,json={"plan":graph(),"request_id":""}).status_code==422
        assert c.get("/").status_code==200
        assert c.get("/static/app.js").status_code==200
        assert "frame-ancestors 'none'" in c.get("/").headers["content-security-policy"]
        assert c.post("/api/p/p/start-agent",headers=write,json={}).status_code==404


def test_demo_is_idempotent_and_not_live(store):
    seed(store);before=len(store.events_after("demo",limit=500)["events"]);seed(store)
    assert len(store.events_after("demo",limit=500)["events"])==before
    assert len(store.state("demo")["agents"])==9
    assert store.state("demo")["sources"][0]["state"]=="demo"


def test_cli_missing_agent_does_not_emit(tmp_path,capsys):
    assert main(["--data",str(tmp_path),"--project","p","focus","W1"])==2
    assert 'agent_required' in capsys.readouterr().err
    assert not (tmp_path/"outbox").exists()


def test_delayed_outbox_focus_does_not_regress_scope(store):
    store.ingest([event('new',nodes=['W2'],at='2026-10-16T12:30:00Z')])
    store.ingest([event('old',nodes=['W1'],at='2026-10-16T12:00:00Z')])
    assert store.state('p')['scopes'][0]['node_ids']==['W2']


def test_projection_rebuild_retains_old_plan_context(store):
    original=store.head('p')
    store.ingest([event('f',nodes=['W1']),event('m','item.upsert',{'item_id':'old','text':'before plan change'}),event('r','node.result',{'summary':'old result'},nodes=['W1'])])
    g=graph();g['nodes']['W1']['acceptance']={'A-new':{'text':'new rule'}}
    store.import_plan(g,original,'new-plan')
    before=store.state('p')
    report=store.rebuild()
    after=store.state('p')
    assert report['replayed']>=5
    for key in ('items','scopes','node_states','agents','checks','cursor'):
        assert before[key]==after[key],key
    assert after['items'][0]['plan_version']==original


def test_backup_and_real_sqlite_reopen(store,tmp_path):
    store.ingest([event('backup',nodes=['W1'])],{'source_key':'file','offset':50})
    copy=tmp_path/'backup.db';store.backup(copy)
    other=Store(copy)
    try:
        assert other.cursor('file')['offset']==50
        assert other.state('p')['scopes'][0]['node_ids']==['W1']
    finally:other.close()
