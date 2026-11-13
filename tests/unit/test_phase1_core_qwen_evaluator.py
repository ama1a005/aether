"""Static fail-closed checks for the real CORE-02 evaluator boundary."""

from instrumentation.qci2_matched_evaluator import INTERNALS, _candidate


def test_exact_four_verified_internal_addresses_are_resolved() -> None:
    assert set(INTERNALS) == {
        "sender.module.L22.attention_output",
        "receiver.module.L22.attention_output",
        "receiver.head.L20.H5.pre_o_proj",
        "receiver.head.L22.H7.pre_o_proj",
    }
    parsed = {address: _candidate(address) for address in INTERNALS}
    assert parsed["sender.module.L22.attention_output"].agent == "sender"
    assert parsed["receiver.head.L20.H5.pre_o_proj"].head == 5
