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
# Inline the explicitly declared ordered scripts, never discover arbitrary paths.
import re
html=html.replace('</head>', '<script>window.WAYPOINT_DEMO='+payload+';</script></head>')
for name in ('themes','projects','plan','filters','algorithm_panel','app'):
    script=(root/'waypoint/web'/f'{name}.js').read_text().replace('</script', '<\\/script')
    html=html.replace(f'<script src="/static/{name}.js" defer></script>', '<script>'+script+'</script>')
if re.search(r'<script[^>]+src=',html):
    raise RuntimeError('Offline preview contains an unresolved script asset')
(root/'preview.html').write_text(html,encoding='utf-8')
(root/'examples/demo-plan.json').write_text(json.dumps(data['states'][data['current']]['plan'],ensure_ascii=False,indent=2),encoding='utf-8')
print('Created preview.html from application sources and fictional fixtures.')
