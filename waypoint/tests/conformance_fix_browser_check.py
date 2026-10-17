"""Four audited regressions through real Chromium/HTTP, synthetic disposable data."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json,subprocess,sys,tempfile,time,traceback,uuid
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'waypoint'),str(ROOT/'waypoint/tests')]
from stage2_http_browser_check import plan,TOKENS
from waypoint.domain import now

def run(output):
    from playwright.sync_api import sync_playwright
    output.mkdir(parents=True,exist_ok=False)
    result={'scope':'SYNTHETIC fixture; actual Chromium → HTTP → disposable Store; no native Codex contact','production_data_modified':False,'checks':[],'browser_errors':[]}
    base='http://127.0.0.1:18784';project='four-defects'
    def api(path,body=None):
        request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+TOKENS['write' if body is not None else 'read'],'Content-Type':'application/json'})
        with urlopen(request,timeout=10) as reply:return json.load(reply)
    def emit(kind,payload,nodes=None,at=None):
        return api('/api/p/'+project+'/events',{'events':[{'event_id':uuid.uuid4().hex,'project_id':project,'source':'synthetic','agent_id':'actor','kind':kind,'at':at or now(),'node_ids':nodes or [],'payload':payload}]})
    def check(label,condition=True):
        result['checks'].append({'name':label,'passed':bool(condition)})
        if not condition:raise AssertionError(label)
    browser=None;service=None;page=None
    try:
        with tempfile.TemporaryDirectory(prefix='waypoint-four-defects-') as temp:
            with (Path(temp)/'service.log').open('w') as log:
                service=subprocess.Popen([sys.executable,str(ROOT/'waypoint/tests/stage2_http_browser_check.py'),'--serve',temp,'--port','18784'],stdout=log,stderr=log)
                try:
                    for _ in range(100):
                        try:api('/api/health');break
                        except Exception:
                            if service.poll() is not None:raise RuntimeError('Disposable service exited')
                            time.sleep(.05)
                    p=plan(project);p['x_observability']['workspace_ref']='plan-default';p['nodes']['ROOT']['x_observability']['workspace_ref']='node-local'
                    p['nodes']['OTHER']['x_observability']['outputs']={'OUT':{'definition':'Synthetic reviewed output','revision':1}}
                    for eid,target,scope,phase in [('ORDER','ROOT','subtree','start'),('PARTIAL','LEAF','node','finish')]:
                        p['edges'][eid]={'from':'OTHER','to':target,'x_observability':{'relation':'order','phase':phase,'target_scope':scope,'why':'Ordering context '+eid}}
                    p['edges']['REQUIRED']={'from':'OTHER','to':'ROOT','x_observability':{'relation':'requires','phase':'finish','target_scope':'subtree','why':'Concrete required result','condition':{'output_id':'OUT','revision':1,'workspace':'consumer'}}}
                    api('/api/p/'+project+'/plans',{'plan':p,'request_id':'four-defects-initial'})
                    emit('source.health',{'source_key':'synthetic','state':'connected'},at='2020-01-01T00:00:00Z')
                    catalogue=api('/api/projects?summary=true')[0]
                    check('F04 API old connected becomes stale and activity counts unknown',catalogue['source_health']['state']=='stale' and catalogue['distinct_active_agents'] is None)
                    prereq=api('/api/p/'+project+'/prerequisites?node=ROOT&workspace=override-base')
                    check('F03 explicit override is exact API basis and requirement basis',prereq['basis']['workspace_ref']['consumer']=='override-base' and all(x['workspace_ref']['consumer']=='override-base' for x in prereq['requirements']))
                    packet=api('/api/p/'+project+'/packet/ROOT');state=api('/api/p/'+project+'/state')
                    check('F03 node-local workspace in packet and per-node state basis',packet['basis']['workspace_ref']['consumer']=='node-local' and state['node_views']['ROOT']['basis']['workspace_ref']['consumer']=='node-local')
                    check('F02 order stays in shared state and packet, never a missing input',all(any(x['edge_id']=='ORDER' and x['state']=='not_required' for x in entries) for entries in [packet['prerequisites']['start'],state['node_views']['ROOT']['prerequisites']['start']]))
                    for i in range(40):emit('item.upsert',{'item_id':'msg-'+str(i),'type':'agentMessage','text':'Message %d. '%i+'Synthetic bounded original text. '*24},['ROOT'])
                    with sync_playwright() as pw:
                        choices=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome')]
                        browser=pw.chromium.launch(executable_path=str(next(p for p in choices if p.exists())),headless=True,args=['--no-sandbox'])
                        result['browser']=browser.version;page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:result['browser_errors'].append(str(e)))
                        page.goto(base+'/#key='+TOKENS['read']);page.locator('.project-card').wait_for()
                        check('F04 catalogue explains stale source and preserves reported connected/time','данные устарели' in page.locator('.source-health').inner_text() and 'подключён' in page.locator('.source-health-detail').inner_text() and '2020' in page.locator('.source-health-detail').inner_text())
                        emit('source.health',{'source_key':'synthetic','state':'connected'},at=(datetime.now(timezone.utc)-timedelta(seconds=20)).isoformat())
                        page.reload();page.locator('.source-health').wait_for();check('F04 fresh report initially stays connected','подключены' in page.locator('.source-health').inner_text())
                        page.wait_for_function("() => document.querySelector('.source-health')?.textContent.includes('данные устарели')",timeout=11000)
                        check('F04 open catalogue refreshes as the report crosses freshness boundary')
                        page.locator('.project-card button').click();page.locator('.node[data-node="ROOT"]').wait_for()
                        check('F02 order edges dashed and distinct from requires',page.locator('#edges .edge-order').count()==2 and page.locator('#edges .edge-requires').count()==1 and page.locator('#edges .edge-order').first.evaluate('(x)=>getComputedStyle(x).strokeDasharray')!='none')
                        partial=page.locator('#edges [data-edge="PARTIAL"]');check('F02 collapsed edge marks partial and retains actual endpoints',partial.get_attribute('data-partial')=='true' and 'OTHER → LEAF' in partial.text_content() and 'частично' in partial.text_content())
                        partial.locator('.edge-hit').press('Enter');check('F02 edge inspector exposes order, phase and reason','Порядок · не блокирует' in page.locator('#inspector-body').inner_text() and 'Ordering context PARTIAL' in page.locator('#inspector-body').inner_text());page.locator('#close').click()
                        page.locator('#project-views button[data-view="plan"]').click();root=page.locator('.plan-row[data-node="ROOT"]');root.locator('.prerequisites summary').first.click()
                        check('F02/F03 Plan shows order reason/non-blocking and actual workspace','Ordering context ORDER' in root.inner_text() and 'не блокирует' in root.inner_text() and 'node-local' in root.inner_text())
                        page.screenshot(path=str(output/'plan.png'))
                        page.locator('#project-views button[data-view="map"]').click();page.locator('.node[data-node="ROOT"] .assignment').click();page.locator('#tabs').get_by_text('Сообщения',exact=True).click();page.locator('#inspector-body .message').first.wait_for()
                        page.locator('.reader-filter summary').click();page.locator('.type-filter').get_by_text('Ничего',exact=True).click();page.locator('[data-category="message"]').check();page.locator('#inspector-body .message[data-item="msg-5"]').wait_for()
                        body=page.locator('#inspector-body');body.evaluate('(x)=>{x.scrollTop=300;x.dispatchEvent(new Event("scroll"))}')
                        emit('item.upsert',{'item_id':'msg-5','type':'commandExecution','text':'Corrected category command'},['ROOT'])
                        page.wait_for_function("() => !document.querySelector('#inspector-body .message[data-item=\"msg-5\"]')",timeout=8000)
                        check('F01 corrected-out visible identity leaves old reader; unrelated rows remain',page.locator('#inspector-body .message').count()==39 and page.locator('#inspector-body .message[data-item="msg-4"]').count()==1)
                        for i in range(140):emit('item.upsert',{'item_id':'new-'+str(i),'type':'agentMessage','text':'New tail '+str(i)},['ROOT'])
                        page.locator('#inspector-body .new-messages').wait_for(state='visible',timeout=8000)
                        check('F01 truncated latest page does not delete arbitrary old identities',page.locator('#inspector-body .message[data-item="msg-4"]').count()==1 and page.locator('#inspector-body .message').count()==39)
                        emit('item.link',{'item_id':'msg-6'},['OTHER'])
                        page.wait_for_function("() => !document.querySelector('#inspector-body .message[data-item=\"msg-6\"]')",timeout=8000)
                        check('F01 exact reconciliation also removes an item moved outside scope',page.locator('#inspector-body .message[data-item="msg-7"]').count()==1)
                        page.screenshot(path=str(output/'reader.png'));check('No uncaught browser errors',not result['browser_errors'])
                        browser.close();browser=None
                finally:
                    service.terminate()
                    try:service.wait(timeout=5)
                    except subprocess.TimeoutExpired:service.kill();service.wait()
        result['status']='PASS'
    except Exception:
        result['status']='FAIL';result['failure']=traceback.format_exc()
        if page:
            try:page.screenshot(path=str(output/'failure.png'))
            except Exception:pass
    finally:
        if browser:browser.close()
        result['captured_at']=now()
        result['source_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'waypoint/waypoint/web/app.js',ROOT/'waypoint/waypoint/web/plan.js',ROOT/'waypoint/waypoint/read_models.py',ROOT/'waypoint/waypoint/source_health.py',ROOT/'waypoint/waypoint/store.py',ROOT/'waypoint/waypoint/server.py']}
        (output/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks':len(result['checks']),'output':str(output),'failure':result.get('failure')},ensure_ascii=False))
    return int(result['status']!='PASS')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();sys.exit(run(args.output))
