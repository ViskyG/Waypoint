"""Read-only installed-target verification; no fixture events or agent control."""
import hashlib,json,sqlite3,sys
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'waypoint'),str(ROOT/'waypoint/tools')]
from waypoint.client import Client
from waypoint.domain import now
from verify_live import ipc_snapshot,original_text
from playwright.sync_api import sync_playwright

def main():
    output=ROOT/'next-stage/evidence/four-defects-20261017/LIVE.json'
    if output.exists():raise ValueError('Preserve immutable proof; choose a new run path')
    private=ROOT/'.runtime/four-defects-20261017';checkpoint=json.loads((private/'restart-checkpoint.json').read_text());data=ROOT/'.runtime/data';client=Client(data)
    state=client.call('GET','/api/p/waypoint/state');health=client.call('GET','/api/health')
    assert state['version']==checkpoint['version'] and health['outbox_error'] is None
    db=sqlite3.connect((data/'waypoint.db').resolve().as_uri()+'?mode=ro',uri=True)
    rows=db.execute('SELECT seq,event_id,hash FROM events WHERE seq<=? ORDER BY seq',(checkpoint['max_seq'],)).fetchall()
    assert len(rows)==checkpoint['event_count'] and hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()==checkpoint['event_identity_digest']
    with sqlite3.connect((private/'before-service-restart.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as old:
        old_keys=set(old.execute('SELECT agent,id FROM items'))
    keys=set(db.execute('SELECT agent,id FROM items'));assert old_keys<=keys
    binding=json.loads((ROOT/'.runtime/root-binding.json').read_text());native=binding['native_id'];actor=binding['agent_id']
    snapshot,ipc=ipc_snapshot(Path('/home/visky/.codex/ipc/ipc.sock'),native)
    source={};stack=[snapshot.get('turns',[]),snapshot.get('turnHistory',{}).get('history',{}).get('entitiesByKey',{})]
    while stack:
        value=stack.pop()
        if isinstance(value,dict):
            if value.get('id') and value.get('type')=='agentMessage':source[value['id']]=original_text(value,'agentMessage');continue
            stack.extend(v for k,v in value.items() if k not in {'arguments','input','output','instructions','encrypted_content'} and isinstance(v,(dict,list)))
        elif isinstance(value,list):stack.extend(value)
    projected=[json.loads(row[0]) for row in db.execute('SELECT body FROM items WHERE project=? AND agent=? ORDER BY first_seq DESC',('waypoint',actor))]
    selected=next(x for x in projected if x['id'] in source and x.get('text')==source[x['id']] and 'WPT-N04-FIX' in x.get('node_ids',[]) and x['first_seq']>=15010)
    reply=client.call('GET','/api/p/waypoint/items/resolve?'+urlencode({'keys':json.dumps([[actor,selected['id']]]),'node':'WPT-N04-FIX','categories':'message'}))
    assert len(reply['items'])==1 and reply['items'][0]['text']==source[selected['id']]
    assert any(s['state']=='connected' and s.get('reported_state')=='connected' for s in state['sources'])
    assert all(n.get('basis',{}).get('workspace_ref') for n in state['node_views'].values())
    key=json.loads((data/'access.json').read_text())['read'];errors=[]
    with sync_playwright() as pw:
        candidates=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome')]
        browser=pw.chromium.launch(executable_path=str(next(p for p in candidates if p.exists())),headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':1540,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
            page.add_init_script('sessionStorage.setItem("waypoint-read-key",'+json.dumps(key)+')');page.goto(client.url+'/#project=waypoint&node=WPT-N04-FIX')
            page.locator('#tabs').get_by_text('Сообщения',exact=True).click()
            message=page.locator('#inspector-body .message[data-item='+json.dumps(selected['id'])+'] .message-text');message.wait_for(timeout=10000)
            assert message.inner_text()==source[selected['id']]
            page.locator('#close').click();page.locator('#project-views button[data-view="plan"]').click();page.wait_for_function('() => document.querySelectorAll(".plan-row").length===38')
            page.locator('.plan-row[data-node="WPT-N02-FIX"]').scroll_into_view_if_needed();page.screenshot(path=str(output.with_suffix('.png')))
            basis=page.evaluate('() => waypointView().basis');assert basis['plan_version']==checkpoint['version'] and not errors
            result={'status':'PASS','captured_at':now(),'scope':'Actual installed Waypoint after service replacement, actual Codex root IPC and existing native message, real headless Chromium; no synthetic events','plan_version':basis['plan_version'],'cursor':basis['cursor'],'event_prefix_preserved':len(rows),'prefix_event_ids_and_hashes_equal':True,'old_item_keys_preserved':len(old_keys),'plan_versions_retained':db.execute('SELECT COUNT(*) FROM plans').fetchone()[0],'sqlite_integrity':db.execute('PRAGMA integrity_check').fetchone()[0],'observer_source_connected':True,'outbox_error':health['outbox_error'],'native_id_type_original_text_exact':1,'selected_item_first_seq':selected['first_seq'],'selected_item_text_exported':False,'native_text_visible_through_resolve_and_browser':True,'ipc':ipc,'browser':browser.version,'browser_errors':errors,'old_health_fixture_and_correction_negative_cases':'Separate SYNTHETIC actual HTTP/Chromium receipt run1/RESULT.json','limitations':'Bounded root-message and recovery check; not a repeat of complete family/native comparison, not full product acceptance.'}
        finally:browser.close()
    db.close()
    with output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
