import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from .agents import ReplayDecisions, RuleAttacker, RuleDefender
from .environment import Environment
from .metrics import evaluate
from .scenarios import ATTACK_IDS, BENIGN_IDS, scenario

def run(config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rng = random.Random(config.seed)
    attacker = ReplayDecisions(config.attacker_plan, 'attacker') if config.attacker_plan else RuleAttacker(config.experiment == 'dual_adaptation')
    defender = ReplayDecisions(config.defender_plan, 'defender') if config.defender_plan else RuleDefender(config.experiment != 'static')
    all_rows, rounds, attack_history, defender_history = [], [], [], []
    attacker_times, defender_times = [], []
    started = time.monotonic()
    (output/'config.json').write_text(json.dumps(config.as_dict(), indent=2)+'\n')
    with (output/'events.jsonl').open('w') as events:
        def log(kind, **data):
            events.write(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=time.monotonic()-started, event=kind, **data))+'\n')
            events.flush()
        try:
            with Environment(config) as env:
                for round_id in range(1, config.rounds+1):
                    begin = time.perf_counter()
                    selected = defender.decide(defender_history, env.current_policy)
                    latency = (time.perf_counter()-begin)*1000
                    defender_times.append(latency)
                    env.set_policy(selected)
                    log('defender_decision', round=round_id, policy=list(env.current_policy), latency_ms=latency,
                        observation_count=len(defender_history))
                    # Fixed attack baseline; adaptive attacker sees previous round only.
                    schedule = ['attack']*config.attack_requests + ['benign']*config.benign_requests
                    rng.shuffle(schedule)
                    rows = []
                    for role in schedule:
                        if time.monotonic()-started >= config.max_runtime_seconds:
                            raise TimeoutError('Controller runtime quota exhausted')
                        decision_ms = None
                        if role == 'attack':
                            begin = time.perf_counter()
                            identifier = attacker.decide(attack_history, rng)
                            decision_ms = (time.perf_counter()-begin)*1000
                            attacker_times.append(decision_ms)
                            if not isinstance(identifier, str) or identifier not in ATTACK_IDS:
                                raise ValueError('Invalid attacker decision')
                            log('attacker_decision', round=round_id, scenario_id=identifier, latency_ms=decision_ms)
                        else:
                            identifier = rng.choice(BENIGN_IDS)
                        observation = env.execute(identifier)
                        item = scenario(identifier)
                        row = dict(round=round_id, scenario_id=identifier, malicious=item.malicious,
                            **observation, policy=list(env.current_policy), decision_latency_ms=decision_ms,
                            attacker_reward=int(item.malicious and not observation['blocked']),
                            defender_reward=1 if item.malicious == observation['blocked'] else -1)
                        rows.append(row)
                        log('observation', **row)
                    all_rows.extend(rows)
                    attack_history = [dict(scenario_id=r['scenario_id'], blocked=r['blocked']) for r in rows if r['malicious']]
                    defender_history = [dict(feature=r['feature'], blocked=r['blocked'], status=r['status']) for r in rows]
                    summary = dict(round=round_id, policy=list(env.current_policy), **evaluate(rows),
                        attacker_reward=sum(r['attacker_reward'] for r in rows),
                        defender_reward=sum(r['defender_reward'] for r in rows))
                    rounds.append(summary)
                    log('round_summary', **summary)
            adaptation = dict(
                detection_delta=rounds[-1]['detection_rate']-rounds[0]['detection_rate'],
                attack_success_delta=rounds[-1]['attack_success_rate']-rounds[0]['attack_success_rate'],
                policy_changes=sum(a['policy'] != b['policy'] for a, b in zip(rounds, rounds[1:])),
                attack_scenario_counts=[{identifier: sum(r['round'] == t and r['scenario_id'] == identifier for r in all_rows)
                    for identifier in ATTACK_IDS} for t in range(1, config.rounds+1)])
            result = dict(config=config.as_dict(), aggregate=evaluate(all_rows), rounds=rounds, adaptation=adaptation,
                decision_latency_ms=dict(attacker_mean=sum(attacker_times)/len(attacker_times),
                    defender_mean=sum(defender_times)/len(defender_times)),
                limitations='Synthetic game markers; scripted policies; detection means blocked request; no LLM capability claim.')
            (output/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
            log('completed', total_requests=len(all_rows))
            return result
        except Exception as error:
            log('failed', error_type=type(error).__name__, message=str(error))
            raise
