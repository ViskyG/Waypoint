import copy, importlib.util, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference'));sys.path.insert(0,str(ROOT/'tools'))
from contract_model import effective_requirements, effective_cycle_nodes, condition_fingerprint, evaluate_requirement, filtered_page, compare_measurements, validate_profile
from prepare_stage_merge import prepare


def sample():
    p=json.loads((ROOT/'contracts/examples/PROJECT.plan.json').read_text())
    p['nodes']['CHILD']=copy.deepcopy(p['nodes']['REPORT']);p['nodes']['CHILD']['parent']='REPORT'
    return p

def observation(r,availability='available',source='unit',seq=1,workspace='w1'):
    return {'event_id':f'{source}-{seq}','source':source,'seq':seq,'consumer_id':r['consumer_id'],
            'requirement_fingerprint':r['requirement_fingerprint'],'workspace_ref':workspace,
            'availability':availability,'basis':{'ref':'synthetic-result','explanation':'test fixture'}}

class DependencyModelTests(unittest.TestCase):
    def test_direct(self): self.assertEqual(len(effective_requirements(sample(),'REPORT')),1)
    def test_node_only_not_inherited(self): self.assertEqual(effective_requirements(sample(),'CHILD'),[])
    def test_subtree_inherited(self):
        p=sample();p['edges']['NEEDS_DATA']['x_observability']['target_scope']='subtree'
        self.assertTrue(effective_requirements(p,'CHILD')[0]['inherited'])
    def test_parent_id_not_name_prefix(self):
        p=sample();p['nodes']['FETCH.child']=copy.deepcopy(p['nodes']['FETCH']);p['nodes']['FETCH.child']['parent']=None
        self.assertEqual(effective_requirements(p,'FETCH.child'),[])
    def test_order_not_blocker(self):
        p=sample();p['edges']['NEEDS_DATA']['x_observability']['relation']='order'
        self.assertEqual(effective_requirements(p,'REPORT'),[])
    def test_finish_not_start(self):
        p=sample();p['edges']['NEEDS_DATA']['x_observability']['phase']='finish'
        self.assertEqual(effective_requirements(p,'REPORT'),[])
        self.assertEqual(len(effective_requirements(p,'REPORT','finish')),1)
    def test_legacy_not_silently_ready(self):
        p=sample();del p['edges']['NEEDS_DATA']['x_observability']
        r=effective_requirements(p,'CHILD')[0]
        self.assertEqual(evaluate_requirement(r,[],'w1')['state'],'unknown')
    def test_layout_does_not_invalidate(self):
        p=sample();a=condition_fingerprint(p,'NEEDS_DATA','REPORT');p['nodes']['FETCH']['layout']['x']=999
        self.assertEqual(a,condition_fingerprint(p,'NEEDS_DATA','REPORT'))
    def test_predicate_does_invalidate(self):
        p=sample();a=condition_fingerprint(p,'NEEDS_DATA','REPORT')
        p['nodes']['FETCH']['x_observability']['outputs']['O1']['definition']='Different required result'
        self.assertNotEqual(a,condition_fingerprint(p,'NEEDS_DATA','REPORT'))
    def test_missing_evidence_not_status_done(self):
        p=sample();p['nodes']['FETCH']['status']='done';r=effective_requirements(p,'REPORT')[0]
        self.assertEqual(evaluate_requirement(r,[],'w1')['state'],'unknown')
    def test_matching_evidence_satisfied(self):
        r=effective_requirements(sample(),'REPORT')[0]
        self.assertEqual(evaluate_requirement(r,[observation(r)],'w1')['state'],'satisfied')
    def test_other_workspace_unknown(self):
        r=effective_requirements(sample(),'REPORT')[0]
        self.assertEqual(evaluate_requirement(r,[observation(r)],'w2')['state'],'unknown')
    def test_reporter_conflict_not_last_writer_wins(self):
        r=effective_requirements(sample(),'REPORT')[0]
        self.assertEqual(evaluate_requirement(r,[observation(r),observation(r,'missing','other',2)],'w1')['state'],'conflict')
    def test_same_reporter_can_withdraw(self):
        r=effective_requirements(sample(),'REPORT')[0]
        self.assertEqual(evaluate_requirement(r,[observation(r),observation(r,'missing',seq=2)],'w1')['state'],'missing')
    def test_effective_self_dependency(self):
        p=sample();p['edges']['NEEDS_DATA']['from']='CHILD';p['edges']['NEEDS_DATA']['x_observability']['target_scope']='subtree'
        self.assertIn('CHILD',effective_cycle_nodes(p))
    def test_parent_cycle_rejected(self):
        p=sample();p['nodes']['REPORT']['parent']='CHILD'
        with self.assertRaises(ValueError):effective_requirements(p,'REPORT')

class FilterModelTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'project_id':'p','agent_id':'a','id':str(i),'first_seq':i,'category':'command' if i else 'message','node_ids':['n','child']} for i in range(1005)]
    def test_rare_old_match_before_limit(self):self.assertEqual(filtered_page(self.rows,project='p',categories={'message'},limit=10)['items'][0]['id'],'0')
    def test_none_is_not_all(self):self.assertEqual(filtered_page(self.rows,project='p',categories=set())['items'],[])
    def test_all_default(self):self.assertEqual(len(filtered_page(self.rows,project='p')['items']),100)
    def test_project_isolation(self):self.assertEqual(filtered_page(self.rows,project='other')['items'],[])
    def test_deep_duplicate_identity_once(self):self.assertEqual(len(filtered_page([self.rows[0],self.rows[0]],project='p',node_ids={'n','child'})['items']),1)
    def test_error_is_orthogonal(self):
        self.rows[1]['is_error']=True
        self.assertEqual([r['id'] for r in filtered_page(self.rows,project='p',only_errors=True)['items']],['1'])
    def test_equal_seq_total_order(self):
        rows=[dict(self.rows[0],id='a',first_seq=1),dict(self.rows[0],id='b',first_seq=1)]
        one=filtered_page(rows,project='p',limit=1);two=filtered_page(rows,project='p',boundary=one['before'],limit=1)
        self.assertEqual([one['items'][0]['id'],two['items'][0]['id']],['b','a'])
    def test_unknown_stays_visible(self):
        self.rows[0]['category']='other'
        self.assertEqual(filtered_page(self.rows,project='p',categories={'other'})['items'][0]['id'],'0')

class AlgorithmModelTests(unittest.TestCase):
    def setUp(self):self.c=json.loads((ROOT/'contracts/examples/algorithm-observations.json').read_text())['cases'][0]
    def test_comparable(self):self.assertEqual(compare_measurements(self.c['baseline'],self.c['candidate'])['state'],'improved')
    def test_dataset_not_comparable(self):
        self.c['candidate']['dataset_ref']='other'
        self.assertEqual(compare_measurements(self.c['baseline'],self.c['candidate'])['state'],'not_comparable')
    def test_wrong_correctness(self):
        self.c['candidate']['correctness']='failed'
        self.assertEqual(compare_measurements(self.c['baseline'],self.c['candidate'])['state'],'not_established')
    def test_regression_not_hidden(self):
        self.c['candidate']['value']=20
        self.assertEqual(compare_measurements(self.c['baseline'],self.c['candidate'])['state'],'regressed')
    def test_invalid_number(self):
        self.c['candidate']['value']=float('nan')
        with self.assertRaises(ValueError):compare_measurements(self.c['baseline'],self.c['candidate'])

class PackageContractTests(unittest.TestCase):
    def setUp(self):self.stage=json.loads((ROOT/'roadmap/ROADMAP.plan.json').read_text())
    def test_stage_profile_and_no_cycle(self):self.assertEqual(validate_profile(self.stage),[])
    def test_second_project_profile(self):self.assertEqual(validate_profile(sample()),[])
    def test_native_schema_preserves_profile(self):
        from legacy_domain import validate_plan
        validated,warnings=validate_plan(self.stage)
        self.assertEqual(validated,self.stage);self.assertEqual(warnings,[])
    def test_stage_merge_preserves_unrelated(self):
        old=sample();old['project_id']='waypoint';old['x_roadmap']['resource_policy']='MIXED';old['custom_unrelated']={'x':1}
        body=prepare({'version':'v-current','plan':old},self.stage)
        self.assertEqual(body['plan']['nodes']['REPORT'],old['nodes']['REPORT'])
        self.assertEqual(body['plan']['custom_unrelated'],{'x':1});self.assertEqual(body['base_version'],'v-current')
    def test_prepared_request_stable(self):
        old=sample();old['project_id']='waypoint';old['x_roadmap']['resource_policy']='MIXED';ex={'version':'v-current','plan':old}
        self.assertEqual(prepare(ex,self.stage),prepare(ex,self.stage))
    def test_reimport_does_not_overwrite_live_stage_edits(self):
        old=sample();old['project_id']='waypoint';old['x_roadmap']['resource_policy']='MIXED';body=prepare({'version':'v1','plan':old},self.stage)
        body['plan']['nodes']['WPT-N03']['assignment']='A later authorized live edit'
        self.assertIsNone(prepare({'version':'v2','plan':body['plan']},self.stage))
    def test_collision_fails(self):
        old=sample();old['project_id']='waypoint';old['x_roadmap']['resource_policy']='MIXED';old['nodes']['WPT-N00']={'title':'another task'}
        with self.assertRaises(ValueError):prepare({'version':'v1','plan':old},self.stage)
    def test_missing_export_version_fails(self):
        with self.assertRaises(ValueError):prepare({'plan':self.stage},self.stage)
    def test_wrong_project_fails(self):
        with self.assertRaises(ValueError):prepare({'version':'v1','plan':sample()},self.stage)

if __name__=='__main__':unittest.main()
