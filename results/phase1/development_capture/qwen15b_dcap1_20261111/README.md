# Qwen2.5-1.5B DCAP-1 development capture

This directory preserves the verified metadata from the successful DCAP-1 run
executed on 2026-11-11. The run used commit
`50c9d1b01304cdb9aabf313cb1d7f35b05f6a618` and pinned model revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

The original archive is intentionally not committed because it is 4,870,794,873
bytes and contains 80 activation tensor files. Its SHA-256 is:

`7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21`

Local verification found 80/80 activation hashes valid, 86/86 manifest entries
valid, 93/93 archive-content hashes valid, no unsafe archive member paths, zero
prediction mismatches, zero tensor round-trip failures, zero hook-cleanup
failures, and zero non-finite measurements. The run produced 3,360 declared
layer-level paired measurements: 2,688 discovery and 672 untouched development
audit measurements. Validation and test execution counts are both zero.

This is activation-capture and descriptive development evidence only. It does
not establish component localization, a causal circuit, search superiority,
remediation benefit, validation performance, or test performance.
