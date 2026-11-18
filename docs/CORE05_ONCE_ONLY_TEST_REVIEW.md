# CORE-05 once-only test review

Review `configs/phase1_core/core05_once_only_test_freeze_v1.yaml` before any
implementation or test access.

## Checklist

- [ ] The repair remains exactly receiver head L20H5.
- [ ] The validation result independently passed and no method is reselected.
- [ ] Exactly test cases `v2_case_032` through `v2_case_039` are declared.
- [ ] Development and validation execution are forbidden.
- [ ] The paired clean donor is explicitly oracle information.
- [ ] Thresholds remain recovery 0.75, clean accuracy 1.0, error fraction 0.
- [ ] The complete maximum remains 504 model forwards.
- [ ] An attempt marker is written before model access.
- [ ] Interrupted work may resume the same attempt; a completed test cannot rerun.
- [ ] A negative result is retained without reselection or threshold changes.
- [ ] Claims are limited to the internal frozen synthetic substrate.

After independent review, approve only with:

> I approve CORE-05 once-only test freeze v1 SHA-256 `<exact hash>`

