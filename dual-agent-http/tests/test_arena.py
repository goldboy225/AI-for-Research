import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from arena.agents import ReplayDecisions, RuleAttacker, RuleDefender
from arena.config import Config
from arena.controller import run
from arena.environment import Environment
from arena.metrics import evaluate
from arena.scenarios import policy, scenario

class UnitTests(unittest.TestCase):
    def test_config_limits(self):
        for kwargs in ({'rounds': 0}, {'rounds': True}, {'rounds': 51}, {'max_requests': 1},
                       {'request_timeout_seconds': float('nan')}, {'attack_requests': 101}):
            with self.assertRaises(ValueError): Config(**kwargs)

    def test_allowlists(self):
        for identifier in ('https://example.com', '../private', 'probe_amber?x=y', [], ''):
            with self.assertRaises(ValueError): scenario(identifier)
        for value in (['amber','blue','green'], ['amber','amber'], ['plain'], 'amber'):
            with self.assertRaises(ValueError): policy(value)

    def test_metric_ground_truth(self):
        rows = [dict(malicious=m, blocked=b, http_latency_ms=1) for m,b in
                [(True,True), (True,False), (False,True), (False,False)]]
        result = evaluate(rows)
        self.assertEqual([result[k] for k in ('tp','fn','fp','tn')], [1,1,1,1])
        for key in ('detection_rate','false_positive_rate','precision','f1'):
            self.assertEqual(result[key], 0.5)
        self.assertEqual(evaluate([])['f1'], 0)

    def test_adaptive_agents(self):
        a = RuleAttacker(True)
        self.assertNotEqual(a.decide([{'scenario_id':'probe_amber','blocked':True}], random.Random(42)), 'probe_amber')
        self.assertEqual(RuleDefender(True).decide([{'feature':'blue','blocked':False,'status':200}], ('amber',)), ('blue',))

    def test_replay_validates_output(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'plan.json'
            p.write_text(json.dumps({'role':'attacker','decisions':['probe_blue']}))
            a = ReplayDecisions(p, 'attacker')
            self.assertEqual(a.decide([], None), 'probe_blue')
            with self.assertRaises(ValueError): a.decide([], None)
            p.write_text(json.dumps({'role':'attacker','decisions':['http://outside/']}))
            with self.assertRaises(ValueError): ReplayDecisions(p, 'attacker')

class HTTPIntegrationTests(unittest.TestCase):
    def test_http_policy_and_quota(self):
        with Environment(Config(rounds=1, attack_requests=1, benign_requests=1, max_requests=2)) as env:
            self.assertEqual(env.server.server_address[0], '127.0.0.1')
            env.set_policy(['amber'])
            self.assertTrue(env.execute('probe_amber')['blocked'])
            self.assertFalse(env.execute('normal_plain')['blocked'])
            with self.assertRaises(RuntimeError): env.execute('probe_blue')
        self.assertFalse(env.thread.is_alive())

    def test_no_connection_for_invalid_scenario(self):
        with Environment(Config()) as env:
            with patch('arena.environment.http.client.HTTPConnection') as connection:
                with self.assertRaises(ValueError): env.execute('http://outside/')
                connection.assert_not_called()

    def test_runtime_limit(self):
        with Environment(Config()) as env:
            env.started -= 31
            with self.assertRaises(TimeoutError): env.execute('normal_plain')

    def test_experiments_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            results = {mode: run(Config(experiment=mode), Path(directory)/mode)
                       for mode in ('static','adaptive_defender','dual_adaptation')}
            self.assertEqual(results['static']['adaptation']['policy_changes'], 0)
            self.assertGreater(results['adaptive_defender']['aggregate']['detection_rate'],
                               results['static']['aggregate']['detection_rate'])
            self.assertGreater(results['dual_adaptation']['aggregate']['attack_success_rate'],
                               results['adaptive_defender']['aggregate']['attack_success_rate'])
            again = run(Config(experiment='dual_adaptation'), Path(directory)/'again')
            self.assertEqual(again['adaptation'], results['dual_adaptation']['adaptation'])
            def semantic_events(path):
                rows = [json.loads(x) for x in path.read_text().splitlines()]
                return [(r['scenario_id'], r['blocked'], r['policy'], r['defender_reward'])
                        for r in rows if r['event'] == 'observation']
            self.assertEqual(semantic_events(Path(directory)/'again/events.jsonl'),
                             semantic_events(Path(directory)/'dual_adaptation/events.jsonl'))
            rows = [json.loads(x) for x in (Path(directory)/'static/events.jsonl').read_text().splitlines()]
            self.assertEqual(sum(r['event'] == 'observation' for r in rows), 120)
            self.assertEqual(rows[-1]['event'], 'completed')
            with self.assertRaises(FileExistsError): run(Config(), Path(directory)/'static')

if __name__ == '__main__': unittest.main()
