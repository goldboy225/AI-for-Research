import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

@dataclass(frozen=True)
class Config:
    experiment: str = 'static'
    seed: int = 42
    rounds: int = 5
    attack_requests: int = 12
    benign_requests: int = 12
    max_requests: int = 500
    max_runtime_seconds: int = 30
    request_timeout_seconds: float = 2.0
    attacker_plan: str | None = None
    defender_plan: str | None = None

    def __post_init__(self):
        if self.experiment not in ('static', 'adaptive_defender', 'dual_adaptation'):
            raise ValueError('Unknown experiment')
        limits = {'seed': (0, 2**32-1), 'rounds': (1, 50), 'attack_requests': (1, 100),
                  'benign_requests': (1, 100), 'max_requests': (1, 5000), 'max_runtime_seconds': (1, 300)}
        for name, (low, high) in limits.items():
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'Invalid {name}')
        if type(self.request_timeout_seconds) not in (int, float) or not 0.01 <= self.request_timeout_seconds <= 5:
            raise ValueError('Invalid request timeout')
        if self.rounds * (self.attack_requests + self.benign_requests) > self.max_requests:
            raise ValueError('Request quota too small for configuration')
        for name in ('attacker_plan', 'defender_plan'):
            if getattr(self, name) is not None and not isinstance(getattr(self, name), str):
                raise ValueError('Plan must be a local path')

    @classmethod
    def load(cls, path):
        raw = json.loads(Path(path).read_text())
        if not isinstance(raw, dict) or set(raw) - {f.name for f in fields(cls)}:
            raise ValueError('Unknown configuration fields')
        return cls(**raw)

    def as_dict(self):
        return asdict(self)
