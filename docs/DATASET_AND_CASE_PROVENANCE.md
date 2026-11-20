# Dataset and case provenance

**Current as of:** 21 November 2026

This registry answers two different questions: which upstream public sources
were used anywhere in AETHER, and which records actually appear in the demo or
central causal experiment. They are not the same.

## Demo cases

| Item | Provenance | Count | Used for research statistics? |
|---|---|---:|---|
| Active `DEMO-PAT-001` through `DEMO-PAT-012` | Twelve selected records from official PTB-XL v1.0.3 metadata, stored as a derived cohort in `demo/cases/ptbxl_demo_cases.json` | 12 | No |
| Historical v1 registry | AETHER-authored synthetic fixtures retained in `demo/cases/demo_cases.json` for history only | 12 | No |
| Demo MCP tool outputs | Deterministic outputs over the active PTB-XL-derived metadata | 12 | No |
| Demo verified replays | Previously executed deterministic software-demo artifacts under `demo/artifacts/replays_ptbxl_v1/` | 12 | No |

The active source is PTB-XL v1.0.3, PhysioNet DOI
`10.13026/kfzx-aw45`, licensed CC BY 4.0. Exact source URLs, byte sizes,
SHA-256 hashes, selection seed, record IDs, folds and derivation rules are in
`demo/cases/ptbxl_source_manifest.json`. Only folds 1–8 are used; publisher-
recommended validation fold 9 and test fold 10 are excluded.

PTB-XL does **not** supply the binary action. AETHER maps NORM-only records to
`DO_NOT_ESCALATE` and records with any non-NORM diagnostic superclass to
`ESCALATE`. This is a transparent demo transformation, not an official PTB-XL
endpoint, clinical recommendation or benchmark score. Waveforms, reports,
symptoms, vitals, medications and labs are not used or invented. The manifest
therefore continues to set `scientific_dataset: false` and records zero AETHER
validation/test executions.

## Central Qwen causal task

| Item | Provenance | Role |
|---|---|---|
| `aether-balanced-causal-v2.0.0` | Project-constructed balanced A/B task in `data/causal_v2/case_registry.json` | Qwen qualification, discovery, audit and locked evaluation |
| AETHER deterministic tool-output manipulation | Project-constructed paired attack | Creates clean/attacked causal contrast |
| Frozen mediator messages | Project contract `aether.mediator.v1` | Explicit sender-to-receiver bridge |

The central task is an AETHER experimental artifact. It is not an official
PTB-XL, MCPTox, TAMAS or BFCL score.

## Public or official-source material actually executed

| Source | Exact use | Evidence classification |
|---|---|---|
| MCPTox pinned repository `f85189f9ad12504c197c7f920ab818a40657b1fa` | Loaded pinned released records/responses; deterministic 20-record released-response rescore: 2 Success, 14 Failure-Ignored, 4 Failure-Direct Execution | Official-source released-response smoke; not a new official Qwen execution |
| TAMAS pinned repository `545c112af9aab93b7ef2b0b60831d93c81c365c3` | Loaded all 300 released adversarial records and serialized a 10-record adapter smoke | Official-source adapter validation; no native AutoGen/CrewAI benchmark run |
| Google DeepMind Tracr `9ce2b8c82b6ba10e62e86cf6f390e7536d4fd2cd` | Compiled reverse program; 24/24 declared intervention rows executed | Known-structure calibration reproduction |
| GPT-2 IOI task | 24 generated canonical-style prompts on pinned GPT-2 Small revision `3fe9a169f57f3ca0cac0b9133351644193b9dd3c` | Published-task mechanistic calibration reproduction |
| Salesforce WikiText-2 raw | Pinned 65,536-token training corpus for the Qwen SAE | Public training corpus; not an AETHER evaluation set |

## Implemented or pinned but not used as accepted experimental evidence

| Source | Current state |
|---|---|
| PTB-XL v1.0.3 | Official metadata files were downloaded from PhysioNet, hash-pinned, and used to derive the active 12-case presentation cohort. This is source-attributed demonstration data, not a PTB-XL benchmark run and not the frozen Qwen causal task. |
| BFCL `bfcl_eval==2026.3.23` | Official-evaluator package and disclosed Qwen adapter prepared; no accepted BFCL result |
| AgentDojo v1.2.2 | Native execution package prepared; no accepted run |
| MCPTox live/native campaign | Not reproduced because the pinned release lacks the original evaluator/live orchestration and has unresolved redistribution licensing |
| TAMAS native campaign | Not run; requires AutoGen/CrewAI and provider credentials or compatible Ollama execution |

## Models are not datasets

The central model is `Qwen/Qwen2.5-1.5B-Instruct` at revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. SmolLM2-1.7B-Instruct was used in
a separate failed qualification study. GPT-2 Small was used only for IOI
calibration. These model snapshots must not be described as datasets.

## Approved presentation wording

> The presentation demo uses twelve source-attributed PTB-XL v1.0.3 development-
> fold records with an explicitly AETHER-derived binary action and real software
> protocols. The scientific causal result uses a separately frozen,
> project-constructed balanced task executed on a real pinned Qwen model.
> External public sources were used for calibration, training, adapter checks and
> benchmark preparation under the classifications shown in the provenance
> registry; no missing official benchmark score is implied.

