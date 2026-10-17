"""N08 composed Chromium→HTTP→new Store checks; explicit synthetic fixture.

Disposable service/database; no production DB/provider contact. Generation races
are already proven by stage2_ui_check and intentionally not repeated here.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TOKENS={'read':'synthetic-stage2-read','write':'synthetic-stage2-write'}


def plan(project):
    nodes={key:{'title':project+' '+key,'parent':parent,'assignment':'EXECUTOR ONLY: inspect existing code and preserve IDs','layout':{'x':40+index*410,'y':40},'acceptance':{'A':{'text':'Keep exact behavior'}},'tests':{'T':{'label':'Synthetic correctness'}},'x_observability':{'intent':{'summary':project+' owner outcome '+key,'context':'A real reader needs project context','change':'Task and plan show the same saved description'},'algorithm_refs':['merge'] if key=='ROOT' else []}} for index,(key,parent) in enumerate([('ROOT',None),('LEAF','ROOT'),('OTHER',None)])}
    algorithm={'id':'merge','title':'Merge <img src=x onerror="window.injected=1">','purpose':'Keep IDs and history','inputs':['Saved plan'],'outputs':['Same identities'],'steps':['<script>window.injected=2</script>'],'invariants':['Never execute data'],'edge_cases':['Empty plan'],'definition_revision':1,'implementation':{'repository':'javascript:window.injected=3','revision':'synthetic-r1','refs':[{'path':'<unsafe>.py','symbol':'merge'}]},'testability':{'strategy':'Synthetic saved evidence','test_refs':[],'missing_cases':[]},'resource_risks':['No real benchmark evidence']}
    return {'schema':'waypoint.plan/1','project_id':project,'title':'Synthetic '+project,'nodes':nodes,'edges':{},'x_observability':{'schema':'waypoint.observability/1','purpose':'Synthetic purpose '+project,'algorithms':{'merge':algorithm}}}


def run(port,output):
    from playwright.sync_api import sync_playwright
    from waypoint.domain import now
    checks=[]; errors=[]; current='setup';base=f'http://127.0.0.1:{port}'
    def api(path,body=None,write=False):
        req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+TOKENS['write' if write else 'read'],'Content-Type':'application/json'})
        with urlopen(req,timeout=10) as response:return json.load(response)
    def emit(project,kind,payload,agent='A1',nodes=None):
        import uuid
        event={'event_id':uuid.uuid4().hex,'schema':'waypoint.event/1','project_id':project,'source':'demo','kind':kind,'agent_id':agent,'at':now(),'node_ids':nodes or [],'edge_ids':[],'payload':payload}
        return api(f'/api/p/{project}/events',{'events':[event]},True)
    def check(name,condition=True):
        nonlocal current
        current=name
        if not condition:raise AssertionError(name)
        checks.append(name)
    with tempfile.TemporaryDirectory(prefix='waypoint-stage2-browser-') as temp:
        log=Path(temp)/'server.log'
        with log.open('w') as logstream:
            service=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve',temp,'--port',str(port)],stdout=logstream,stderr=logstream,cwd=ROOT)
            browser=None;page=None
            try:
                for _ in range(100):
                    try:health=api('/api/health');break
                    except Exception:
                        if service.poll() is not None:raise RuntimeError(log.read_text())
                        time.sleep(.05)
                else:raise RuntimeError('Isolated service did not start')
                versions={}
                for project in ['alpha','beta']:
                    versions[project]=api(f'/api/p/{project}/plans',{'plan':plan(project),'base_version':None,'request_id':'synthetic-'+project},True)['version']
                    emit(project,'source.health',{'source_key':'demo','state':'connected','detail':'SYNTHETIC N08 HTTP/browser fixture'})
                    emit(project,'agent.upsert',{'name':'Synthetic parent','parent_id':None,'provider':'synthetic'},'A1')
                    emit(project,'agent.upsert',{'name':'Synthetic nested','parent_id':'A1','provider':'synthetic'},'A2')
                    emit(project,'agent.activity',{'state':'running'},'A2')
                    emit(project,'scope.set',{},'A2',['LEAF'])
                    emit(project,'node.status',{'status':'waiting','explanation':'Parent report is independent'},'A1',['ROOT'])
                    for index in range(65):
                        emit(project,'item.upsert',{'item_id':'msg-'+str(index),'type':'agentMessage','text':f'{project} long message {index}. '+('Original bounded reader text. '*25),'state':'completed'},'A1',['ROOT'])
                    emit(project,'item.upsert',{'item_id':'cmd-failed','type':'commandExecution','text':project+' explicit failed command','state':'failed'},'A1',['ROOT'])
                    emit(project,'item.upsert',{'item_id':'reason','type':'reasoning','text':project+' explanation preserved','state':'completed'},'A2',['LEAF'])
                    emit(project,'algorithm.observation',{'algorithm_id':'merge','definition_revision':1,'implementation_ref':'synthetic-r1','observation_kind':'correctness','correctness':{'outcome':'passed','evidence_refs':['fixture:synthetic-case']},'measurement':None,'comparison':None,'note':'Synthetic correctness record; not actual algorithm run'},'A1',['ROOT'])
                summary=api('/api/projects?summary=true')
                check('Catalogue API is metadata only with distinct active leaf count',all('items' not in x and 'messages' not in x and x['purpose'].startswith('Synthetic purpose') and x['distinct_active_agents']==1 and x['distinct_active_blocks']==1 for x in summary))
                with sync_playwright() as pw:
                    choices=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
                    browser=pw.chromium.launch(executable_path=str(next(p for p in choices if p.exists())),headless=True,args=['--no-sandbox'])
                    page=browser.new_page(viewport={'width':1660,'height':1050});page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto(base+'/#key='+TOKENS['read']);page.locator('.project-card').first.wait_for()
                    check('Actual HTTP app opens catalogue and retains two known themes with missing third',page.locator('.project-card').count()==2 and page.locator('#viewport').is_hidden() and page.locator('#theme option').count()==3 and page.locator('#theme option').last.is_disabled())
                    page.locator('.project-card[data-project="alpha"] button').click();page.locator('.node[data-node="ROOT"]').wait_for()
                    check('Waiting parent retains independent child activity in actual Store projection','waiting' in page.locator('.node[data-node="ROOT"] .status-label').inner_text() and '1 активных' in page.locator('.node[data-node="ROOT"] .descendant-badge').inner_text())
                    check('Nested native agents render with their parent',page.locator('.agent-card').count()==2 and page.locator('.orch').count()==1)
                    page.locator('.node[data-node="ROOT"] .assignment').click();page.locator('.task-subtabs').wait_for()
                    check('Human Task opens first on real state projection','alpha owner outcome ROOT' in page.locator('#inspector-body').inner_text() and 'EXECUTOR ONLY' not in page.locator('#inspector-body').inner_text())
                    page.locator('.task-subtabs').get_by_text('Для исполнителя',exact=True).click();check('Executor assignment remains in separate subtab','EXECUTOR ONLY' in page.locator('#inspector-body').inner_text())
                    page.locator('#close').click();page.locator('#project-views button[data-view="plan"]').click();page.locator('.plan-row[data-node="ROOT"]').wait_for()
                    emit('alpha','node.status',{'status':'observed-new','explanation':'One durable synthetic event'},'A1',['ROOT'])
                    page.wait_for_function("() => document.querySelector('.plan-row[data-node=ROOT] .plan-status')?.textContent.includes('observed-new')",timeout=8000)
                    page.locator('#project-views button[data-view="map"]').click();page.wait_for_function("() => document.querySelector('.node[data-node=ROOT] .status-label')?.textContent==='observed-new'")
                    check('One durable event updates both Plan and Map without duplicate agent write')
                    page.locator('.node[data-node="ROOT"] .assignment').click();page.locator('#tabs').get_by_text('Сообщения',exact=True).click();page.locator('#inspector-body .message').first.wait_for();page.locator('.reader-filter summary').click()
                    page.locator('.type-filter').get_by_text('Ничего',exact=True).click();page.wait_for_function("() => document.querySelectorAll('#inspector-body .message').length===0",timeout=4000)
                    check('Empty typed category selection returns no records through HTTP')
                    page.locator('.type-filter').get_by_text('Все',exact=True).click();page.locator('#inspector-body .message').first.wait_for()
                    page.locator('.type-filter').get_by_text('Только ошибки',exact=True).click();page.wait_for_function("() => document.querySelectorAll('#inspector-body .message').length===1",timeout=4000)
                    check('Explicit errors facet preserves only machine failed item','explicit failed command' in page.locator('#inspector-body .message').inner_text())
                    check('Inspector filtering does not rewrite independent map card reader',page.locator('.node[data-node="ROOT"] .messages .message').count()>1)
                    page.locator('.type-filter').get_by_text('Только ошибки',exact=True).click();page.locator('#inspector-body .message').nth(2).wait_for();body=page.locator('#inspector-body');body.evaluate('(x)=>x.scrollTop=300')
                    selection=body.locator('.message-text').first
                    selection.evaluate("x=>{let range=document.createRange();range.selectNodeContents(x);let s=getSelection();s.removeAllRanges();s.addRange(range)}")
                    selected=page.evaluate('getSelection().toString()');top=body.evaluate('(x)=>x.scrollTop')
                    emit('alpha','item.upsert',{'item_id':'tail-new','type':'agentMessage','text':'alpha new durable tail after user selection','state':'completed'},'A1',['ROOT'])
                    page.wait_for_function("() => document.querySelector('#inspector-body .new-messages')?.textContent.includes('1')",timeout=8000)
                    check('New HTTP event preserves old reader position and selected text',page.evaluate('getSelection().toString()')==selected and abs(body.evaluate('(x)=>x.scrollTop')-top)<3)
                    page.evaluate('getSelection().removeAllRanges()');page.locator('#close').click();page.locator('#project-views button[data-view="algorithms"]').click();page.locator('#algorithms-view .algorithm-card').wait_for()
                    check('Algorithm project view exposes saved correctness and safe injected title','подтверждена' in page.locator('#algorithms-view').inner_text() and page.locator('#algorithms-view img').count()==0 and page.locator('#algorithms-view script').count()==0 and page.evaluate('window.injected') is None and page.locator('#algorithms-view a').count()==0)
                    page.locator('#algorithms-view .algorithm-title').click();page.locator('#inspector-body .algorithm-card').wait_for();check('Right inspector opens algorithm detail via actual API',page.locator('#inspector-body .algorithm-card').count()==1)
                    page.locator('#close').click();page.locator('#project-views button[data-view="map"]').click();page.locator('.node[data-node="ROOT"] .assignment').click();page.locator('#tabs').get_by_text('Алгоритмы',exact=True).click();page.locator('#inspector-body .algorithm-card').wait_for();check('Node inspector shows associated algorithm cards',page.locator('#inspector-body .algorithm-card').count()==1)
                    page.locator('#close').click();page.select_option('#project','beta');page.wait_for_function("() => waypointView().project==='beta' && !!waypointView().basis")
                    page.locator('#project-views button[data-view="plan"]').click();page.locator('.plan-row[data-node="ROOT"]').wait_for();check('Project switch with identical block IDs keeps proper intent and status','beta owner outcome ROOT' in page.locator('#plan-view').inner_text() and 'alpha owner' not in page.locator('#plan-view').inner_text() and 'Сообщено: waiting' in page.locator('.plan-row[data-node="ROOT"]').inner_text())
                    for theme in ['terracotta','obsidian']:
                        page.select_option('#theme',theme);check('Actual HTTP theme '+theme+' keeps readable view',page.evaluate('document.documentElement.dataset.theme')==theme and page.locator('.plan-row').first.is_visible())
                    check('No browser application errors',not errors)
                    result={'status':'PASS','fixture':'SYNTHETIC isolated projects and observations','transport':'Actual Chromium → localhost HTTP → schema3 Store → durable event polling','live_codex_tested':False,'production_data_modified':False,'checks':checks,'check_count':len(checks),'browser':browser.version,'limitations':['Current production Codex connection is verified by the main N08 integration owner.','Late cross-project request variants reuse the already passed bounded synthetic race evidence.']}
                    browser.close();browser=None
            except Exception as exc:
                result={'status':'FAIL','fixture':'SYNTHETIC isolated HTTP service','transport':'Actual Chromium → localhost HTTP → current Store','live_codex_tested':False,'checks':checks,'failed_at':current,'error':str(exc),'traceback':traceback.format_exc(),'browser_errors':errors,'server_tail':log.read_text()[-2000:]}
                if page:
                    try:page.screenshot(path=str(output.with_suffix('.failure.png')))
                    except Exception:pass
                if browser:
                    try:browser.close()
                    except Exception:pass
            finally:
                service.terminate()
                try:service.wait(timeout=5)
                except subprocess.TimeoutExpired:service.kill();service.wait()
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));return result['status']=='PASS'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--serve');parser.add_argument('--port',type=int,default=18773);parser.add_argument('--output',type=Path,default=ROOT.parent/'next-stage/evidence/N08-browser.json');args=parser.parse_args()
    if args.serve:
        import uvicorn
        from waypoint.server import create_app
        uvicorn.run(create_app(Path(args.serve),tokens=TOKENS),host='127.0.0.1',port=args.port,log_level='warning',timeout_graceful_shutdown=2)
    else:sys.exit(0 if run(args.port,args.output) else 1)
