#!/usr/bin/env python3
"""Build offline demo from the exact application assets; no user data or secrets."""
from pathlib import Path
import json
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waypoint.demo import seed
from waypoint.store import Store
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    store=Store(Path(temp)/'demo.db');seed(store)
    versions=store.versions('demo')
    data={'current':store.head('demo'),'versions':versions,'states':{v['version']:store.state('demo',v['version']) for v in versions}}
    store.close()
html=(root/'waypoint/web/index.html').read_text()
html=html.replace('<link rel="stylesheet" href="/static/style.css">','<style>'+(root/'waypoint/web/style.css').read_text()+'</style>')
payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
html=html.replace('<script src="/static/app.js" defer></script>','<script>window.WAYPOINT_DEMO='+payload+';</script>\n<script>'+(root/'waypoint/web/app.js').read_text()+'</script>')
(root/'preview.html').write_text(html,encoding='utf-8')
(root/'examples/demo-plan.json').write_text(json.dumps(data['states'][data['current']]['plan'],ensure_ascii=False,indent=2),encoding='utf-8')
print('Created preview.html from application sources and fictional fixtures.')
