import pytest
import os
import json
from target.case_loader import CaseLoader
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_ecg_analysis
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.decision_parser import DecisionParser
from target.trace_logger import TraceLogger
from contracts.schemas import AttackSpec, PatientCase, A2AMessageRecord, RunTrace

def test_case_loader_synthetic():
    loader = CaseLoader('synthetic')
    cases = loader.load_cases(5, seed=42)
    assert len(cases) == 5
    for c in cases:
        assert isinstance(c, PatientCase)
        assert c.source_dataset == 'synthetic'
        assert c.ground_truth_decision in ['ESCALATE', 'DO_NOT_ESCALATE']
        assert 'heart_rate' in c.features


def test_case_loader_fails_closed_and_preserves_rng(tmp_path):
    import random
    state = random.getstate()
    CaseLoader('synthetic').load_cases(3, seed=42)
    assert state == random.getstate()
    with pytest.raises(FileNotFoundError):
        CaseLoader('fixture', str(tmp_path)).load_cases(1, seed=42)
    with pytest.raises(ValueError, match="Unsupported"):
        CaseLoader('typo')
    with pytest.raises(ValueError, match="count"):
        CaseLoader('synthetic').load_cases(-1, seed=42)

def test_case_loader_fixture(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    fixture_file = fixture_dir / "patient_case.json"
    
    mock_case = {
        "case_id": "test_001",
        "features": {"heart_rate": 70},
        "ground_truth_decision": "DO_NOT_ESCALATE",
        "source_dataset": "fixture",
        "source_split": "fixture",
        "metadata": {}
    }
    fixture_file.write_text(json.dumps(mock_case))
    
    loader = CaseLoader('fixture', fixture_dir=str(fixture_dir))
    cases = loader.load_cases(1, seed=42)
    assert len(cases) == 1
    assert cases[0].case_id == "test_001_0"

def test_case_loader_deterministic():
    loader = CaseLoader('synthetic')
    cases1 = loader.load_cases(3, seed=42)
    cases2 = loader.load_cases(3, seed=42)
    for c1, c2 in zip(cases1, cases2):
        assert c1.features == c2.features

def test_mock_mcp_clean():
    client = MockMCPClient({"test_tool": lambda x: {"result": x*2}})
    res = client.call_tool("test_tool", {"x": 5})
    assert res == {"result": 10}

def test_mock_mcp_poison_description():
    client = MockMCPClient({"test_tool": lambda x: {"result": x*2}})
    spec = AttackSpec("a1", "tool_description_poison", "mcp_tool_description", "DO_NOT_ESCALATE", {}, {"description": "POISON"})
    res = client.call_tool("test_tool", {"x": 5}, poisoned=True, poison_spec=spec)
    # _poison_context now includes [OVERRIDE:<target_behavior>] for machine-detectable parsing
    assert res["result"] == 10
    assert "POISON" in res["_poison_context"]
    assert "[OVERRIDE:DO_NOT_ESCALATE]" in res["_poison_context"]

def test_mock_mcp_poison_output():
    client = MockMCPClient({"test_tool": lambda x: {"result": x*2}})
    spec = AttackSpec("a1", "tool_output_inject", "mcp_tool_output", "DO_NOT_ESCALATE", {}, {"result": "POISONED_RES"})
    res = client.call_tool("test_tool", {"x": 5}, poisoned=True, poison_spec=spec)
    assert res == "POISONED_RES"

def test_agent_a_clean_run():
    client = MockMCPClient({"get_ecg_analysis": lambda **k: {"risk_level": "LOW"}, "get_vital_signs": lambda **k: {}})
    agent = AgentA("model_a", client, {})
    case = PatientCase("c1", {}, "DO_NOT_ESCALATE")
    out_text, msg, calls = agent.run(case)
    
    assert isinstance(msg, A2AMessageRecord)
    assert msg.sender == "model_a"
    assert "LOW" in msg.structured_payload["risk_level"]
    assert len(calls) == 2

def test_agent_b_clean_escalate():
    agent = AgentB("model_b", {})
    msg = A2AMessageRecord("m1", "r1", "a", "b", "test", structured_payload={"risk_level": "CRITICAL"})
    case = PatientCase("c1", {}, "ESCALATE")
    dec, score = agent.run(msg, case)
    assert dec == "ESCALATE"
    assert score > 0

def test_agent_b_clean_no_escalate():
    agent = AgentB("model_b", {})
    msg = A2AMessageRecord("m1", "r1", "a", "b", "test", structured_payload={"risk_level": "LOW"})
    case = PatientCase("c1", {}, "DO_NOT_ESCALATE")
    dec, score = agent.run(msg, case)
    assert dec == "DO_NOT_ESCALATE"
    assert score < 0

def test_agent_b_attack_success():
    agent = AgentB("model_b", {})
    msg = A2AMessageRecord("m1", "r1", "a", "b", "test", structured_payload={"risk_level": "CRITICAL", "_poison_influence": "DO_NOT_ESCALATE"})
    case = PatientCase("c1", {}, "ESCALATE")
    dec, score = agent.run(msg, case)
    assert dec == "DO_NOT_ESCALATE"
    assert score < 0

def test_decision_parser_structured():
    parser = DecisionParser()
    dec, score = parser.parse("text doesn't matter", {"risk_level": "CRITICAL"})
    assert dec == "ESCALATE"
    assert score > 0

def test_decision_parser_text():
    parser = DecisionParser()
    dec, score = parser.parse("ESCALATE because of reasons", None)
    assert dec == "ESCALATE"
    assert score > 0
    
    dec, score = parser.parse("DO NOT ESCALATE", None)
    assert dec == "DO_NOT_ESCALATE"
    assert score < 0

def test_attack_success_detection():
    parser = DecisionParser()
    spec = AttackSpec("a1", "fam", "surf", "DO_NOT_ESCALATE", {}, {})
    assert parser.is_attack_success("DO_NOT_ESCALATE", spec) == True
    assert parser.is_attack_success("ESCALATE", spec) == False

def test_trace_logger_roundtrip(tmp_path):
    logger = TraceLogger(str(tmp_path))
    trace = RunTrace("r1", "c1", 42, {"a":"1","b":"2"}, [], [], "ESCALATE")
    logger.log(trace)
    loaded = logger.load("r1")
    assert loaded.run_id == "r1"
    assert loaded.case_id == "c1"

def test_runner_produces_csv(tmp_path):
    # Create mock config
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
case_source:
  type: synthetic
n_cases: 2
seed: 42
output:
  trace_dir: {}
""".format(str(tmp_path).replace('\\', '/')))
    
    import subprocess
    import sys
    
    subprocess.run([sys.executable, "-m", "target.runner", "--config", str(config_path)], check=True)
    
    assert (tmp_path / "p1_review_target_results.csv").exists()
