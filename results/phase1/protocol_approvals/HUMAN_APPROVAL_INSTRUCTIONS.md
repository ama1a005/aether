# Agent C Protocol Approval — Human Gate

**This directory holds human reviewer approval decisions. No approval file may be
created by an automated agent or CI system.**

---

## What must be created here

After a human reviewer has read and approved
`configs/experiments/agent_c_qwen_development.yaml`, they must create:

```
results/phase1/protocol_approvals/agent_c_qwen_development.json
```

with **exactly** the following schema:

```json
{
  "schema_version": "aether.protocol-decision.v1",
  "approved": true,
  "reviewer": "<full name of human reviewer>",
  "proposal_sha256": "211ff7d3cc78ab962b5b9bf9c478484c656e6ede06ab8be9427a1a05151fef5b",
  "validation_authorized": false,
  "test_authorized": false
}
```

### Field notes

| Field | Requirement |
|---|---|
| `schema_version` | Must be exactly `"aether.protocol-decision.v1"` |
| `approved` | Must be boolean `true` |
| `reviewer` | Non-empty string identifying the human reviewer by name |
| `proposal_sha256` | **Fixed value** — SHA-256 of `configs/experiments/agent_c_qwen_development.yaml` as it exists on `m1/target-harness`. Do not recompute; use the value above. If the YAML changes, the hash must be recomputed and this file updated. |
| `validation_authorized` | Must be boolean `false` — this run is development-only |
| `test_authorized` | Must be boolean `false` — this run is development-only |

---

## Verification

The runner (`experiments/phase1/qwen_agent_c.py`) calls
`verify_protocol_approval(config_path, approval_path)` before any data access.
It will raise `PermissionError` if any field is wrong or the SHA does not match.

---

## After creating the approval file

1. Commit it to `m1/target-harness`:
   ```bash
   git add results/phase1/protocol_approvals/agent_c_qwen_development.json
   git commit -m "chore(agent-c): add human protocol approval for development run"
   git push origin m1/target-harness
   ```

2. Note the new HEAD commit SHA. Update `notebooks/aether_qwen_agent_c.ipynb`
   cell 1's `COMMIT` variable to this new SHA so the Kaggle notebook clones the
   correct state.

3. Run the Kaggle notebook: `notebooks/aether_qwen_agent_c.ipynb`

4. Download the resulting `aether-agent_c-results.tar.gz`, verify it with
   `scripts/verify_external_bundle.py`, then ingest with
   `scripts/ingest_external_bundle.py`.

---

## Who may create the approval

Only a human project member with authority over the `configs/experiments/`
protocol may create this file. It must NOT be created by an AI coding agent.

---

## Current config SHA-256 (for reference)

```
211ff7d3cc78ab962b5b9bf9c478484c656e6ede06ab8be9427a1a05151fef5b
```

Computed from: `configs/experiments/agent_c_qwen_development.yaml` on branch
`m1/target-harness` at commit `c846dde3eac543ef2ceb7601ea07062622555f05`.
