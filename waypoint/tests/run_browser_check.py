"""Run C06 browser checks with a new fictional localhost service, then clean up."""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen,Request
from browser_check import run

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='waypoint-browser-') as temp:
    data=Path(temp)
    service=subprocess.Popen([sys.executable,'-m','waypoint','--data',str(data),'serve','--port','18773','--demo'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+12
        while not (data/'access.json').exists() and time.monotonic()<deadline:time.sleep(.05)
        token=json.loads((data/'access.json').read_text())['read']
        while True:
            try:
                with urlopen(Request('http://127.0.0.1:18773/api/health',headers={'Authorization':'Bearer '+token}),timeout=1):break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.05)
        print(json.dumps(run('http://127.0.0.1:18773',data,root),ensure_ascii=False,indent=2))
    finally:
        service.terminate();service.wait(timeout=20)
