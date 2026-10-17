#!/usr/bin/env python3
"""Generate portable JSON Schemas and the actual FastAPI route description."""
from pathlib import Path
import json, sys, tempfile
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from waypoint.server import create_app
ID={"type":"string","pattern":r"^[A-Za-z0-9][A-Za-z0-9_.:@/\-]{0,199}$"}
project={"type":"string","pattern":r"^[A-Za-z0-9][A-Za-z0-9_.:@\-]{0,199}$"}
record={"type":"object"}
node={"type":"object","required":["title"],"properties":{"title":{"type":"string","maxLength":500},"parent":{"anyOf":[ID,{"type":"null"}]},"assignment":{"type":"string","maxLength":2000000},"acceptance":{"type":"object","additionalProperties":record},"tests":{"type":"object","additionalProperties":record},"layout":{"type":"object","properties":{k:{"type":"number","minimum":-1000000,"maximum":1000000} for k in ['x','y','lane','depth']}}},"additionalProperties":True}
plan={"$schema":"https://json-schema.org/draft/2020-12/schema","title":"Waypoint plan 1","type":"object","required":["schema","project_id","title","nodes"],"properties":{"schema":{"const":"waypoint.plan/1"},"project_id":project,"title":{"type":"string","maxLength":500},"nodes":{"type":"object","maxProperties":20000,"propertyNames":ID,"additionalProperties":node},"edges":{"type":"object","maxProperties":100000,"propertyNames":ID,"additionalProperties":{"type":"object","required":["from","to"],"properties":{"from":ID,"to":ID}}}},"additionalProperties":True,"$comment":"Cross-references, parent-cycle and dependency-cycle diagnostics are implemented by domain.validate_plan; JSON Schema alone cannot establish them."}
event={"$schema":"https://json-schema.org/draft/2020-12/schema","title":"Waypoint observation 1","type":"object","required":["event_id","project_id","source","kind","at"],"properties":{"schema":{"const":"waypoint.event/1"},"event_id":ID,"project_id":project,"source":ID,"kind":ID,"agent_id":{"anyOf":[ID,{"type":"null"}]},"at":{"type":"string","format":"date-time"},"node_ids":{"type":"array","items":ID,"maxItems":1000},"edge_ids":{"type":"array","items":ID,"maxItems":1000},"payload":{"type":"object"}},"additionalProperties":True,"allOf":[]}
def condition(kinds,required,payload):
 return {"if":{"properties":{"kind":{"enum":kinds}}},"then":{"required":required,"properties":{"payload":payload}}}
event['allOf'].append(condition(['node.status'],['node_ids','payload'],{'type':'object','required':['status'],'properties':{'status':{'type':'string','maxLength':240},'explanation':{'type':'string'}}}))
event['allOf'].append(condition(['test.result'],['node_ids','payload'],{'type':'object','required':['test_id','run_id','outcome'],'properties':{'test_id':ID,'run_id':ID,'outcome':{'enum':['passed','failed','skipped','error','not_run']},'freshness':{'enum':['current','stale','unknown']}}}))
event['allOf'].append({'if':{'properties':{'kind':{'enum':['scope.set','agent.upsert','agent.activity','item.upsert','item.link','item.identity_corrected']}}},'then':{'required':['agent_id'],'properties':{'agent_id':ID}}})
event['allOf'].append(condition(['item.upsert','item.link'],['payload'],{'type':'object','required':['item_id'],'properties':{'item_id':ID,'text':{'type':'string','maxLength':2000000}}}))
event['allOf'].append(condition(['item.identity_corrected'],['payload'],{'type':'object','required':['item_id','previous_agent_id','basis'],'properties':{'item_id':ID,'previous_agent_id':ID,'basis':{'type':'string','minLength':1}}}))
for name,doc in [('plan.schema.json',plan),('event.schema.json',event)]:
 (root/'schemas'/name).write_text(json.dumps(doc,ensure_ascii=False,indent=2))
with tempfile.TemporaryDirectory() as temp:
 app=create_app(Path(temp),tokens={'read':'synthetic-read-key-long-enough-for-test','write':'synthetic-write-key-long-enough-for-test'},testing=True)
 spec=app.openapi();spec['info']['description']='Actual reference API. See CONTRACTS.md and adjacent JSON Schemas for graph/event semantic validation. No agent-execution routes.'
 (root/'schemas/openapi.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2));app.state.store.close()
print('Wrote plan/event schemas and actual OpenAPI paths.')
