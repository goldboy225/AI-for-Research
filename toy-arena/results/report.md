# Local toy-arena results

Scripted players; real localhost HTTP services; no LLM calls; API cost: $0.

| Run | Player | Captures R1/R2/R3 | Availability | Score |
| --- | --- | --- | --- | --- |
| solo 0 | A | [1, 1, 1] | 100% | 100.0 |
| contest 1 | A | [1, 1, 0] | 100% | 66.67 |
| contest 1 | B | [1, 1, 0] | 100% | 66.67 |
| contest 2 | A | [1, 1, 0] | 100% | 66.67 |
| contest 2 | B | [1, 1, 0] | 100% | 66.67 |
| contest 3 | A | [1, 1, 0] | 100% | 66.67 |
| contest 3 | B | [1, 1, 0] | 100% | 66.67 |

All assertions passed: solo captures, persistent repairs, alternative-route fallback,
fresh secrets, stale-proof rejection, and public functionality.

Rounds are accelerated logical phases, not 20-minute rounds. Repairs follow a fixed
schedule after a synchronization barrier. These results demonstrate implementation
mechanics only, not autonomous learning, LLM capability, or the paper’s findings.
