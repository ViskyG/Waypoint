"""Bounded installed acceptance with actual Codex; never creates fixture messages."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'waypoint'),str(ROOT/'waypoint/tools')]
from waypoint.client import Client
from waypoint.domain import now
from verify_live import ipc_snapshot,original_text
from playwright.sync_api import sync_playwright


def run(checkpoint_path, output):
    if output.exists():raise ValueError('Use a new immutable evidence path')
    checkpoint=json.loads(checkpoint_path.read_text());data=ROOT/'.runtime/data'
    client=Client(data,timeout=8);base='/api/p/waypoint'
    state=client.call('GET',base+'/state');health=client.call('GET','/api/health')
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    check('Fresh guarded plan import retained after restart',state['version']==json.loads((ROOT/'next-stage/evidence/remaining-20261020/PLAN_IMPORT.json').read_text())['observed_version'])
    db=sqlite3.connect((data/'waypoint.db').resolve().as_uri()+'?mode=ro',uri=True)
    rows=db.execute('SELECT seq,event_id,hash FROM events WHERE seq<=? ORDER BY seq',(checkpoint['max_seq'],)).fetchall()
    check('All checkpoint event IDs and hashes preserved',len(rows)==checkpoint['event_count'] and hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()==checkpoint['event_identity_digest'])
    with sqlite3.connect((checkpoint_path.parent/'before-final-restart.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as old:
        old_keys=set(old.execute('SELECT agent,id FROM items'))
    check('All prior item identities preserved',old_keys<=set(db.execute('SELECT agent,id FROM items')))
    check('SQLite schema3 and integrity preserved',db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0]=='3')
    check('Actual source reconnected and outbox healthy',any(s['state']=='connected' and s.get('reported_state')=='connected' for s in state['sources']) and health['outbox_error'] is None)
    binding=json.loads((ROOT/'.runtime/root-binding.json').read_text());native=binding['native_id'];actor=binding['agent_id']
    check('Verifier belongs to actual root',os.environ.get('CODEX_THREAD_ID')==native)
    snapshot,ipc=ipc_snapshot(Path('/home/visky/.codex/ipc/ipc.sock'),native)
    source={};stack=[snapshot.get('turns',[]),snapshot.get('turnHistory',{}).get('history',{}).get('entitiesByKey',{})]
    while stack:
        value=stack.pop()
        if isinstance(value,dict):
            if value.get('id') and value.get('type')=='agentMessage':source[value['id']]=original_text(value,'agentMessage');continue
            stack.extend(v for k,v in value.items() if k not in {'arguments','input','output','instructions','encrypted_content'} and isinstance(v,(dict,list)))
        elif isinstance(value,list):stack.extend(value)
    projected=[json.loads(row[0]) for row in db.execute('SELECT body FROM items WHERE project=? AND agent=? AND first_seq>? ORDER BY first_seq DESC',('waypoint',actor,checkpoint['max_seq']))]
    selected=next(x for x in projected if x['id'] in source and x.get('text')==source[x['id']] and 'WPT-N08-FIX' in x.get('node_ids',[]) and any(s.startswith('codex-ipc/') for s in x.get('observed_sources',[])))
    resolved=client.call('GET',base+'/items/resolve?'+urlencode({'keys':json.dumps([[actor,selected['id']]]),'node':'WPT-N08-FIX','categories':'message'}))
    check('New ordinary native message after restart matches direct IPC and API',len(resolved['items'])==1 and resolved['items'][0]['text']==source[selected['id']])
    workers=['codex/01a15929-2593-7bd2-a1d8-9544e5317324','codex/01a15929-4c41-7321-8b50-b12d74937c65']
    agents={a['id']:a for a in state['agents']}
    check('Both actual repair workers retain nested parent identity',all(agents[a].get('parent_id')==actor for a in workers))
    warning=state['node_views']['WPT-N08']
    check('Actual23 historical warnings remain one basis period',warning['dependency_warning_count']==23 and warning['dependency_incident_count']==1 and warning['dependency_incidents'][0]['receipt_count']==23)
    registry=client.call('GET',base+'/algorithms')['algorithms']
    check('Installed registry contains summaries without observation bodies',len(registry)==4 and all(a['evidence']==[] and a['evidence_scope']=='summary' for a in registry))
    errors=[]
    with sync_playwright() as pw:
        choices=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome')]
        browser=pw.chromium.launch(executable_path=str(next(p for p in choices if p.exists())),headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':1660,'height':1050});page.on('pageerror',lambda error:errors.append(type(error).__name__))
            page.add_init_script('sessionStorage.setItem("waypoint-read-key",'+json.dumps(client.tokens['read'])+')')
            page.goto(client.url+'/#project=waypoint&node=WPT-N08-FIX')
            page.locator('.agent-card').first.wait_for()
            ids=page.locator('.agent-card').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.actor)')
            check('Actual root and nested workers rendered in Chromium',all(a in ids for a in [actor,*workers]))
            page.locator('#tabs').get_by_text('Сообщения',exact=True).click()
            message=page.locator('#inspector-body .message[data-item='+json.dumps(selected['id'])+'] .message-text')
            message.wait_for(timeout=15000)
            check('New ordinary native text reaches actual browser unchanged',message.inner_text()==source[selected['id']])
            page.locator('#inspector-body .reader-filter summary').click()
            page.locator('#inspector-body .type-filter').get_by_role('button',name='Ничего',exact=True).click()
            page.wait_for_function('()=>document.querySelectorAll("#inspector-body .message").length===0')
            page.locator('#inspector-body .type-filter').get_by_role('button',name='Все',exact=True).click()
            message.wait_for(timeout=10000);check('Actual None and All filters restore real source',message.inner_text()==source[selected['id']])
            page.locator('#close').click();page.locator('[data-view="plan"]').click()
            page.wait_for_function('()=>document.querySelectorAll(".plan-row").length===38')
            check('Updated38-node roadmap rendered',page.locator('.plan-row').count()==38)
            status='Проверена локальная установка · '+now()
            client.call('POST',base+'/events',{'events':[{'event_id':uuid.uuid4().hex,'project_id':'waypoint','source':'agent-signal','agent_id':actor,'kind':'node.status','at':now(),'node_ids':['WPT-N08-FIX'],'payload':{'status':status,'explanation':'Actual installed acceptance status observation; no executor command.'}}]})
            page.wait_for_function('(s)=>document.querySelector(".plan-row[data-node=WPT-N08-FIX] .plan-status")?.textContent.includes(s)',arg=status,timeout=15000)
            check('One genuine acceptance status event updates Plan',True)
            row=page.locator('.plan-row[data-node="WPT-N08"]');row.scroll_into_view_if_needed()
            check('Actual grouped warning appears with raw history retained',row.locator('.dependency-incident').count()==1 and 'записей журнала: 23' in row.inner_text() and row.locator('.dependency-warning-raw .dependency-record').count()==20)
            page.screenshot(path=str(output.with_suffix('.png')))
            page.locator('[data-view="map"]').click();page.locator('#search').fill('WPT-N08-FIX');page.locator('#search').press('Enter')
            page.wait_for_function('(s)=>document.querySelector(".node[data-node=WPT-N08-FIX] .status-label")?.textContent.includes(s)',arg=status,timeout=15000)
            check('Same status event updates Map',True)
            check('Browser observes imported plan version',page.evaluate('()=>waypointView().basis.plan_version')==state['version'])
            check('No uncaught application errors',not errors)
            result={'status':'PASS','captured_at':now(),'evidence_level':'actual_Codex_IPC_installed_HTTP_Store_Chromium','fixture':False,'checks':checks,'check_count':len(checks),'plan_version':state['version'],'checkpoint_event_count':len(rows),'checkpoint_max_seq':checkpoint['max_seq'],'old_item_keys_preserved':len(old_keys),'plan_versions_retained':db.execute('SELECT COUNT(*) FROM plans').fetchone()[0],'native_message_first_seq':selected['first_seq'],'native_text_exported':False,'actual_repair_workers_rendered':len(workers),'source_control_commands':0,'ipc':ipc,'browser':browser.version,'browser_errors':errors,'limits':['One current root message compared by ID/type/original text, not every future provider item.','Observed nested identity is not a claim that every historical child has a current IPC owner.','N09 remains waiting for a confirmed third graphic reference; old missing N07 bytes and unknown starts remain historical unknowns.']}
        finally:browser.close()
    db.close()
    with output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:run(args.checkpoint,args.output)
    except Exception as error:
        print(json.dumps({'status':'FAIL','error_type':type(error).__name__,'reason':str(error).split('Call log:')[0][:400],'private_navigation_and_text_suppressed':True}));sys.exit(1)
