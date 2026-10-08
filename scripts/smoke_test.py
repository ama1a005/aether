#!/usr/bin/env python3
"""
smoke_test.sh equivalent — Python smoke test runner
Run: python scripts/smoke_test.py
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"SMOKE: {label}")
    print(f"CMD:   {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd, cwd=ROOT, capture_output=False)
    if result.returncode == 0:
        print(f"[PASS] {label}")
        return True
    else:
        print(f"[FAIL] {label} (exit code {result.returncode})")
        return False


def main():
    results = []

    # Unit tests
    results.append(run(
        [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        "Unit tests"
    ))

    # P3 smoke test
    results.append(run(
        [sys.executable, "-m", "experiments.phase1.single_agent_circuit_smoke"],
        "P3 single-agent circuit smoke"
    ))

    # P4 smoke test
    results.append(run(
        [sys.executable, "-m", "experiments.phase1.cross_agent_smoke"],
        "P4 cross-agent graph smoke"
    ))

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"SMOKE TEST SUMMARY: {passed}/{total} passed")
    if passed == total:
        print("ALL SMOKE TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME SMOKE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
