#!/usr/bin/env python3
"""Check exact packaged delivery. No services, network or code execution."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[2]
m=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
errors=[]
for f in m['files']:
 p=(root/f['path']).resolve()
 if not p.is_relative_to(root) or not p.is_file():errors.append(f['path']);continue
 b=p.read_bytes()
 if len(b)!=f['size_bytes'] or hashlib.sha256(b).hexdigest()!=f['sha256']:errors.append(f['path'])
print(json.dumps({'status':'FAIL' if errors else 'PASS','checked':len(m['files']),'different_or_missing':errors,'meaning':'exact current packaged delivery integrity, not proof of runtime behavior'},ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
