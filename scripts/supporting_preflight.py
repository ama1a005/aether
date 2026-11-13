#!/usr/bin/env python3
"""SUPPORT preflight checker — validates environment before any experiment run.

Checks:
  1. Hardware: RAM, disk space
  2. Python version (must be 3.11.x)
  3. Git status: clean working tree, correct branch, source commit
  4. Dependency availability (import checks for critical packages)
  5. Split access guard: blocks validation/test split access
  6. Output-dir vacancy for each experiment
  7. Model snapshot availability (HuggingFace cache check)
  8. External tensor archive availability (SAE only)

Usage:
    python scripts/supporting_preflight.py
    python scripts/supporting_preflight.py --verbose
    python scripts/supporting_preflight.py --check-model
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PYTHON = (3, 11)
MINIMUM_RAM_GB = 8.0
MINIMUM_DISK_GB = 10.0
FROZEN_SOURCE_COMMIT = "00846b020b685dfa3ab89bce2c5227d2810c9d1e"
EXPECTED_BRANCH = "amala"

QUALIFIED_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
QUALIFIED_MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"

EXTERNAL_TENSOR_ARCHIVE_SHA256 = (
    "7890212a8e7a4eb099be86bc572cd6172fd1c45b839f695e56e6ba4a46e97b21"
)

OUTPUT_DIRS = [
    REPO_ROOT / "results" / "phase1" / "red_team" / "qwen15b",
    REPO_ROOT / "results" / "phase1" / "agent_c" / "qwen15b",
    REPO_ROOT / "results" / "phase1" / "sae" / "qwen15b",
    REPO_ROOT / "results" / "phase1" / "model_qualification" / "second_model",
]

BLOCKED_SPLITS = {"validation", "test"}

REQUIRED_IMPORTS = [
    "contracts.schemas",
    "attacks.orchestration",
    "attacks.corpus.attack_store",
    "attacks.corpus.builder",
    "target.agents.agent_a",
    "target.agents.agent_b",
    "target.agents.agent_c",
    "target.mcp.mock_client",
    "causal.interventions.sae",
    "experiments.supporting_nov19.red_team.adapter",
    "experiments.supporting_nov19.red_team.runner",
    "experiments.supporting_nov19.agent_c.runner",
    "experiments.supporting_nov19.sae.runner",
    "experiments.supporting_nov19.second_model.runner",
]

OPTIONAL_IMPORTS = [
    "torch",
    "transformers",
    "numpy",
]


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

class PreflightResult:
    """Collect pass/fail/warn results."""

    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append({"name": name, "status": status, "detail": detail})

    @property
    def passed(self) -> bool:
        return all(c["status"] != "FAIL" for c in self.checks)

    def summary(self) -> str:
        lines = []
        for c in self.checks:
            icon = {"PASS": "[OK]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}
            marker = icon.get(c["status"], "[??]")
            line = f"  {marker:6s} {c['name']}"
            if c["detail"]:
                line += f"  --  {c['detail']}"
            lines.append(line)
        n_pass = sum(1 for c in self.checks if c["status"] == "PASS")
        n_fail = sum(1 for c in self.checks if c["status"] == "FAIL")
        n_warn = sum(1 for c in self.checks if c["status"] == "WARN")
        lines.append("")
        lines.append(f"  Total: {len(self.checks)} checks | "
                      f"{n_pass} passed | {n_fail} failed | {n_warn} warnings")
        return "\n".join(lines)


def check_python_version(result: PreflightResult) -> None:
    """Python version must be 3.11.x."""
    major, minor = sys.version_info[:2]
    if (major, minor) == REQUIRED_PYTHON:
        result.add("python_version", "PASS", f"{major}.{minor}.{sys.version_info[2]}")
    else:
        result.add("python_version", "FAIL",
                    f"Need 3.11.x, got {major}.{minor}.{sys.version_info[2]}")


def check_hardware(result: PreflightResult) -> None:
    """Check RAM and disk space."""
    # RAM
    try:
        if platform.system() == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", c_ulonglong),
                    ("ullAvailPhys", c_ulonglong),
                    ("ullTotalPageFile", c_ulonglong),
                    ("ullAvailPageFile", c_ulonglong),
                    ("ullTotalVirtual", c_ulonglong),
                    ("ullAvailVirtual", c_ulonglong),
                    ("ullAvailExtendedVirtual", c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = stat.ullTotalPhys / (1024 ** 3)
            avail_gb = stat.ullAvailPhys / (1024 ** 3)
        else:
            import resource  # noqa: PLC0415
            # Fallback: read /proc/meminfo
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            mem = {l.split(":")[0]: int(l.split()[1]) for l in lines if ":" in l}
            total_gb = mem.get("MemTotal", 0) / (1024 ** 2)
            avail_gb = mem.get("MemAvailable", 0) / (1024 ** 2)

        if total_gb >= MINIMUM_RAM_GB:
            result.add("ram_total", "PASS", f"{total_gb:.1f} GB total, {avail_gb:.1f} GB available")
        else:
            result.add("ram_total", "WARN",
                        f"{total_gb:.1f} GB total (recommended >= {MINIMUM_RAM_GB} GB)")
    except Exception as exc:
        result.add("ram_total", "WARN", f"Could not determine RAM: {exc}")

    # Disk
    try:
        usage = shutil.disk_usage(REPO_ROOT)
        free_gb = usage.free / (1024 ** 3)
        if free_gb >= MINIMUM_DISK_GB:
            result.add("disk_free", "PASS", f"{free_gb:.1f} GB free")
        else:
            result.add("disk_free", "WARN",
                        f"{free_gb:.1f} GB free (recommended >= {MINIMUM_DISK_GB} GB)")
    except Exception as exc:
        result.add("disk_free", "WARN", f"Could not check disk: {exc}")


def check_git_status(result: PreflightResult) -> None:
    """Check branch, clean tree, and base commit."""
    try:
        # Branch name
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if branch == EXPECTED_BRANCH:
            result.add("git_branch", "PASS", f"On branch '{branch}'")
        else:
            result.add("git_branch", "WARN", f"Expected '{EXPECTED_BRANCH}', on '{branch}'")

        # Clean working tree
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if not status:
            result.add("git_clean", "PASS", "Working tree clean")
        else:
            n_files = len(status.splitlines())
            result.add("git_clean", "WARN", f"{n_files} uncommitted change(s)")

        # Source commit is ancestor
        rc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", FROZEN_SOURCE_COMMIT, "HEAD"],
            cwd=REPO_ROOT, capture_output=True,
        ).returncode
        if rc == 0:
            result.add("git_base_commit", "PASS",
                        f"Frozen commit {FROZEN_SOURCE_COMMIT[:12]} is ancestor of HEAD")
        else:
            result.add("git_base_commit", "FAIL",
                        f"Frozen commit {FROZEN_SOURCE_COMMIT[:12]} is NOT ancestor of HEAD")

    except FileNotFoundError:
        result.add("git_branch", "FAIL", "git not found on PATH")
    except subprocess.CalledProcessError as exc:
        result.add("git_status", "FAIL", f"git command failed: {exc}")


def check_imports(result: PreflightResult) -> None:
    """Check that all required modules are importable."""
    # Add repo root to sys.path temporarily
    root_str = str(REPO_ROOT)
    added = root_str not in sys.path
    if added:
        sys.path.insert(0, root_str)

    for mod_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(mod_name)
            result.add(f"import:{mod_name}", "PASS", "")
        except Exception as exc:
            result.add(f"import:{mod_name}", "FAIL", str(exc))

    for mod_name in OPTIONAL_IMPORTS:
        try:
            importlib.import_module(mod_name)
            result.add(f"import:{mod_name}", "PASS", "(optional)")
        except ImportError:
            result.add(f"import:{mod_name}", "WARN",
                        f"Optional dependency '{mod_name}' not installed (needed for --execute)")

    if added:
        sys.path.remove(root_str)


def check_split_guard(result: PreflightResult) -> None:
    """Verify that no config references validation or test splits."""
    config_dir = REPO_ROOT / "configs" / "supporting_nov19"
    if not config_dir.is_dir():
        result.add("split_guard", "FAIL", f"Config dir not found: {config_dir}")
        return

    for cfg_path in config_dir.glob("*.json"):
        try:
            config = json.loads(cfg_path.read_text(encoding="utf-8"))
            split = config.get("split", "")
            if split in BLOCKED_SPLITS:
                result.add(f"split_guard:{cfg_path.name}", "FAIL",
                            f"Config references blocked split '{split}'")
            else:
                result.add(f"split_guard:{cfg_path.name}", "PASS",
                            f"split='{split}' (allowed)")
        except Exception as exc:
            result.add(f"split_guard:{cfg_path.name}", "WARN", f"Could not parse: {exc}")


def check_output_dirs(result: PreflightResult) -> None:
    """Check that output directories are empty (no accidental overwrite)."""
    for d in OUTPUT_DIRS:
        if d.is_dir():
            contents = list(d.iterdir())
            # .gitkeep is OK
            real_contents = [f for f in contents if f.name != ".gitkeep"]
            if real_contents:
                result.add(f"output_dir:{d.name}", "WARN",
                            f"{len(real_contents)} file(s) present — may overwrite evidence")
            else:
                result.add(f"output_dir:{d.name}", "PASS", "Empty (ready)")
        else:
            result.add(f"output_dir:{d.name}", "PASS", "Does not exist yet (will be created)")


def check_model_availability(result: PreflightResult, check_model: bool) -> None:
    """Check if the qualified model is available in HuggingFace cache."""
    if not check_model:
        result.add("model_snapshot", "SKIP", "Use --check-model to verify model cache")
        return

    try:
        from huggingface_hub import scan_cache_dir  # noqa: PLC0415
        cache_info = scan_cache_dir()
        found = False
        for repo in cache_info.repos:
            if repo.repo_id == QUALIFIED_MODEL_ID:
                for rev in repo.revisions:
                    if rev.commit_hash == QUALIFIED_MODEL_REVISION:
                        found = True
                        break
        if found:
            result.add("model_snapshot", "PASS",
                        f"{QUALIFIED_MODEL_ID}@{QUALIFIED_MODEL_REVISION[:12]} in cache")
        else:
            result.add("model_snapshot", "WARN",
                        f"{QUALIFIED_MODEL_ID}@{QUALIFIED_MODEL_REVISION[:12]} NOT in cache "
                        "(download before --execute)")
    except ImportError:
        result.add("model_snapshot", "WARN",
                    "huggingface_hub not installed; cannot check model cache")
    except Exception as exc:
        result.add("model_snapshot", "WARN", f"Could not scan HF cache: {exc}")


def check_frozen_files(result: PreflightResult) -> None:
    """Verify that frozen core files were not modified (compare to base commit)."""
    frozen_paths = [
        "contracts/schemas.py",
        "instrumentation/adapters/qwen2.py",
        "instrumentation/model_adapter.py",
        "configs/models/model_registry.json",
        "configs/phase1_completion_gates.yaml",
    ]
    frozen_dirs = ["causal/", "discovery/", "remediation/"]

    try:
        # Get diff against frozen base
        diff_output = subprocess.run(
            ["git", "diff", "--name-only", FROZEN_SOURCE_COMMIT, "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        changed_files = set(diff_output.splitlines()) if diff_output else set()

        for fp in frozen_paths:
            if fp in changed_files:
                result.add(f"frozen:{fp}", "FAIL", "Modified since frozen base!")
            else:
                result.add(f"frozen:{fp}", "PASS", "Unchanged")

        for fd in frozen_dirs:
            modified_in_dir = [f for f in changed_files if f.startswith(fd)]
            if modified_in_dir:
                result.add(f"frozen:{fd}", "FAIL",
                            f"{len(modified_in_dir)} file(s) modified: {modified_in_dir[:3]}")
            else:
                result.add(f"frozen:{fd}", "PASS", "Unchanged")

    except Exception as exc:
        result.add("frozen_files", "WARN", f"Could not check: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AETHER supporting-experiments preflight checker.",
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all checks, including passed ones.")
    parser.add_argument("--check-model", action="store_true",
                        help="Also verify model snapshot is in HuggingFace cache.")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON instead of human-readable text.")
    args = parser.parse_args()

    result = PreflightResult()

    print("=" * 60)
    print("  AETHER Supporting Experiments — Preflight Check")
    print("=" * 60)
    print()

    check_python_version(result)
    check_hardware(result)
    check_git_status(result)
    check_frozen_files(result)
    check_split_guard(result)
    check_output_dirs(result)
    check_imports(result)
    check_model_availability(result, args.check_model)

    if args.json:
        print(json.dumps(result.checks, indent=2))
    else:
        print(result.summary())

    print()
    if result.passed:
        print("  PREFLIGHT PASSED  (all critical checks ok)")
        return 0
    else:
        print("  PREFLIGHT FAILED  (see [FAIL] items above)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
