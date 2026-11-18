"""Common bounded decision interfaces; agents never receive network clients."""
from collections import Counter

import json
from pathlib import Path
from typing import Protocol
from .scenarios import ATTACK_IDS, FEATURES, policy

class Attacker(Protocol):
    def decide(self, observations: list[dict], rng) -> str: ...

class Defender(Protocol):
    def decide(self, observations: list[dict], current: tuple[str, ...]) -> tuple[str, ...]: ...

class RuleAttacker:
    def __init__(self, adaptive=False):
        self.adaptive = adaptive

    def decide(self, observations, rng):
        if not self.adaptive or not observations:
            return 'probe_blue'
        rates = {}
        for identifier in ATTACK_IDS:
            attempts = [o for o in observations if o['scenario_id'] == identifier]
            # Untried routes are optimistic; prefer recent unblocked routes.
            rates[identifier] = sum(not o['blocked'] for o in attempts)/len(attempts) if attempts else 1.0
        best = max(rates.values())
        return rng.choice([k for k, value in rates.items() if value == best])

class RuleDefender:
    def __init__(self, adaptive=False):
        self.adaptive = adaptive

    def decide(self, observations, current):
        if not self.adaptive or not observations:
            return ('amber',)
        # No labels or scenario IDs: only observed request features and verdicts.
        counts = Counter(o['feature'] for o in observations if o['feature'] in FEATURES)
        return policy(sorted(counts, key=lambda f: (-counts[f], f))[:2])

class ReplayDecisions:
    """Optional offline LLM-output adapter; no provider calls or generated HTTP."""
    def __init__(self, path, role):
        p = Path(path)
        if p.stat().st_size > 65536:
            raise ValueError('Decision plan exceeds 64 KiB')
        raw = json.loads(p.read_text())
        if not isinstance(raw, dict) or set(raw) != {'role', 'decisions'} or raw['role'] != role:
            raise ValueError('Invalid decision plan')
        decisions = raw['decisions']
        if not isinstance(decisions, list) or not 1 <= len(decisions) <= 5000:
            raise ValueError('Invalid decision count')
        if role == 'attacker':
            if any(not isinstance(x, str) or x not in ATTACK_IDS for x in decisions):
                raise ValueError('Non-allowlisted attacker decision')
            self.decisions = decisions
        elif role == 'defender':
            self.decisions = [policy(x) for x in decisions]
        else:
            raise ValueError('Unknown role')
        self.index = 0

    def decide(self, observations, context):
        if self.index >= len(self.decisions):
            raise ValueError('Decision plan exhausted')
        result = self.decisions[self.index]
        self.index += 1
        return result
