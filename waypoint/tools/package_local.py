#!/usr/bin/env python3
"""Package this private source delivery; exclude installed state and live transcripts."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/'Waypoint-local-2026-10-17.zip'
DENIED={'.runtime','.venv','.git','.agents','.codex','.aws','__pycache__','.pytest_cache','build','dist'}

def include(path):
    relative=path.relative_to(ROOT)
    if path.is_symlink() or any(p in DENIED or p.endswith('.egg-info') for p in relative.parts):return False
    if relative.parts[0] not in {'waypoint','roadmap'} and relative.as_posix() not in {'.gitignore','PACKAGE_MANIFEST.json','START_HERE_RU.md'}:return False
    if path.name in {'access.json','connection.json'} or path.suffix in {'.db','.sqlite','.pyc','.log'} or path.name.endswith(('.db-wal','.db-shm')):return False
    return path.is_file()

def records(paths,root):
    return [{'path':p.relative_to(root).as_posix(),'size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]


def main():
    # Retain the original delivery identity, never call a modified tree the old source.
    for current,saved in [(ROOT/'PACKAGE_MANIFEST.json',ROOT/'roadmap/history/original-PACKAGE_MANIFEST.json'),(ROOT/'waypoint/MANIFEST.json',ROOT/'waypoint/evidence/original-delivery-manifest.json')]:
        if not saved.exists():saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(current.read_bytes())
    source_manifest=ROOT/'waypoint/MANIFEST.json'
    files=sorted(p for p in (ROOT/'waypoint').rglob('*') if include(p) and p!=source_manifest)
    source_manifest.write_text(json.dumps({'schema_version':'waypoint-delivery-manifest/1','project_id':'waypoint','state':'LOCAL_INTEGRATION_20261017','source_archive_sha256':'6c5c77322e79d56df988a5954830353d2493c6400750f87d040e62a054f40da6','file_count':len(files),'files':records(files,ROOT/'waypoint')},ensure_ascii=False,indent=2)+'\n')
    manifest=ROOT/'PACKAGE_MANIFEST.json'
    files=sorted(p for p in ROOT.rglob('*') if include(p) and p!=manifest)
    manifest.write_text(json.dumps({'schema_version':'waypoint-local-package/1','state':'LOCAL_INTEGRATION_20261017','files':records(files,ROOT)},ensure_ascii=False,indent=2)+'\n')
    files=sorted([*files,manifest])
    # Compare actual installed capabilities, not merely credential-looking patterns.
    secrets=[]
    for access in (ROOT/'.runtime').rglob('access.json'):
        values=json.loads(access.read_text())
        secrets.extend(v.encode() for v in values.values() if isinstance(v,str) and len(v)>=24)
    for p in files:
        data=p.read_bytes()
        if any(secret in data for secret in secrets):raise SystemExit('Refusing actual local capability in '+str(p.relative_to(ROOT)))
        if p.suffix=='.json':json.loads(data)
    with zipfile.ZipFile(ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in files:archive.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())=={p.relative_to(ROOT).as_posix() for p in files}
        for item in json.loads(manifest.read_text())['files']:
            assert hashlib.sha256(archive.read(item['path'])).hexdigest()==item['sha256']
    checksum=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    ARCHIVE.with_suffix('.zip.sha256').write_text(checksum+'  '+ARCHIVE.name+'\n')
    print(json.dumps({'status':'PASS','archive':ARCHIVE.name,'files':len(files),'size_bytes':ARCHIVE.stat().st_size,'sha256':checksum,'private_runtime_included':False,'actual_capabilities_found':0,'publication':'local only'},indent=2))

if __name__=='__main__':main()
