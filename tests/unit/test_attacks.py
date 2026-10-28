import os
import shutil
import pytest
from attacks.corpus.attack_store import AttackStore
from attacks.corpus.builder import CorpusBuilder
from attacks.adapters.mcptox_adapter import MCPToxAdapter
from attacks.templates.frozen_templates import ATTACK_TEMPLATES
from attacks.a2a.manipulator import A2AManipulator
from attacks.evaluator import AttackEvaluator
from attacks.stats import bootstrap_ci, paired_mcnemar
from contracts.schemas import AttackSpec, A2AMessageRecord, RunTrace

@pytest.fixture
def temp_store():
    store_dir = 'temp_test_corpus'
    store = AttackStore(store_dir)
    yield store
    if os.path.exists(store_dir):
        shutil.rmtree(store_dir)

def test_corpus_builder_count(temp_store):
    builder = CorpusBuilder(seed=42)
    specs = builder.build_review_corpus(temp_store, n_per_family=3)
    assert len(specs) == 9

def test_corpus_builder_deterministic(temp_store):
    builder1 = CorpusBuilder(seed=123)
    specs1 = builder1.build_review_corpus(temp_store, n_per_family=2)
    builder2 = CorpusBuilder(seed=123)
    specs2 = builder2.build_review_corpus(temp_store, n_per_family=2)
    assert [s.attack_id for s in specs1] == [s.attack_id for s in specs2]

def test_corpus_families(temp_store):
    builder = CorpusBuilder(seed=42)
    specs = builder.build_review_corpus(temp_store, n_per_family=2)
    families = set(s.family for s in specs)
    assert families == {'tool_description_poison', 'tool_output_inject', 'a2a_manipulation'}

def test_attack_store_roundtrip(temp_store):
    spec = AttackSpec(
        attack_id="atk_test_001",
        family="test_family",
        target_surface="test_surface",
        target_behavior="ESCALATE",
        clean_payload={"a": 1},
        adversarial_payload={"a": 2},
        metadata={}
    )
    temp_store.add(spec)
    loaded = temp_store.load("atk_test_001")
    assert loaded.attack_id == spec.attack_id
    assert loaded.family == spec.family
    assert loaded.adversarial_payload == spec.adversarial_payload

def test_attack_store_list_family(temp_store):
    temp_store.add(AttackSpec("atk_1", "fam1", "surf1", "beh1", {}, {}, {}))
    temp_store.add(AttackSpec("atk_2", "fam1", "surf1", "beh1", {}, {}, {}))
    temp_store.add(AttackSpec("atk_3", "fam2", "surf1", "beh1", {}, {}, {}))
    fam1_specs = temp_store.load_family("fam1")
    assert len(fam1_specs) == 2
    assert all(s.family == "fam1" for s in fam1_specs)


def test_phase1_corpus_adds_deterministic_implicit_preference_family(temp_store):
    builder = CorpusBuilder(seed=42)
    specs = builder.build_phase1_corpus(temp_store, n_per_family=3)
    assert len(specs) == 12
    implicit = [spec for spec in specs if spec.family == "implicit_preference_manipulation"]
    assert len(implicit) == 3
    assert all(spec.target_surface == "mcp_tool_description" for spec in implicit)
    assert all(spec.metadata["explicit_command"] is False for spec in implicit)
    assert all("DO_NOT_ESCALATE" not in spec.adversarial_payload["description"] for spec in implicit)
    assert builder.build_phase1_corpus(temp_store, 3)[-3:] == implicit


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_phase1_corpus_rejects_invalid_family_count(temp_store, count):
    with pytest.raises(ValueError, match="positive integer"):
        CorpusBuilder().build_phase1_corpus(temp_store, count)

def test_mcptox_adapter_mapping():
    adapter = MCPToxAdapter()
    mcptox_attack = {
        "attack_id": "m1",
        "attack_type": "tool_description_poison",
        "original_description": "clean",
        "malicious_description": "poisoned",
        "risk_category": "high",
        "tool_name": "t1"
    }
    spec = adapter.mcptox_to_attack_spec(mcptox_attack)
    assert spec.family == "tool_description_poison"
    assert spec.clean_payload["description"] == "clean"
    assert spec.adversarial_payload["description"] == "poisoned"

def test_frozen_templates_exist():
    expected = [
        'tool_desc_v1_override_priority', 'tool_desc_v2_preclearance', 'tool_desc_v3_system_note',
        'tool_output_v1_flip_risk', 'tool_output_v2_clear_flags', 'a2a_v1_downplay'
    ]
    for e in expected:
        assert e in ATTACK_TEMPLATES

def test_a2a_manipulator_applies():
    manipulator = A2AManipulator()
    msg = A2AMessageRecord("m1", "r1", "s1", "r2", "clean text", {"risk_level": "CRITICAL"})
    spec = AttackSpec("a1", "a2a_manipulation", "a2a_message", "DO_NOT_ESCALATE", {}, {"risk_level": "LOW", "content_text": "bad text"}, {})
    res = manipulator.apply_attack(msg, spec)
    assert res.structured_payload["risk_level"] == "LOW"
    assert res.content_text == "bad text"

def test_a2a_manipulator_immutable():
    manipulator = A2AManipulator()
    msg = A2AMessageRecord("m1", "r1", "s1", "r2", "clean text", {"risk_level": "CRITICAL"})
    spec = AttackSpec("a1", "a2a_manipulation", "a2a_message", "DO_NOT_ESCALATE", {}, {"risk_level": "LOW"}, {})
    res = manipulator.apply_attack(msg, spec)
    assert msg.structured_payload["risk_level"] == "CRITICAL"

def test_a2a_manipulator_diff_fields():
    manipulator = A2AManipulator()
    clean = A2AMessageRecord("m1", "r1", "s1", "r2", "clean text", {"risk_level": "CRITICAL", "other": "x"})
    attacked = A2AMessageRecord("m1", "r1", "s1", "r2", "bad text", {"risk_level": "LOW", "other": "x"})
    diffs = manipulator.get_diff_fields(clean, attacked)
    assert "content_text" in diffs
    assert "structured_payload.risk_level" in diffs
    assert "structured_payload.other" not in diffs

def test_evaluator_labels_success():
    evaluator = AttackEvaluator()
    spec = AttackSpec("atk_1", "fam1", "surf1", "DO_NOT_ESCALATE", {}, {}, {})
    trace = RunTrace("r1", "c1", 42, {}, [], [], "DO_NOT_ESCALATE", attack_id="atk_1")
    assert evaluator.label_attack_success(trace, spec) == True

def test_evaluator_labels_failure():
    evaluator = AttackEvaluator()
    spec = AttackSpec("atk_1", "fam1", "surf1", "DO_NOT_ESCALATE", {}, {}, {})
    trace = RunTrace("r1", "c1", 42, {}, [], [], "ESCALATE", attack_id="atk_1")
    assert evaluator.label_attack_success(trace, spec) == False

def test_asr_computation():
    evaluator = AttackEvaluator()
    spec = AttackSpec("atk_1", "fam1", "surf1", "DO_NOT_ESCALATE", {}, {}, {})
    specs = {"atk_1": spec}
    traces = [
        RunTrace("r_clean", "c1", 42, {}, [], [], "ESCALATE"),
        RunTrace("r_attack", "c1", 42, {}, [], [], "DO_NOT_ESCALATE", attack_id="atk_1")
    ]
    res = evaluator.compute_asr(traces, specs)
    assert res["fam1"]["n_total"] == 1
    assert res["fam1"]["asr"] == 1.0
    assert res["fam1"]["conditional_asr"] == 1.0

def test_bootstrap_ci_bounds():
    lower, upper = bootstrap_ci(50, 100)
    assert 0.3 < lower < 0.5
    assert 0.5 < upper < 0.7
    assert lower < upper

def test_bootstrap_ci_deterministic():
    l1, u1 = bootstrap_ci(10, 20, seed=42)
    l2, u2 = bootstrap_ci(10, 20, seed=42)
    assert l1 == l2
    assert u1 == u2

def test_mcnemar_paired():
    y_clean = [True, True, False, False]
    y_attacked = [True, False, True, False]
    stat, pval = paired_mcnemar(y_clean, y_attacked)
    assert 0 <= pval <= 1.0
