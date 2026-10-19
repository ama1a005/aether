# Contribution Matrix

| Area | Accountable | Consulted | Primary evidence | Review hand-off |
|---|---|---|---|---|
| Target protocol and tool harness | M1 | M2, M3 | `target/`, `contracts/` | Structured traces to M2/M3 |
| Attack corpus and metrics | M2 | M1, M4 | `attacks/`, `data/attack_cases/` | Validated deltas to M1/M4 |
| Hooks and neural interventions | M3 | M1, M4 | `mechanistic/`, `interventions/` | Activation traces to M4 |
| Cross-agent graph and mediation | M4 | M1, M3 | `causal/` | Causal result summaries to all |
| Review demo and documentation | All | All | `demo/`, `docs/team/` | One shared scientific narrative |

Ownership is about review and change responsibility, not exclusive knowledge. Every member must be able to explain the full pipeline, frozen contracts, evidence tiers, and current blockers. Cross-owner changes require the path owner to review them.
