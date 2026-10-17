"""Deterministic native taxonomy and query-bound live paging cursors. No inference."""
from __future__ import annotations
import base64
import json
from .domain import ContractError, digest, ident

CATEGORIES = ('message','explanation','plan','command','tool','change','test','agent','other')
TYPE_CATEGORY = {
 'agentMessage':'message','userMessage':'message','message':'message',
 'reasoning':'explanation','explanation':'explanation',
 'plan':'plan','planUpdate':'plan','turnPlan':'plan',
 'commandExecution':'command','command':'command',
 'mcpToolCall':'tool','toolCall':'tool','functionCall':'tool',
 'fileChange':'change','patch':'change',
 'testResult':'test','test.result':'test','test':'test',
 'subAgentActivity':'agent','agentActivity':'agent','agent':'agent',
}

def classify(item):
    native = str(item.get('native_type') or item.get('type') or 'message')
    category = TYPE_CATEGORY.get(native, 'other')
    # Only explicit machine failure data qualifies, never arbitrary prose.
    failed = item.get('is_error') is True or str(item.get('state',item.get('status',''))).lower() in {'failed','error'}
    failure = item.get('error')
    failed = failed or isinstance(failure,dict) and bool(failure)
    return {'category':category,'is_error':bool(failed),'native_type':native}

def categories(value):
    if value is None: return None
    if value in ('none', '') or value == []: return []
    result = value.split(',') if isinstance(value,str) else value
    if not isinstance(result,(list,tuple)) or not result or any(x not in CATEGORIES for x in result):
        raise ContractError('item_categories','Unknown or invalid message category')
    return sorted(set(result))

def query_hash(project,node,edge,agent,deep,selected,errors,version,outside=False):
    return digest({'project':project,'node':node,'edge':edge,'agent':agent,'deep':deep,'categories':selected,'only_errors':errors,'version':version,'outside':outside})

def encode_cursor(boundary,version,query):
    return base64.urlsafe_b64encode(json.dumps({'v':1,'direction':'older','boundary':list(boundary),'plan_version':version,'query_hash':query},separators=(',',':')).encode()).rstrip(b'=').decode()

def decode_cursor(value,version,query):
    try:
        if not isinstance(value,str) or not value or len(value)>2048:raise ValueError()
        raw=base64.b64decode(value+'='*(-len(value)%4),altchars=b'-_',validate=True)
        data=json.loads(raw)
        key=data['boundary']
        if data['v']!=1 or data['direction']!='older' or data['plan_version']!=version or data['query_hash']!=query:raise ValueError()
        if not isinstance(key,list) or len(key)!=3 or isinstance(key[0],bool) or not isinstance(key[0],int) or not 0<key[0]<2**63:raise ValueError()
        ident(key[1],'cursor actor');ident(key[2],'cursor item')
        return tuple(key)
    except (ValueError,KeyError,TypeError,UnicodeError,ContractError) as exc:
        raise ContractError('cursor_scope_mismatch','Paging cursor is invalid or belongs to another query; open a new window') from exc
