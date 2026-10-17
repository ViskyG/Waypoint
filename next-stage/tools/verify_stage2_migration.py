#!/usr/bin/env python3
"""Verify a SQLite backup of actual history; never replace the installed database."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'waypoint'))
from waypoint.store import Store

def fingerprint(db,table,columns,order):
    digest=hashlib.sha256();count=0
    for row in db.execute(f'SELECT {columns} FROM {table} ORDER BY {order}'):
        digest.update(json.dumps(tuple(row),ensure_ascii=False,separators=(',',':')).encode());count+=1
    return {'rows':count,'sha256':digest.hexdigest()}

def immutable(db):
    return {t:fingerprint(db,t,c,o) for t,c,o in [
        ('events','seq,event_id,hash,project,source,kind,agent,at,body','seq'),
        ('plans','version,project,ordinal,parent,hash,at,body','version'),
        ('requests','request_id,hash,reply','request_id'),
        ('cursors','source_key,body','source_key'),('event_plan','seq,version','seq')]}

def projections(db):
    return {t:fingerprint(db,t,'*',order) for t,order in [
        ('items','project,agent,id'),('item_facets','project,agent,item'),
        ('item_targets','project,agent,item,target_kind,target_id'),
        ('agents','project,id'),('scopes','project,agent'),('node_states','project,id'),
        ('dependency_evidence','seq'),('algorithm_evidence','seq'),('dependency_starts','project,seq,node')]}

def run(source,copy_path,output):
    if copy_path.exists():raise ValueError('Refuse existing backup destination')
    source_db=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
    target=sqlite3.connect(copy_path)
    try:source_db.backup(target)
    finally:source_db.close()
    copy_path.chmod(0o600)
    before=immutable(target);old_schema=target.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0]
    target.close()
    s=Store(copy_path)
    assert immutable(s.db)==before
    assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    migrated=projections(s.db)
    null_arrivals=s.db.execute('SELECT COUNT(*) FROM events WHERE observed_at IS NULL').fetchone()[0]
    s.close();s=Store(copy_path)
    assert immutable(s.db)==before and projections(s.db)==migrated
    receipt=s.rebuild()
    assert immutable(s.db)==before and projections(s.db)==migrated
    projects=s.projects();s.close()
    result={'status':'PASS','fixture':False,'source':'SQLite backup of actual accepted local history','schema_before':old_schema,'schema_after':'3','immutable_records':before,'legacy_unknown_arrivals':null_arrivals,'checks':['online SQLite backup','integrity_check','ledger/plans/requests/source cursors/capture versions byte-preserved','reopen identical','disposable projection replay identical'],'recovery':receipt,'projects':len(projects),'external_sources_read':False,'private_content_exported':False}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('copy',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.source,a.copy,a.output)
