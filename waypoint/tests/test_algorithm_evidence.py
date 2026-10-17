"""Synthetic contract tests, never live correctness/measurement receipts."""
import copy
import unittest
from waypoint.algorithm_evidence import algorithm_views, compare_measurements, validate_algorithm_observation
from waypoint.domain import ContractError


def observation(eid='a1', revision='abc', outcome='passed', **extra):
    return {'event_id':eid,'kind':'algorithm.observation','source':'tests','at':'2026-01-01T00:00:00Z','seq':1,
            'payload':{'algorithm_id':'merge','definition_revision':1,'implementation_ref':revision,'observation_kind':'correctness',
                       'correctness':{'outcome':outcome,'evidence_refs':['fixture:test'] if outcome != 'not_run' else []},
                       'measurement':None,'comparison':None,'note':'Synthetic unit fixture',**extra}}


def measurement(value=12, **extra):
    return {'metric':'latency','unit':'ms','n':5,'value':value,'statistic':'median','method':'fixture','environment_ref':'env',
            'dataset_ref':'data','workload_ref':'work','semantic_revision':'1','direction':'lower','correctness':'passed',**extra}


class Algorithms(unittest.TestCase):
    def setUp(self):
        self.plan={'nodes':{'p':{'parent':None,'x_observability':{'algorithm_refs':['merge']}},'c':{'parent':'p','x_observability':{'algorithm_refs':['merge']}}},
                   'x_observability':{'algorithms':{'merge':{'id':'merge','definition_revision':1,'implementation':{'repository':'repo','revision':'abc','refs':[]}}}}}
    def test_distinct_associations_and_planned_states(self):
        views=algorithm_views(self.plan,[],node='p',deep=True)
        self.assertEqual(len(views),1)
        self.assertEqual(views[0]['associations'],[{'node_id':'c','direct':False},{'node_id':'p','direct':True}])
        self.assertEqual(views[0]['tested'],'not_run')
        self.assertFalse(views[0]['measured']);self.assertFalse(views[0]['installed'])
    def test_freshness_and_integration_separate(self):
        event=validate_algorithm_observation(observation())
        row=algorithm_views(self.plan,[event])[0]
        self.assertEqual(row['tested'],'passed');self.assertFalse(row['installed'])
        self.plan['x_observability']['algorithms']['merge']['implementation']['revision']='changed'
        row=algorithm_views(self.plan,[event])[0]
        self.assertEqual(row['tested'],'not_run');self.assertEqual(row['evidence'][0]['freshness'],'stale')
    def test_rejects_fictitious_correctness_and_bad_measurement(self):
        event=observation();event['payload']['correctness']['evidence_refs']=[]
        with self.assertRaises(ContractError):validate_algorithm_observation(event)
        for invalid in [float('nan'),float('inf'),True]:
            with self.assertRaises(ContractError):validate_algorithm_observation(observation(measurement=measurement(invalid)))
        with self.assertRaises(ContractError):validate_algorithm_observation(observation(measurement=measurement(n=0)))
    def test_comparison_guards_and_regressions(self):
        self.assertEqual(compare_measurements(measurement(12),measurement(8))['state'],'improved')
        self.assertEqual(compare_measurements(measurement(12),measurement(13))['state'],'regressed')
        self.assertEqual(compare_measurements(measurement(12),measurement(8,unit='s'))['state'],'not_comparable')
        self.assertEqual(compare_measurements(measurement(12),measurement(8,correctness='failed'))['state'],'not_established')
        self.assertEqual(compare_measurements(measurement(12),measurement(8),{'memory':'regressed'})['state'],'regressed')
        self.assertEqual(compare_measurements(measurement(12),measurement(8),{'memory':'unknown'})['state'],'not_established')
        self.assertEqual(compare_measurements(None,measurement())['state'],'not_measured')
    def test_comparison_reference_is_not_prose_speedup(self):
        event=observation(comparison={'baseline_observation_id':'missing','candidate_observation_id':'a1','constraints':{},'claim':'100x faster'})
        row=algorithm_views(self.plan,[event])[0]
        self.assertEqual(row['comparisons'][0]['state'],'not_comparable')
    def test_historical_baseline_comparison_keeps_revision_labels(self):
        old=observation('old',revision='before',measurement=measurement(12))
        new=observation('new',measurement=measurement(8))
        report=observation('cmp',comparison={'baseline_observation_id':'old','candidate_observation_id':'new','constraints':{},'claim':'Compare recorded runs'})
        row=algorithm_views(self.plan,[old,new,report])[0]
        self.assertEqual(row['comparisons'][0]['state'],'improved')
        self.assertEqual(row['comparisons'][0]['baseline_freshness'],'stale')
        self.assertEqual(row['comparisons'][0]['candidate_freshness'],'current')
    def test_failed_current_evidence_never_looks_passed(self):
        self.assertEqual(algorithm_views(self.plan,[observation(),observation('a2',outcome='failed')])[0]['tested'],'failed')

if __name__=='__main__':unittest.main()
