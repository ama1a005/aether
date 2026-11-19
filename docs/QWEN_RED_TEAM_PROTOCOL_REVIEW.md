# Qwen red-team development protocol review

The proposal at `configs/experiments/qwen_red_team_development.yaml` is a
development-only supporting robustness protocol. It freezes the Qwen revision,
case-selection rule, corpus-generation policy, four attack families, surfaces,
pre-output eligibility, error accounting, bounded call budget, raw evidence
schema, metrics, and restart policy. It keeps validation and test counters at
zero.

The implementation now runs model-free admission checks before snapshot access,
binds corpus provenance and per-pair deltas to the campaign plan, and requires
independent bundle verification before ingestion. A low ASR is retained as a
negative scientific outcome; incomplete rows, bad provenance, or a budget
overrun are evidence failures.

Human approval is still required. The owner must compute the SHA-256 of the
current YAML bytes and issue exactly:

`I approve Qwen real red-team development protocol v1 SHA-256 <EXACT_HASH>`

Until then, do not download or access the Qwen snapshot for this campaign.
