# MCPTox Integration

## Source identity

- Official repository: `https://github.com/zhiqiangwang4/MCPTox-Benchmark`
- Pinned commit: `f85189f9ad12504c197c7f920ab818a40657b1fa`
- Publication: *MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers*, AAAI 2026, DOI `10.1609/aaai.v40i42.40895`
- Repository license: no license file is present at the pinned commit. Redistribution/use status requires human review.
- `pure_tool.json`: SHA-256 `9a321dc4ecf4869883cf2a29ea8189e1f7663720a9c41a3e5ce2323d580e31c1`
- `response_all.json`: SHA-256 `4f8177dcbe3718ce3d6ea6a0eec8fa27813158179bd30afe340fe854e886fdf5`

The pinned release contains 45 server groups and 485 poisoned-tool records: Template-1 77, Template-2 183, and Template-3 225. Published counts differ: the arXiv abstract reports 1,312 cases and the AAAI paper reports 1,348. These numbers are not silently reconciled.

## Native semantics

MCPTox attacks tool metadata. A malicious instruction is embedded in a poisoned tool description during tool registration; the poisoned tool need not be executed. The benchmark succeeds when the agent calls a legitimate server tool to perform the malicious action described in that metadata. The three released paradigms cover unrelated prerequisites, fake enabling prerequisites, and argument hijacking. Released labels are `Success`, `Failure-Ignored`, `Failure-Direct Execution`, `Failure-Refused`, and `None`; the release notebook excludes `None` from the ASR denominator.

The release contains queries, poisoned descriptions, server/tool identities, risks, paradigms, released responses, and labels. It does not contain the evaluator implementation or a reproducible clean-response counterpart for every poisoned record. Therefore the current smoke is released-response rescoring, not a new local-model benchmark run and not a clean-competence measurement.

## Result-origin separation

- `mcptox_official_compatible`: unchanged official records and official released labels.
- `mcptox_aether_transformed`: a future AETHER transformation; none exists in this checkpoint.
- `aether_positive_control`: the synthetic ECG substrate, which is unrelated to MCPTox semantics.

The deterministic 20-record smoke uses the first eligible released responses by sorted server and native instance order. It does not select on outcomes. Full benchmark execution and live MCP server calls are deferred.
