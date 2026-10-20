"""Bilingual smoke of generated offline views, not a live Codex test."""
from pathlib import Path
import hashlib,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).with_name('offline.json')
assert not OUT.exists(), 'Evidence output must be new'
report={'scope':'Offline generated HTML in real Chromium; no live service or native Codex','views':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 for path in ['waypoint/preview.html','roadmap/PREVIEW.html']:
  context=browser.new_context(locale='ru-RU',viewport={'width':1280,'height':900})
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto((ROOT/path).as_uri());page.locator('#language').wait_for()
  page.wait_for_function('window.waypointView?.().view === "projects"')
  assert page.locator('html').get_attribute('lang')=='en'
  assert page.locator('#home').inner_text()=='Projects'
  project=page.evaluate('Object.values(window.WAYPOINT_DEMO.states)[0].plan.project_id')
  authored=page.evaluate('JSON.stringify(window.WAYPOINT_DEMO)')
  page.locator('.project-open').first.click() if page.locator('.project-open').count() else page.locator('#project').select_option(project)
  page.wait_for_function('(p)=>window.waypointView?.().project===p',arg=project)
  for language in ['ru','en']:
   page.locator('#language').select_option(language)
   assert page.locator('html').get_attribute('lang')==language
   assert page.locator('#home').inner_text()==('Проекты' if language=='ru' else 'Projects')
   assert page.evaluate('JSON.stringify(window.WAYPOINT_DEMO)')==authored
   assert page.evaluate('window.WaypointUI.translationDiagnostics().missing')==[]
  assert not errors,errors
  page.locator('#language').select_option('ru');page.reload()
  page.wait_for_function('window.WaypointUI?.language==="ru"')
  assert page.locator('#home').inner_text()=='Проекты'
  report['views'].append({'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'English_default_despite_Russian_browser':True,'both_languages':True,'Russian_persists_reload':True,'authored_data_unchanged':True,'missing_keys':[],'browser_errors':errors})
  context.close()
 report['chromium']=browser.version;browser.close()
report['status']='PASS';OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','offline_views':len(report['views'])}))
