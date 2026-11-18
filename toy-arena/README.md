# Harmless local arena feasibility test

Run from this directory with `python3 run.py`. Python's standard library is the
only dependency. Local socket permission is required. Servers bind to loopback
on automatically assigned ports and shut down at the end. No Docker, API keys,
external network, or real vulnerable application is used.

Two HTTP services expose a public workflow and two deliberately enabled game
hint routes. Each round the independent coordinator replaces each secret.
Scripted players query the opponent's hints, submit the value to the coordinator,
and close one hint on their own service after each of the first two rounds.
They try the second hint if the first is closed. The coordinator tests the public
workflow five times per service per round and rejects prior-round proofs.

The run includes a three-round static solo control and three fresh contests.
This solo control is deliberately simplified: the paper instead allows two
single-round attempts. Both players share one process in this demonstration;
this is not a security sandbox. They access the services through HTTP, while
repairs and assessment use coordinator-owned Python objects. Scripted players
do not access the opponent's secret object directly.

Expected capture sequences: solo A = 111; contest A and B = 110. Outcomes are
prescribed by the fixed repair policy and synchronization barrier. Repeats check
mechanical consistency, not statistical evidence about autonomous capability.
Round lengths are accelerated, and health probes are batched at round end.

Outputs: `results/report.md` and `results/runs.json`, including timestamped events,
per-round observations, freshness checks, and the equal-weight attack / defense /
availability score. Local runtime is the only resource cost; API spending is $0.

Next step toward the paper: substitute model-driven players and free-running
rounds, separate assessor permissions, continuously probe functionality, and
use the original service challenge. This demo alone does not reproduce the
paper's model evaluations or establish production sandbox isolation.
