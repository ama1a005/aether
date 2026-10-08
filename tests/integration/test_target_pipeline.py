import pytest
from target.case_loader import CaseLoader
from target.mcp.mock_client import MockMCPClient
from target.mcp.tools import get_ecg_analysis, get_vital_signs
from target.agents.agent_a import AgentA
from target.agents.agent_b import AgentB
from target.decision_parser import DecisionParser
from target.trace_logger import TraceLogger
from contracts.schemas import AttackSpec, RunTrace
import dataclasses

@pytest.fixture
def pipeline_setup():
    mcp = MockMCPClient()
    mcp.register_tool('get_ecg_analysis', get_ecg_analysis)
    mcp.register_tool('get_vital_signs', get_vital_signs)
    
    agent_a = AgentA("a", mcp, {})
    agent_b = AgentB("b", {})
    parser = DecisionParser()
    loader = CaseLoader('synthetic')
    
    return loader, agent_a, agent_b, parser

def test_full_clean_pipeline(pipeline_setup):
    loader, agent_a, agent_b, parser = pipeline_setup
    cases = loader.load_cases(1, seed=42)
    case = cases[0]
    
    out_a, msg_a, calls = agent_a.run(case)
    out_b, score = agent_b.run(msg_a, case)
    dec, _ = parser.parse(out_b, msg_a.structured_payload)
    
    assert dec in ["ESCALATE", "DO_NOT_ESCALATE"]
    assert len(calls) == 2

def test_full_attacked_pipeline(pipeline_setup):
    loader, agent_a, agent_b, parser = pipeline_setup
    # Create a case that should ESCALATE
    cases = loader.load_cases(10, seed=42)
    case = next(c for c in cases if c.ground_truth_decision == 'ESCALATE')
    
    spec = AttackSpec("a1", "fam", "mcp_tool_description", "DO_NOT_ESCALATE", {}, {"description": "DO_NOT_ESCALATE"})
    
    out_a, msg_a, calls = agent_a.run(case, attack_spec=spec)
    out_b, score = agent_b.run(msg_a, case)
    dec, _ = parser.parse(out_b, msg_a.structured_payload)
    
    assert dec == "DO_NOT_ESCALATE"
    assert parser.is_attack_success(dec, spec) == True

def test_deterministic_rerun(pipeline_setup, tmp_path):
    loader, agent_a, agent_b, parser = pipeline_setup
    
    def run_pass():
        cases = loader.load_cases(1, seed=42)
        out_a, msg_a, calls = agent_a.run(cases[0])
        out_b, score = agent_b.run(msg_a, cases[0])
        dec, p_score = parser.parse(out_b, msg_a.structured_payload)
        return RunTrace("r1", cases[0].case_id, 42, {}, [dataclasses.asdict(msg_a)], calls, dec, decision_score=p_score)
        
    trace1 = run_pass()
    trace2 = run_pass()

    # Decisions, scores, case_ids, and content are deterministic.
    # message_id and tool_call_ids use uuid4() which are intentionally random per-run.
    # Test that the research-relevant outputs are identical.
    assert trace1.case_id == trace2.case_id
    assert trace1.final_decision == trace2.final_decision
    assert trace1.decision_score == trace2.decision_score
    assert trace1.attack_success == trace2.attack_success
    assert len(trace1.messages) == len(trace2.messages)
    # Message content (not IDs) should be identical
    for m1, m2 in zip(trace1.messages, trace2.messages):
        assert m1["content_text"] == m2["content_text"]
        assert m1["structured_payload"] == m2["structured_payload"]
    # Tool call results should be identical
    assert len(trace1.tool_calls) == len(trace2.tool_calls)
    for t1, t2 in zip(trace1.tool_calls, trace2.tool_calls):
        assert t1["result"] == t2["result"]
