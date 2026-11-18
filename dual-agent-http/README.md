# Synthetic dual-agent HTTP research platform

A minimum viable local experiment with dedicated attacker and defender agents,
loopback HTTP simulation, and an independent controller/scorer. Inspired by
CyberArena's adaptive interaction idea; this asymmetric toy experiment does not
reproduce its symmetric CTF benchmark or reported model results.

## Run

Python 3.10+, standard library only. From this directory:

```sh
python3 -m unittest discover -s tests -v
python3 -m arena --config configs/static.json --output results/static
python3 -m arena --config configs/adaptive_defender.json --output results/adaptive_defender
python3 -m arena --config configs/dual_adaptation.json --output results/dual_adaptation
```

Use a new output directory each time. Local listening sockets must be permitted.
No Docker, credentials, external network, package installation, or API spending.

## Experiments and activities

| Experiment | Attacker | Defender |
| --- | --- | --- |
| Static baseline | Always blue probe | Always blocks amber |
| Adaptive defender | Always blue probe | Learns frequent features from previous round |
| Dual adaptation | Prefers successful or untried probes from previous round | Same adaptive defender |

Each round: defender selects a policy, controller shuffles a seeded traffic
schedule, attacker chooses a scenario for each attack slot, controller executes
fixed HTTP requests, and assessor records results. Both agents use previous-round
observations only. The attacker sees its scenario IDs and blocked outcomes. The
defender sees features, status, and blocked verdicts, without scenario IDs or true
labels. Only the assessor uses ground-truth labels for evaluation and rewards.

Three synthetic probe features (amber, blue, green) stand for attack classes.
No actual exploit occurs. Legitimate traffic is either plain or amber; the shared
amber feature makes false positives possible. A defensive policy can block at most
two features. The simple adaptive defender selects the most frequent suspicious
features; it may overblock legitimate traffic and need not beat a static policy.

## Assessment and reproducibility

Every run saves resolved `config.json`, timestamped `events.jsonl`, and `summary.json`.
Logs include decisions, scenario IDs, policy actions, HTTP observations, rewards,
UTC time, elapsed time, agent decision latency, and separate HTTP latency.

TP = blocked malicious, FN = served malicious, FP = blocked benign, TN = served benign.
Detection/recall = TP/(TP+FN); FPR = FP/(FP+TN); precision = TP/(TP+FP);
F1 = 2TP/(2TP+FP+FN). Zero denominators return zero. In this simulation detection
means blocking, not a separate IDS alert. Attacker reward = 1 for a served malicious
probe, else 0. Defender reward = +1 for a correct verdict and -1 otherwise.

Adaptation includes last-minus-first detection/attack-success rates, policy change
count, and scenario counts per round. Aggregate results include warm-up round 1.
Same configuration and seed reproduce choices/outcomes, not timing or timestamps.
Use multiple seeds for research comparisons; the supplied single seed is a smoke
experiment, not evidence of statistical significance or autonomous learning.

## Architecture and optional LLM output

- `scenarios.py`: finite scenario and policy allowlists.
- `agents.py`: common Attacker/Defender protocols and rule-based implementations.
- `environment.py`: bounded loopback HTTP server and executor.
- `controller.py`: multi-round orchestration, filtered histories, rewards, logs.
- `metrics.py`: confusion matrix and evaluation.
- `config.py`: strict configurable bounds.

Optional offline LLM decisions use the same agent interface. Set `attacker_plan`
or `defender_plan` to a local JSON file with one decision per attack request or
per defender round:

```json
{"role":"attacker","decisions":["probe_blue","probe_green"]}
```

```json
{"role":"defender","decisions":[["amber"],["blue","green"]]}
```

Plans are limited to 64 KiB, checked against allowlists before execution, and stop
on exhaustion. This adapter supports offline LLM-origin decisions; **live model
inference is not implemented**. Replay cannot react to fresh observations. A future
local model can implement the protocols, with separate inference process/time limits.
No agent decision can supply a URL, arbitrary payload, shell command, or policy code.

## Execution limits and isolation scope

The simulator binds only to 127.0.0.1 on an ephemeral port; the executor connects
only to that bound port. It uses `http.client`, which neither uses environment
proxies nor automatically follows redirects. No remote target setting exists.
All scenarios are synthetic. Requests have no bodies. Unknown IDs are rejected
before connection. Fixed paths never access files or fetch upstream resources.

Hard upper limits: 50 rounds, 100 requests per traffic class per round, 5,000 total
requests, 300 seconds runtime, 5 seconds per request, 4 KiB response reads, two
blocked features, 64 KiB replay input. Configurations must fit the request quota;
limits are checked again at execution. Runtime is checked between decisions/requests,
and request timeout is clamped to remaining time. Failure events are logged and
servers shut down on exit. An in-flight operation/shutdown can slightly exceed the
overall deadline. Output grows only with the bounded request count.

This trusted single-process application is not a hostile-code sandbox or an OS
network namespace. It does not execute untrusted agents. Supplied networking is
loopback-only; arbitrary Python plugins would require OS isolation. The single-threaded
server and bounded workload limit resource usage; OS-level CPU/RAM quotas are not
implemented. Do not expose it on a public interface or add unreviewed executable plugins.

## Verification

Tests cover metric arithmetic, config bounds, allowlist rejection, offline plan
validation/exhaustion, actual HTTP policy behavior, loopback binding, request/time
quotas, rejection before connection, cleanup, all three experiments, deterministic
semantic replay, and refusal to overwrite existing results.
