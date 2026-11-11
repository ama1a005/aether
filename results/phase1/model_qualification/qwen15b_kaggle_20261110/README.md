# Qwen2.5-1.5B qualification evidence

This directory contains the JSON and JSONL artifacts extracted from the Kaggle
qualification archive produced on 2026-11-10 UTC. The run used repository commit
`ed6a9ab742426d45626b63c211642079af9f1a97` and official Qwen revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

Local ingestion verified all eleven artifacts named in `manifest.json` by
SHA-256. MQ-HW1, MQ-G1, and MQ-G2 passed; all 24 rows were development rows and
validation/test execution counts were zero. The source archive itself was not
present in the repository at ingestion, so its outer `.tar.gz` hash is not
recorded here. The inner artifact hashes remain verifiable and authoritative.

This run qualifies the behavioral substrate for a separately reviewed
instrumentation-acceptance stage. It contains no activation capture, internal
intervention, circuit localization, search, validation, or test evidence.
