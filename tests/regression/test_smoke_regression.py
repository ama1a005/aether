"""tests/regression/test_smoke_regression.py
Regression tests that verify all four demo commands produce expected output.
These are the commands shown in the code review. If they break, the sprint
evidence is invalid.

Run: python -m pytest tests/regression/ -v
"""
import subprocess
import sys
import json
import os
import pytest

PYTHON = sys.executable
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_module(module: str, timeout: int = 120) -> tuple[int, str, str]:
    result = subprocess.run(
        [PYTHON, "-m", module],
        capture_output=True, text=True, timeout=timeout, cwd=ROOT,
    )
    return result.returncode, result.stdout, result.stderr


class TestDemoCommands:
    """Each method tests one of the four required review demo commands."""

    def test_p1_runner(self):
        """python -m target.runner --config configs/experiments/review_target.yaml"""
        result = subprocess.run(
            [PYTHON, "-m", "target.runner",
             "--config", "configs/experiments/review_target.yaml"],
            capture_output=True, text=True, timeout=60, cwd=ROOT,
        )
        assert result.returncode == 0, f"P1 runner failed:\n{result.stderr}"
        out = result.stdout
        assert "Clean Pass Rate" in out, "P1 missing clean pass rate in output"
        assert "Attack Success Rate" in out, "P1 missing attack success rate"

    def test_p2_runner(self):
        """python -m attacks.runner --config configs/experiments/review_attack.yaml"""
        result = subprocess.run(
            [PYTHON, "-m", "attacks.runner",
             "--config", "configs/experiments/review_attack.yaml"],
            capture_output=True, text=True, timeout=60, cwd=ROOT,
        )
        assert result.returncode == 0, f"P2 runner failed:\n{result.stderr}"
        out = result.stdout
        assert "ATTACK RUNNER COMPLETE" in out, "P2 missing completion message"
        assert "ASR" in out, "P2 missing ASR in output"

    def test_p3_smoke(self):
        """python -m experiments.phase1.single_agent_circuit_smoke"""
        code, out, err = run_module("experiments.phase1.single_agent_circuit_smoke")
        assert code == 0, f"P3 smoke failed:\n{err}"
        assert "P3 SMOKE TEST COMPLETE" in out, "P3 missing completion message"
        assert "PASS" in out, "P3 missing PASS verification"
        # Result files must exist
        assert os.path.exists(os.path.join(ROOT, "results/raw/p3_smoke_circuit_result.json"))
        assert os.path.exists(os.path.join(ROOT, "results/figures/p3_faithfulness_curve.png"))

    def test_p4_smoke(self):
        """python -m experiments.phase1.cross_agent_smoke"""
        code, out, err = run_module("experiments.phase1.cross_agent_smoke")
        assert code == 0, f"P4 smoke failed:\n{err}"
        assert "PASS" in out, "P4 missing PASS verification"
        # Result files must exist
        assert os.path.exists(os.path.join(ROOT, "results/raw/p4_smoke_circuit_result.json"))
        assert os.path.exists(os.path.join(ROOT, "results/figures/p4_graph.png"))

    def test_e2e_smoke(self):
        """python -m experiments.phase1.end_to_end_smoke"""
        code, out, err = run_module("experiments.phase1.end_to_end_smoke")
        assert code == 0, f"E2E smoke failed:\n{err}"
        assert "ALL CHECKS PASS" in out, "E2E missing ALL CHECKS PASS"
        assert os.path.exists(os.path.join(ROOT, "results/raw/e2e_smoke_summary.json"))

    def test_result_files_not_hardcoded(self):
        """Verify result JSON files contain real computed values (not placeholder zeros)."""
        p3_path = os.path.join(ROOT, "results/raw/p3_smoke_circuit_result.json")
        p4_path = os.path.join(ROOT, "results/raw/p4_smoke_circuit_result.json")
        e2e_path = os.path.join(ROOT, "results/raw/e2e_smoke_summary.json")

        for path in [p3_path, p4_path, e2e_path]:
            assert os.path.exists(path), f"Missing result file: {path}"
            with open(path) as f:
                data = json.load(f)
            # Must not be trivially empty
            assert data, f"Result file is empty: {path}"

        with open(p3_path) as f:
            p3 = json.load(f)
        assert p3.get("faithfulness", 0) > 0.5, \
            f"P3 faithfulness suspiciously low: {p3.get('faithfulness')}"

        with open(p4_path) as f:
            p4 = json.load(f)
        meta = p4.get("metadata", {})
        eval_m = meta.get("evaluation", {})
        assert eval_m.get("f1", 0) > 0.5, \
            f"P4 F1 suspiciously low: {eval_m.get('f1')}"
