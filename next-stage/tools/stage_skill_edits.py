#!/usr/bin/env python3
"""Prepare checked skill candidates/patches in a NEW folder. Never edits repositories."""
from __future__ import annotations
import argparse,difflib,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def blob(data):return hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
def transform(body:str,edit:dict,section:str)->str:
    marker=('version: "'+edit['version_from']+'"') if edit['path'].endswith('/SKILL.md') else 'версии '+edit['version_from']
    replacement=('version: "'+edit['version_to']+'"') if edit['path'].endswith('/SKILL.md') else 'версии '+edit['version_to']
    if body.count(marker)!=1:raise ValueError('Version marker mismatch: '+edit['path'])
    body=body.replace(marker,replacement,1)
    anchor=edit.get('insert_before')
    if anchor:
        if body.count(anchor)!=1:raise ValueError('Anchor mismatch: '+edit['path'])
        return body.replace(anchor,section.rstrip()+'\n\n'+anchor,1)
    return body.rstrip()+'\n\n'+section.rstrip()+'\n'
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path);parser.add_argument('--skills-root',type=Path)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    roots={'Waypoint':args.project_root,'agent-skills':args.skills_root}
    try:
        if args.out.exists():raise ValueError('Output must be a new directory')
        if any(root is not None and args.out.resolve().is_relative_to(root.resolve()) for root in roots.values()):raise ValueError('Output must be outside the input repositories')
        staged=[];skipped=[]
        for e in json.loads((ROOT/'skills/EDITS.json').read_text())['edits']:
            root=roots[e['repository']]
            if root is None:skipped.append(e['repository']+':'+e['path']);continue
            relative=Path(e['path'])
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe path')
            source=(root/relative).resolve()
            if not source.is_relative_to(root.resolve()):raise ValueError('Source escapes repository')
            raw=source.read_bytes()
            if blob(raw)!=e['expected_git_blob']:raise ValueError('Source changed; reconcile before applying: '+str(source))
            section=(ROOT/'skills'/e['section']).read_text()
            old=raw.decode('utf-8');new=transform(old,e,section)
            staged.append((e,old,new))
        if not staged:raise ValueError('No repository roots supplied')
        # Validate all inputs before writing any candidate.
        args.out.mkdir(parents=True)
        for e,old,new in staged:
            target=args.out/e['repository']/e['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_text(new,encoding='utf-8')
            patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+e['path'],tofile='b/'+e['path']))
            dest=args.out/'patches'/(e['repository']+'__'+e['path'].replace('/','__')+'.patch');dest.parent.mkdir(exist_ok=True);dest.write_text(patch,encoding='utf-8')
        (args.out/'STAGING.json').write_text(json.dumps({'state':'PREPARED_ONLY','files':len(staged),'skipped':skipped,'source_repositories_modified':False},indent=2)+'\n')
        print('PREPARED_ONLY',len(staged),'files. Skipped without supplied root:',len(skipped))
    except (OSError,ValueError,KeyError,UnicodeError) as exc:parser.exit(2,str(exc)+'\n')
if __name__=='__main__':main()
