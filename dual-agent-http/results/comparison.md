# Recorded local smoke experiment

Seed 42; five rounds; 12 attack and 12 benign requests per round; 120 requests per experiment. Standard-library rule agents, actual loopback HTTP, API cost $0.

| Experiment | Detection | False positive | F1 | Attack success | Policy changes | Attacker / defender decision ms |
| --- | --- | --- | --- | --- | --- | --- |
| static | 0.0% | 55.0% | 0.000 | 100.0% | 0 | 0.0002 / 0.0009 |
| adaptive_defender | 80.0% | 55.0% | 0.681 | 20.0% | 1 | 0.0002 / 0.0115 |
| dual_adaptation | 48.3% | 46.7% | 0.496 | 51.7% | 3 | 0.0041 / 0.0083 |

These are synthetic measurements, not CyberArena benchmark results. The static policy deliberately misses the initial blue probe. Adaptive defense can learn that feature, while an adaptive attacker can switch among the allowlisted features. The shared amber feature creates false positives. Timing is machine-dependent.

Nine unit/integration tests passed, including deterministic semantic replay and quotas. Raw decisions and HTTP observations are in each experiment directory.
