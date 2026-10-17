"""C06.3: synthetic rich histories, actual Browser -> localhost HTTP -> Store index.
Never contacts Codex, never imports any owner dialogue. Self-contained disposable service.
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright
from waypoint.store import Store


def fixture(count):
    root_count = count * 4 // 5
    branch_count = (count-root_count)//2
    nodes = {}
    for i in range(count):
        parent = None if i<root_count else f'N-{i-root_count:03}' if i<root_count+branch_count else f'N-{root_count+i-root_count-branch_count:03}'
        local = i if parent is None else 0
        nodes[f'N-{i:03}'] = {'title':f'Synthetic rich work {i}', 'assignment':'Representative assignment with bounded responsibilities and preserved original messages. '*5,'parent':parent,'acceptance':{f'A-{j}':{'text':f'Expected behavior {j}: inspect actual result separately from reported status.'} for j in range(4)},'tests':{f'T-{j}':{'label':f'Independent check {j}'} for j in range(6)},'layout':{'x':(local%10)*440+60,'y':(local//10)*470+30}}
    edges={f'E-{i:03}':{'from':f'N-{i:03}','to':f'N-{(i+1)%count:03}'} for i in range(count)}
    edges.update({f'X-{i:03}':{'from':f'N-{i:03}','to':f'N-{(i+17)%count:03}'} for i in range(count)})
    plan={'schema':'waypoint.plan/1','project_id':'rich','title':f'SYNTHETIC rich {count}', 'nodes':nodes,'edges':edges}
    events=[]
    def event(kind,payload,agent=None,node_ids=None,edge_ids=None):
        events.append({'event_id':'seed-'+str(len(events)),'project_id':'rich','source':'rich-browser-fixture','agent_id':agent,'kind':kind,'at':'2026-10-17T09:00:00Z','node_ids':node_ids or [],'edge_ids':edge_ids or [],'payload':payload})
    for i in range(24):
        actor=f'fixture/agent-{i}'
        event('agent.upsert',{'name':f'Synthetic actor {i}','parent_id':None if i==0 else f'fixture/agent-{(i-1)//3}','provider':'fixture','session_id':'fictional-container'},actor)
        event('agent.activity',{'state':'running' if i%4 else 'idle'},actor)
        event('scope.set',{},actor,[f'N-{i:03}'])
    for i in [*range(2,count),0,1]:
        event('node.status',{'status':'Reading fixture' if i%3 else 'done','explanation':'Synthetic reported state; not inferred from checks.'},'fixture/agent-0',[f'N-{i:03}'])
        for j in range(6): event('test.result',{'test_id':f'T-{j}','run_id':'synthetic-run','outcome':['passed','failed','not_run'][j%3],'freshness':'unknown'},'fixture/agent-0',[f'N-{i:03}'])
        for j in range(500 if i in [0,1] else 30):
            event('item.upsert',{'item_id':f'node-{i}-item-{j}','type':['agentMessage','reasoning','commandExecution','mcpToolCall','fileChange'][j%5],'text':f'SYNTHETIC node {i}, item {j}. '+('A representative original paragraph, with file names, tool details and readable content. '*9),'state':'completed'},f'fixture/agent-{i%24}',[f'N-{i:03}'])
        event('item.upsert',{'item_id':f'edge-{i}','type':'agentMessage','text':'Synthetic cross-scope edge message. '*10,'state':'completed'},'fixture/agent-0',[],[f'E-{i:03}'])
    return plan,events


def run(output, port):
    root=Path(__file__).resolve().parents[1]
    results=[]
    with sync_playwright() as playwright:
        executable=os.environ.get('WAYPOINT_BROWSER') or next((str(x) for x in [Path('/usr/bin/chromium'),Path(playwright.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)] if x.exists()),None)
        browser=playwright.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        try:
            for count in [100,300]:
                with tempfile.TemporaryDirectory(prefix='waypoint-rich-') as temp:
                    data=Path(temp);store=Store(data/'waypoint.db')
                    plan,events=fixture(count);store.import_plan(plan,None,'rich-fixture-'+str(count))
                    for offset in range(0,len(events),500):store.ingest(events[offset:offset+500])
                    store.close()
                    # CLI owns DB filename; preserve its exact contract.
                    service=subprocess.Popen([sys.executable,'-m','waypoint','--data',str(data),'serve','--port',str(port)],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    try:
                        deadline=time.monotonic()+10
                        access=data/'access.json'
                        while not access.exists() and time.monotonic()<deadline:time.sleep(.05)
                        tokens=json.loads(access.read_text())
                        base=f'http://127.0.0.1:{port}'
                        def request(path,body=None):
                            req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+tokens['write' if body is not None else 'read'],'Content-Type':'application/json'})
                            with urlopen(req,timeout=10) as response:return response.read()
                        while True:
                            try:request('/api/health');break
                            except OSError:
                                if time.monotonic()>deadline:raise
                                time.sleep(.05)
                        page=browser.new_page(viewport={'width':1660,'height':1050},device_scale_factor=1)
                        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                        began=time.perf_counter();page.goto(base+'/#project=rich&key='+tokens['read'],wait_until='domcontentloaded');page.wait_for_selector('.node[data-node="N-000"] [data-item="node-0-item-499"]');initial_ms=(time.perf_counter()-began)*1000
                        snapshot=request('/api/p/rich/state');json.loads(snapshot)
                        samples={}
                        for name,path in [('state','/api/p/rich/state'),('indexed_deep','/api/p/rich/items?node=N-000&deep=true&limit=100'),('indexed_direct','/api/p/rich/items?node=N-000&deep=false&limit=100')]:
                            request(path) # warmup
                            values=[]
                            for _ in range(5):
                                started=time.perf_counter();body=request(path);values.append((time.perf_counter()-started)*1000)
                            samples[name]={'n':len(values),'ms':values,'median_ms':statistics.median(values),'max_ms':max(values),'bytes':len(body)}
                        cdp=page.context.new_cdp_session(page)
                        def measure():
                            return {'elements':page.locator('*').count(),'mounted_cards':page.locator('.node').count(),'mounted_messages':page.locator('.node .message').count(),'heap':cdp.send('Runtime.getHeapUsage'),'dom':cdp.send('Memory.getDOMCounters')}
                        reading=measure()
                        page.evaluate("window.__unchangedActor=document.querySelector('[data-actor=\"fixture/agent-2\"]')")
                        actor_event={'event_id':uuid.uuid4().hex,'project_id':'rich','source':'rich-browser-fixture','agent_id':'fixture/agent-1','kind':'agent.activity','at':'2026-10-17T09:01:00Z','node_ids':[],'edge_ids':[],'payload':{'state':'idle','historical':True,'reported_by':'event_msg.task_complete'}}
                        request('/api/p/rich/events',{'events':[actor_event]})
                        page.locator('[data-actor="fixture/agent-1"] .activity-provenance').wait_for()
                        assert page.evaluate("window.__unchangedActor===document.querySelector('[data-actor=\"fixture/agent-2\"]')")
                        assert 'История' in page.locator('[data-actor="fixture/agent-1"] .activity-provenance').inner_text()

                        assert page.locator('.node .messages').first.evaluate('(e)=>getComputedStyle(e).height')=='235px'
                        page.locator('#search').fill('N-000');page.locator('#search').press('Enter')
                        page.locator('#inspector-body [data-item="node-0-item-499"]').wait_for()
                        latency=[];duration=time.monotonic()
                        # Sustained append over actual HTTP and actual committed-event long-poll, with revisions.
                        for batch in range(60):
                            native=f'flow-{batch}'
                            event={'event_id':uuid.uuid4().hex,'project_id':'rich','source':'rich-browser-fixture','agent_id':'fixture/agent-0','kind':'item.upsert','at':'2026-10-17T10:00:00Z','node_ids':['N-000'],'edge_ids':[],'payload':{'item_id':native,'type':'agentMessage','text':f'SYNTHETIC stream {batch}. '+('Flow text. '*45),'state':'completed'}}
                            started=time.perf_counter();request('/api/p/rich/events',{'events':[event]});page.locator(f'#inspector-body [data-item="{native}"]').wait_for();latency.append((time.perf_counter()-started)*1000)
                            page.wait_for_timeout(250)
                        after_stream=measure();assert page.locator('#inspector-body .message').count()<=100
                        page.locator('#close').click();page.locator('#fit').click();page.wait_for_timeout(150);overview=measure()
                        assert page.locator('#world').evaluate("e=>e.classList.contains('overview')")
                        page.locator('#viewport').focus();before=page.evaluate('waypointView().camera.x');page.keyboard.press('ArrowRight');assert page.evaluate('waypointView().camera.x')!=before
                        themes={}
                        for theme in ['terracotta','obsidian']:
                            page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
                            themes[theme]=page.evaluate("()=>{const s=getComputedStyle(document.documentElement);return {text:s.getPropertyValue('--text').trim(),panel:s.getPropertyValue('--panel').trim(),muted:s.getPropertyValue('--muted').trim(),accent:s.getPropertyValue('--accent').trim(),pass:s.getPropertyValue('--pass').trim(),fail:s.getPropertyValue('--fail').trim()}}")
                        with open(f'/proc/{service.pid}/status') as f:rss=next(line.strip() for line in f if line.startswith('VmRSS:'))
                        results.append({'nodes':count,'root_nodes':count*4//5,'nested_levels':3,'edges':len(plan['edges']),'actors':24,'history_items':sum(e['kind']=='item.upsert' for e in events),'seed_events':len(events),'db_bytes':(data/'waypoint.db').stat().st_size,'snapshot_bytes':len(snapshot),'initial_readable_ms':initial_ms,'requests':samples,'reading':reading,'after_stream':after_stream,'overview':overview,'stream':{'n':len(latency),'duration_seconds':time.monotonic()-duration,'append_visible_ms':latency,'median_ms':statistics.median(latency),'max_ms':max(latency)},'service_rss':rss,'theme_tokens':themes,'actor_incremental_history_check':'PASS','js_errors':errors})
                        assert not errors
                        page.close()
                    finally:
                        service.terminate();service.wait(timeout=20)
            hardware={'os':platform.platform(),'machine':platform.machine(),'cpu':next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),'memory_total':next(line.strip() for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:')),'logical_cpus':os.cpu_count()}
            report={'status':'PASS','fixture':'SYNTHETIC rich histories','transport':'real localhost HTTP','live_codex_tested':False,'browser':browser.version,'headless':True,'viewport':{'width':1660,'height':1050,'device_scale_factor':1},'hardware':hardware,'samples':results,'limitations':['Headless automation is not a human readability review.','60 appended messages per size are a bounded sustained-flow sample, not an hours-long soak.','No production SLA, FPS guarantee or cross-machine claim.']}
            output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
        finally:browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'evidence/rich-browser-results.json');parser.add_argument('--port',type=int,default=18770);args=parser.parse_args();run(args.output,args.port)
