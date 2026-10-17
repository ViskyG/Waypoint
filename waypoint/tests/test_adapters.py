from __future__ import annotations
import json
import socket
import struct
import threading
import time
from pathlib import Path
import pytest
from waypoint.domain import ContractError
from waypoint.adapters.patches import FrameDecoder, encode_frame, apply_patches, RevisionState
from waypoint.adapters.codex import JsonlTail, Normalizer, discover_family
from waypoint.adapters.ipc import Follower, ALLOWED_REQUESTS


def test_frame_fragmentation_and_size():
    a=encode_frame({"text":"привет"});b=encode_frame({"n":2});d=FrameDecoder()
    assert not d.feed(a[:2]);assert not d.feed(a[2:7])
    assert d.feed(a[7:]+b)==[{"text":"привет"},{"n":2}]
    with pytest.raises(ContractError):FrameDecoder(8).feed(struct.pack('<I',9))


def test_patch_atomicity_and_revision_gap():
    initial={"a":[{"text":"old"}],"b":1}
    patched=apply_patches(initial,[{"op":"replace","path":["a",0,"text"],"value":"new"},{"op":"add","path":["a",1],"value":{"text":"another"}}])
    assert initial["a"][0]["text"]=="old" and patched["a"][0]["text"]=="new"
    with pytest.raises(ContractError):apply_patches(initial,[{"op":"replace","path":["b"],"value":2},{"op":"remove","path":["a",9]}])
    assert initial["b"]==1
    r=RevisionState();r.accept({"type":"snapshot","revision":2,"conversationState":initial})
    with pytest.raises(ContractError):r.accept({"type":"patches","baseRevision":1,"revision":3,"patches":[]})
    assert r.state["b"]==1


def test_shared_session_is_not_agent_identity():
    n=Normalizer('p','file','g')
    a=n.metadata({"id":"one","session_id":"same"});b=n.metadata({"id":"two","parent_thread_id":"one","session_id":"same"})
    assert a["agent_id"]!=b["agent_id"]
    assert b["payload"]["parent_id"]==a["agent_id"]
    with pytest.raises(ContractError):n.metadata({"session_id":"same"})


def test_snapshot_filters_settings_and_encrypted_reasoning():
    n=Normalizer('p','ipc','g')
    state={"id":"one","threadRuntimeStatus":{"type":"active"},"latestThreadSettings":{"developerInstructions":"DO NOT COLLECT"},"turns":[{"items":[{"id":"m","type":"agentMessage","text":"<script>bad()</script>"},{"id":"r","type":"reasoning","encrypted_content":"hidden"}]}]}
    events=n.snapshot(state,'one',True)
    items=[e for e in events if e['kind']=='item.upsert']
    assert len(items)==1 and items[0]['payload']['text']=='<script>bad()</script>'
    assert 'DO NOT COLLECT' not in json.dumps(events) and 'hidden' not in json.dumps(events)
    assert not [e for e in n.snapshot(state,'one') if e['kind']=='item.upsert']


def test_partial_tail_and_rotation(tmp_path):
    p=tmp_path/'a.jsonl';p.write_text('{"type":"x"}\n{"type":')
    tail=JsonlTail(p);rows,cursor=tail.read();assert len(rows)==1
    with p.open('a') as f:f.write('"y"}\n')
    resumed=JsonlTail(p,cursor);rows,cursor2=resumed.read();assert rows[0][1]['type']=='y'
    p.write_text('{"type":"z"}\n')
    fresh=JsonlTail(p,cursor2);rows,cursor3=fresh.read();assert rows[0][1]['type']=='z'
    assert fresh.issue=='source_generation_changed' and cursor3['generation']!=cursor2['generation']


def test_bad_line_keeps_entire_uncommitted_cursor(tmp_path):
    p=tmp_path/'bad.jsonl';p.write_text('{"ok":1}\nbad\n')
    tail=JsonlTail(p)
    with pytest.raises(ContractError):tail.read()
    assert tail.offset==0


def test_genealogy_discovery_only_selected_family(tmp_path):
    for ident,parent in [('r',None),('c','r'),('g','c'),('other',None)]:
        (tmp_path/f'{ident}.jsonl').write_text(json.dumps({'type':'session_meta','payload':{'id':ident,'parent_thread_id':parent,'session_id':'shared'}})+'\n')
    assert set(discover_family(tmp_path,'r'))=={'r','c','g'}


def test_synthetic_unix_peer_observation_only(tmp_path):
    path=tmp_path/'ipc.sock';server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(path));server.listen(1)
    sent=[];errors=[]
    def peer():
        try:
            conn,_=server.accept();conn.settimeout(4);decoder=FrameDecoder()
            with conn:
                while True:
                    data=conn.recv(65536)
                    if not data:break
                    for msg in decoder.feed(data):
                        sent.append(msg)
                        if msg.get('type')=='request':
                            method=msg['method'];response={'type':'response','requestId':msg['requestId'],'resultType':'success','result':{}}
                            if method=='initialize':response['result']={'clientId':'observer'}
                            if method=='thread-owner-discovery':response['handledByClientId']='owner'
                            conn.sendall(encode_frame(response))
                            if method=='thread-follower-load-complete-history':
                                params={'conversationId':'r','hostId':'local','change':{'type':'snapshot','revision':1,'conversationState':{'id':'r','turns':[]}}}
                                conn.sendall(encode_frame({'type':'broadcast','method':'thread-stream-state-changed','params':params}))
                                params={**params,'change':{'type':'patches','baseRevision':1,'revision':2,'patches':[{'op':'add','path':['value'],'value':42}]}}
                                conn.sendall(encode_frame({'type':'broadcast','method':'thread-stream-state-changed','params':params}))
                        elif msg.get('method')=='thread-stream-following-changed' and not msg['params']['following']:
                            return
        except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=peer);thread.start();states=[];health=[]
    follower=Follower(path,lambda t,s,h:states.append((t,s,h)),lambda s,d:health.append(s))
    try:
        follower.connect();follower.follow('r')
        deadline=time.monotonic()+3
        while len(states)<2 and time.monotonic()<deadline:follower.pump(.05)
        assert states[-1][1]['value']==42 and states[0][2] is True
        with pytest.raises(ContractError):follower._rpc('turn/start',{})
    finally:follower.close();thread.join(5);server.close()
    assert not errors
    assert all(m['method'] in ALLOWED_REQUESTS for m in sent if m['type']=='request')
    assert sent[-1]['params']['following'] is False


def test_unacknowledged_tail_batch_keeps_stable_ids(tmp_path):
    p=tmp_path/'log.jsonl';p.write_text('{"timestamp":"2026-10-16T00:00:00Z","type":"session_meta","payload":{"id":"root"}}\n')
    a=JsonlTail(p);b=JsonlTail(p);ra,ca=a.read();rb,cb=b.read()
    assert ra[0][0]==rb[0][0]
    na=Normalizer('p','file',a.generation);nb=Normalizer('p','file',b.generation)
    assert na.rollout(ra[0][1],None,ra[0][0])[1]==nb.rollout(rb[0][1],None,rb[0][0])[1]


@pytest.mark.parametrize('change',[None,[],"not-an-object"])
def test_malformed_change_is_an_explicit_protocol_error(change):
    with pytest.raises(ContractError):RevisionState().accept(change)


def test_malformed_patch_does_not_half_mutate():
    state={'a':1}
    with pytest.raises(ContractError):apply_patches(state,[{'op':'replace','path':['a'],'value':2},'wrong'])
    assert state=={'a':1}
