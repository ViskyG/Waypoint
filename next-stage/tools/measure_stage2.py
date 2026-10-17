#!/usr/bin/env python3
"""Bounded N08 HTTP/UI measurements on disposable SYNTHETIC 100/300-node fixtures.

Reuses established rich fixture generation, never user history or production DB.
This is descriptive measurement, not a universal SLA or model/provider benchmark.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.request import Request,urlopen

WORKSPACE=Path(__file__).resolve().parents[2]
ROOT=WORKSPACE/'waypoint'
sys.path.insert(0,str(ROOT))
TOKENS={'read':'synthetic-perf-read','write':'synthetic-perf-write'}


def run(port,output):
    from playwright.sync_api import sync_playwright
    from waypoint.domain import now
    fixture_spec=importlib.util.spec_from_file_location('rich_stage_fixture',ROOT/'tests/rich_browser_check.py')
    fixture_module=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture_module)
    base=f'http://127.0.0.1:{port}';results=[];checks=[];browser=None
    def request(path,body=None):
        req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+TOKENS['write' if body is not None else 'read'],'Content-Type':'application/json'})
        with urlopen(req,timeout=30) as response:return response.read()
    try:
        with sync_playwright() as pw:
            candidates=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
            browser=pw.chromium.launch(executable_path=str(next(p for p in candidates if p.exists())),headless=True,args=['--no-sandbox'])
            browser_version=browser.version
            for count in [100,300]:
                with tempfile.TemporaryDirectory(prefix='waypoint-stage2-measure-') as temp:
                    data=Path(temp);log=data/'service.log'
                    with log.open('w') as logs:
                        service=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve',str(data),'--port',str(port)],cwd=ROOT,stdout=logs,stderr=logs)
                        page=None
                        try:
                            for _ in range(100):
                                try:json.loads(request('/api/health'));break
                                except Exception:
                                    if service.poll() is not None:raise RuntimeError(log.read_text())
                                    time.sleep(.05)
                            else:raise RuntimeError('Disposable service failed to start')
                            plan,events=fixture_module.fixture(count)
                            plan['x_observability']={'schema':'waypoint.observability/1','algorithms':{},'purpose':f'Synthetic {count}-node rich measurement'}
                            for key,node in plan['nodes'].items():node['x_observability']={'intent':{'summary':'Preserve readable original work '+key,'context':'Representative synthetic rich history','change':'Read current observations without losing history'}}
                            request('/api/p/rich/plans',{'plan':plan,'base_version':None,'request_id':'perf-'+str(count)})
                            # Deliberately old failures before thousands of newer non-error messages:
                            # a post-limit facet would return zero; association-first filtering returns all three.
                            early=[]
                            for index in range(3):
                                early.append({'event_id':'early-failed-'+str(index),'project_id':'rich','source':'rich-browser-fixture','agent_id':'fixture/agent-0','kind':'item.upsert','at':now(),'node_ids':['N-000'],'edge_ids':[],'payload':{'item_id':'rare-failed-'+str(index),'type':'commandExecution','text':'SYNTHETIC explicitly failed old command '+str(index),'state':'failed'}})
                            events=early+events
                            for offset in range(0,len(events),400):request('/api/p/rich/events',{'events':events[offset:offset+400]})
                            request('/api/p/rich/events',{'events':[{'event_id':'perf-health','project_id':'rich','source':'rich-browser-fixture','kind':'source.health','at':now(),'node_ids':[],'edge_ids':[],'payload':{'source_key':'rich-browser-fixture','state':'connected','detail':'Synthetic local performance fixture'}}]})
                            routes={
                                'catalogue':'/api/projects?summary=true',
                                'state':'/api/p/rich/state',
                                'all_20':'/api/p/rich/items?node=N-000&deep=false&limit=20',
                                'none_20':'/api/p/rich/items?node=N-000&deep=false&limit=20&categories=none',
                                'command_20':'/api/p/rich/items?node=N-000&deep=false&limit=20&categories=command',
                                'errors_20':'/api/p/rich/items?node=N-000&deep=false&limit=20&categories=command&only_errors=true'}
                            samples={};responses={}
                            for label,path in routes.items():
                                request(path) # one bounded warmup, then three descriptive HTTP samples
                                elapsed=[]
                                for _ in range(3):
                                    started=time.perf_counter();body=request(path);elapsed.append((time.perf_counter()-started)*1000)
                                parsed=json.loads(body);responses[label]=parsed
                                samples[label]={'n':3,'ms':elapsed,'median_ms':statistics.median(elapsed),'max_ms':max(elapsed),'bytes':len(body),'records':len(parsed.get('items',[])) if isinstance(parsed,dict) else len(parsed)}
                            assert len(responses['all_20']['items'])==20
                            assert responses['none_20']['items']==[]
                            assert all(item['category']=='command' for item in responses['command_20']['items'])
                            assert {item['id'] for item in responses['errors_20']['items']}=={'rare-failed-0','rare-failed-1','rare-failed-2'}
                            assert not any(item['is_error'] for item in responses['all_20']['items'])
                            checks.append(f'{count} nodes: All/None and explicit rare errors filtered before limit despite newer rich history')
                            page=browser.new_page(viewport={'width':1660,'height':1050});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                            started=time.perf_counter();page.goto(base+'/#project=rich&key='+TOKENS['read'],wait_until='domcontentloaded');page.locator('.node[data-node="N-000"] .message').first.wait_for(timeout=8000);initial_ms=(time.perf_counter()-started)*1000
                            assert 'project=rich' in page.url and 'key=' not in page.url
                            checks.append(f'{count} nodes: deep link retains project after read key removal')
                            cdp=page.context.new_cdp_session(page)
                            reading={'mounted_cards':page.locator('.node').count(),'mounted_messages':page.locator('.node .message').count(),'elements':page.locator('*').count(),'heap':cdp.send('Runtime.getHeapUsage'),'dom':cdp.send('Memory.getDOMCounters')}
                            started=time.perf_counter();page.locator('#project-views button[data-view="plan"]').click();page.locator('.plan-row').nth(count-1).wait_for();plan_ms=(time.perf_counter()-started)*1000
                            assert page.locator('.plan-row').count()==count
                            page.locator('#project-views button[data-view="map"]').click();page.locator('.node[data-node="N-000"] .assignment').click();page.locator('#tabs').get_by_text('Сообщения',exact=True).click();page.locator('#inspector-body .message').first.wait_for();page.locator('.reader-filter summary').click();page.locator('.type-filter').get_by_text('Только ошибки',exact=True).click();page.wait_for_function('() => document.querySelectorAll("#inspector-body .message").length===3')
                            assert all('explicitly failed old command' in text for text in page.locator('#inspector-body .message').all_text_contents())
                            checks.append(f'{count} nodes: browser error filter reaches old matching bodies through HTTP; all {count} Plan rows mounted')
                            assert not errors,errors
                            rss=next(line.strip() for line in Path(f'/proc/{service.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
                            results.append({'nodes':count,'root_nodes':count*4//5,'edges':len(plan['edges']),'actors':24,'history_items':sum(event['kind']=='item.upsert' for event in events),'seed_events':len(events),'body_shape':'mixed native message/reasoning/command/tool/change; ~800 chars per ordinary item; 500 items in each of N-000/N-001','service_rss':rss,'db_bytes':(data/'waypoint.db').stat().st_size,'http':samples,'browser_initial_readable_ms':initial_ms,'browser_plan_mount_ms':plan_ms,'reading':reading,'browser_errors':errors})
                            page.close();page=None
                        finally:
                            if page:
                                try:page.close()
                                except Exception:pass
                            service.terminate()
                            try:service.wait(timeout=5)
                            except subprocess.TimeoutExpired:service.kill();service.wait()
            report={'status':'PASS','fixture':'SYNTHETIC isolated rich histories; no owner transcript','transport':'Actual Chromium → localhost HTTP → schema3 Store','live_codex_tested':False,'production_data_modified':False,'recovered_issue':'First attempt found project hash lost while consuming read key; root fixed key-only removal and this run checks project retained/key removed','browser':browser_version,'headless':True,'viewport':{'width':1660,'height':1050},'environment':{'os':platform.platform(),'machine':platform.machine(),'logical_cpus':os.cpu_count(),'cpu':next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),'memory_total':next(line.strip() for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))},'checks':checks,'samples':results,'limitations':['Three timed HTTP samples after one warmup are descriptive, not confidence intervals or universal thresholds.','Single-machine headless synthetic measurement; no FPS, production SLA, provider latency or hours-long soak claim.','HTTP response semantics prove old rare matches survive before the limit; Store structural query checks separately establish that bodies are fetched after association/type/error ID selection.','Existing C01–C07 sustained-flow evidence was reused; no repeated 60-event campaign.']}
    except Exception as exc:report={'status':'FAIL','fixture':'SYNTHETIC isolated performance service','error':str(exc),'traceback':traceback.format_exc(),'checks':checks,'samples':results,'prior_attempt':{'status':'FAIL','cause':'Project hash was lost while consuming read key; first 100-node HTTP filters already passed','fixed_by':'Root integration owner; subsequent run required to validate deep-link fix'}}
    finally:
        if browser:
            try:browser.close()
            except Exception:pass
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'status':report['status'],'output':str(output),'checks':checks,'samples':[{'nodes':x['nodes'],'items':x['history_items'],'initial_ms':round(x['browser_initial_readable_ms'],2),'plan_ms':round(x['browser_plan_mount_ms'],2),'state_median_ms':round(x['http']['state']['median_ms'],2),'filtered_errors_median_ms':round(x['http']['errors_20']['median_ms'],2)} for x in results],'error':report.get('error')},ensure_ascii=False));return report['status']=='PASS'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--serve');parser.add_argument('--port',type=int,default=18774);parser.add_argument('--output',type=Path,default=WORKSPACE/'next-stage/evidence/N08-performance.json');args=parser.parse_args()
    if args.serve:
        import uvicorn
        from waypoint.server import create_app
        uvicorn.run(create_app(Path(args.serve),tokens=TOKENS),host='127.0.0.1',port=args.port,log_level='warning',timeout_graceful_shutdown=2)
    else:sys.exit(0 if run(args.port,args.output) else 1)
