# QCI-2 method-freeze v2 change summary

**Review outcome for v1:** revisions required; no execution authorized.

The original `qci2_method_freeze_v1.yaml` remains byte-identical with SHA-256
`aafc0a20a33b0cabab1f9d54ceb2da42369c8fe617d2c4c620e5ee6fb4963d24`.
It is retained as the reviewed historical proposal and is not executable.

## Changes in v2

1. Search masks contain intervenable nodes only. A retained node applies a
   paired clean-donor intervention to the attacked execution; a removed node
   preserves its attacked value. Operations occur sender, message, receiver.
2. Edges are never search actions or model operations. They enter a reported
   connected path only after a separate edge-specific BVP record passes.
3. `message.decision_code` and `message.whole` are mutually exclusive. Receiver
   layer-22 head 7 and the whole layer-22 attention output are also mutually
   exclusive. Invalid masks fail before model access.
4. Each method and seed receives its own cache and maxima: 32 unique search
   masks, 45 total evaluator calls and 1,504 model forwards. Baselines, controls,
   PPO training/selection/reload, independent verification and local-minimality
   checks are separately accounted. Actual consumption is reported.
   The 64 clean/attacked baseline forwards count toward the forward ceiling but
   are not mask evaluations; 32 search + 13 reserved mask evaluations = 45.
5. Budget exhaustion produces retained state `INCOMPLETE_BUDGET`; it never
   becomes a successful or locally minimal result.
6. The `0.1` clean threshold is explicitly the median absolute change in the raw
   `A-B` logit margin on the 16 development clean cases. It is an identity/non-
   interference diagnostic, not benign utility. Clean accuracy, flips and raw
   margins are separately required; remediation needs a later utility protocol.
7. Every hypothesized edge now has an exact intervention, downstream
   measurement, controls, direction, eligibility, thresholds and message-byte
   policy. Connected paths require every constituent edge to pass.
8. A distinct, unexecuted conflicting-evidence construct-validity protocol is
   specified. It uses new disjoint development cases and independent ground
   truth; it does not modify QCI-2.
9. Model-independent verification now covers masks, overlaps, budgets, split
   isolation, edge promotion, benign units, incomplete states and v1 immutability.

No QCI result, frozen prompt, candidate, threshold, audit artifact, validation
case or test case was changed or accessed.
