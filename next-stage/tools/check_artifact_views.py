import json,sys,tempfile,subprocess,shutil,hashlib,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];(R/'evidence').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='wp-skill-check-') as tmp:
 t=Path(tmp);p=t/'project';p.mkdir()
 for skill in ['waypoint-map','waypoint-observe']:
  dest=p/'waypoint/skills'/skill;dest.mkdir(parents=True)
  for file in ['SKILL.md','SKILL.ru.md']:shutil.copy2(R/'sources/project-skills'/skill/file,dest/file)
 before={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
 cp=subprocess.run([sys.executable,str(R/'tools/stage_skill_edits.py'),'--project-root',str(p),'--out',str(t/'candidates')],capture_output=True,text=True,check=True)
 after={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
 assert before==after
 subprocess.run(['git','init','-q',str(p)],check=True)
 patches=sorted((t/'candidates/patches').glob('*.patch'))
 for patch in patches:subprocess.run(['git','-C',str(p),'apply','--check',str(patch)],check=True)
 # Applying to this disposable test copy demonstrates patch equivalence only.
 for patch in patches:subprocess.run(['git','-C',str(p),'apply',str(patch)],check=True)
 for f in (t/'candidates/Waypoint').rglob('*'):
  if f.is_file():assert f.read_bytes()==(p/f.relative_to(t/'candidates/Waypoint')).read_bytes()
 report={'state':'PASS','project_skill_files':4,'project_source_preserved_by_stager':True,'unified_patches_apply_to_disposable_copy':True,'candidate_matches_applied_patch':True,'global_three_skills_staging':'NOT_RUN here; source hashes and anchors taken from inspected canonical files, actual checkout required','runtime_installation':'NOT_RUN','stdout':cp.stdout}
 (R/'evidence/SKILL_STAGING.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('skill staging passed')
from playwright.sync_api import sync_playwright
checks=[];errors=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1680,'height':1050})
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content((R/'roadmap/PREVIEW.html').read_text(),wait_until='load')
 assert page.locator('#list button').count()==10;checks.append('10 packet navigation buttons')
 assert 'WPT-N00' in page.locator('#detail').inner_text();checks.append('default N00')
 page.locator('button[data-id="WPT-N03"]').click()
 assert 'полный читаемый план' in page.locator('#detail').inner_text();checks.append('human project plan description')
 assert not page.locator('details').get_attribute('open');checks.append('executor detail collapsed by default')
 page.locator('summary').click();assert page.locator('details').get_attribute('open') is not None;checks.append('executor detail expands')
 page.locator('button[data-id="WPT-N09"]').click();assert 'выдуманным референсом' in page.locator('#detail').inner_text();checks.append('third reference unresolved not faked')
 page.locator('button[data-id="WPT-N02"]').click();assert 'Показывать настоящие причины ожидания' in page.locator('#detail').inner_text();checks.append('dependency packet navigation')
 assert not errors;checks.append('no JavaScript page errors')
 page.evaluate('window.scrollTo(0,0)'); page.screenshot(path=str(R/'evidence/ROADMAP_PREVIEW.png'),full_page=False)
 (R/'evidence/BROWSER.json').write_text(json.dumps({'status':'PASS','browser':b.version,'viewport':[1680,1050],'checks':checks,'js_errors':errors,'mode':'standalone design preview via set_content; NOT product/UI integration'},ensure_ascii=False,indent=2)+'\n')
 b.close()
print('browser checks',len(checks))
