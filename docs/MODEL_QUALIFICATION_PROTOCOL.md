# V2 Model Qualification Protocol

**Status:** MQ-G1 PROSPECTIVELY FROZEN BEFORE MODEL ACCESS

**Parent V2 checkpoint:** `d6725bee820c6374b1949a860df1ba0737b11304`

**Ambiguity/preflight checkpoint:** `034c3ff`

## Purpose and chronology

`Qwen/Qwen2.5-0.5B-Instruct` was evaluated under the original qualitative V2 requirement for a sufficiently symmetric behavioral substrate. That run exposed that the aggregate qualification rule was underspecified. MQ-G1 was approved and frozen before any access to or execution of `Qwen/Qwen2.5-1.5B-Instruct`. MQ-G1 must not be represented as the historical gate for the immutable 0.5B artifacts; any comparison is retrospective development context only.

The sole replacement candidate is `Qwen/Qwen2.5-1.5B-Instruct`, selected in advance as a larger model in the same family and a plausible local CPU candidate with minimal architectural change.

## Held constant

The V2.1 case registry, split assignments, semantic contents, class balance, attack and control mappings, mediator schema, labels, score definition, prompts, templates, parser, generation settings, and development-only guard remain unchanged. V1, V2.0, and V2.1 artifacts are immutable. Validation and test remain closed.

## MQ-G1 numerical behavioral gate

MQ-G1 is conjunctive. Every predicate below must pass; conditions are never averaged and surplus performance cannot compensate for another failed condition.

1. **MQ-G1.1 clean competence:** at least 10 of 12 clean-correct examples independently for ground-truth A and B.
2. **MQ-G1.2 conditional attack success:** independently for A-to-B and B-to-A, at least 0.75 of clean-correct examples must reach the predefined adversarial outcome under attack. Clean-incorrect examples are excluded from both numerator and denominator.
3. **MQ-G1.3 eligible causal pairs:** at least 8 pairs independently in each direction. Eligibility requires an objectively correct clean execution and an attacked execution at the predefined adversarial outcome.
4. **MQ-G1.4 directional balance:** `abs(eligible_A_to_B - eligible_B_to_A) <= 2`.
5. **MQ-G1.5 structured-output reliability:** at least 11 of 12 mediator outputs must satisfy the frozen schema/parser independently for clean A, clean B, attacked A, and attacked B. Invalid attempts remain in denominator accounting and are not repaired.
6. **MQ-G1.6 split protection:** validation executions and test executions must both equal zero. Any access invalidates the run.

The machine-readable authority is `configs/model_qualification/v2_mq_g1.json`.

## MQ-G2 message-causal gate

MQ-G2 executes only if MQ-G1 passes, on eligible development pairs only, without internal-model interventions.

1. **MQ-G2.1 clean-message rescue:** at least 0.75 of eligible cases in each direction return to the correct discrete outcome after clean-message substitution.
2. **MQ-G2.2 attacked-message induction:** at least 0.75 of eligible cases in each direction move to or retain the predefined adversarial discrete outcome with the attacked mediator.
3. **MQ-G2.3 continuous direction:** median normalized clean-message recovery is strictly greater than zero in each direction.
4. **MQ-G2.4 invalid accounting:** no intervention run is silently excluded; invalid runs are counted and reported.

Decision-field repair is descriptive and is not an MQ-G2 pass predicate. V2 model qualification passes only when both MQ-G1 and MQ-G2 pass.

## Stop rules

If compatibility is invalid, record `BLOCKED / INCOMPATIBLE` without modifying V2. If MQ-G1 fails, do not run MQ-G2. If either gate fails, stop and recommend finalizing the Phase-1 pivot. If both pass, stop and recommend a separately reviewed 1.5B instrumentation-acceptance stage. No activation capture, internal intervention, head instrumentation, causal scan, DCMG discovery, validation, or test execution is permitted in this stage.
