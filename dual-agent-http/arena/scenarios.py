"""Finite synthetic game scenarios. No executable security payloads."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Scenario:
    id: str
    feature: str
    malicious: bool

SCENARIOS = {
    s.id: s for s in (
        Scenario('probe_amber', 'amber', True),
        Scenario('probe_blue', 'blue', True),
        Scenario('probe_green', 'green', True),
        Scenario('normal_plain', 'plain', False),
        Scenario('normal_amber', 'amber', False),
    )
}
ATTACK_IDS = tuple(k for k, s in SCENARIOS.items() if s.malicious)
BENIGN_IDS = tuple(k for k, s in SCENARIOS.items() if not s.malicious)
FEATURES = ('amber', 'blue', 'green')

def scenario(identifier):
    if not isinstance(identifier, str) or identifier not in SCENARIOS:
        raise ValueError('Scenario is not allowlisted')
    return SCENARIOS[identifier]

def policy(value):
    if not isinstance(value, (list, tuple)) or len(value) > 2:
        raise ValueError('Policy must contain at most two features')
    if any(not isinstance(x, str) or x not in FEATURES for x in value) or len(set(value)) != len(value):
        raise ValueError('Invalid defensive policy')
    return tuple(sorted(value))
