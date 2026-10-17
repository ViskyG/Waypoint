#!/usr/bin/env python3
"""Disposable real HTTP/service/outbox/restart test, with no browser/Codex access."""
import json, os, signal, socket, subprocess, sys, tempfile, threading, time, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from waypoint.domain import now


def run():
    results=[]
    with tempfile.TemporaryDirectory(prefix='waypoint-http-') as directory:
        data=Path(directory); log=(data/'service.log').open('w')
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        url=f'http://127.0.0.1:{port}'
        command=[sys.executable,'-m','waypoint','--data',str(data),'serve','--demo','--port',str(port)]
        def start():
            p=subprocess.Popen(command,cwd=root,stdout=log,stderr=log)
            for _ in range(100):
                try:
                    if (data/'access.json').exists():
                        tokens=json.loads((data/'access.json').read_text())
                        req=Request(url+'/api/health',headers={'Authorization':'Bearer '+tokens['read']})
                        with urlopen(req,timeout=.3) as r:
                            if r.status==200:return p,tokens
                except (OSError,ValueError):pass
                if p.poll() is not None:raise RuntimeError('Test service exited; inspect private test log')
                time.sleep(.05)
            p.terminate();raise TimeoutError('Test service startup')
        process,tokens=start()
        def call(path,body=None,key='read'):
            req=Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+tokens[key],'Content-Type':'application/json'})
            with urlopen(req,timeout=5) as r:return json.load(r)
        try:
            assert call('/api/health')['observer_only'];results.append('Real loopback HTTP startup and authentication')
            state=call('/api/p/demo/state');after=state['cursor']
            replies=[]
            waiter=threading.Thread(target=lambda:replies.append(call(f'/api/p/demo/events?after={after}&wait=3')))
            waiter.start();time.sleep(.1)
            event={'event_id':'http-'+uuid.uuid4().hex,'project_id':'demo','source':'http-test','agent_id':'A3','kind':'node.status','at':now(),'node_ids':['HTTP-TEST'],'payload':{'status':'arbitrary state'}}
            call('/api/p/demo/events',{'events':[event]},'write');waiter.join(5)
            assert replies and any(x['event_id']==event['event_id'] for x in replies[0]['events']);results.append('Real POST commit wakes GET long-poll with same event')
            try:call('/api/p/demo/events',{'events':[event]},'read');raise AssertionError('Read key wrote')
            except HTTPError as exc:assert exc.code==401
            results.append('Browser read capability cannot write over actual HTTP')
            process.terminate();process.wait(8)
            out=subprocess.run([sys.executable,'-m','waypoint','--data',str(data),'--project','demo','--agent','A3','status','QUEUED-TEST','queued status'],cwd=root,capture_output=True,text=True,timeout=6)
            assert out.returncode==0,out.stderr
            assert json.loads(out.stdout)['delivery']=='QUEUED_LOCALLY';results.append('CLI queues signal while service is absent, without claiming delivered')
            process,tokens=start()
            for _ in range(60):
                current=call('/api/p/demo/state')
                if any(x['id']=='QUEUED-TEST' and x['status']=='queued status' for x in current['node_states']):break
                time.sleep(.1)
            else:raise AssertionError('Outbox did not drain')
            assert not list((data/'outbox').glob('*.json'));results.append('Actual restart imports durable outbox and preserves prior state')
        finally:
            if process.poll() is None:process.terminate();process.wait(8)
            log.close()
    report={'status':'PASS','checks':results,'check_count':len(results),'transport':'real localhost HTTP','browser':False,'fixture':'fictional','codex_contacted':False}
    (root/'evidence/http-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report


if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
