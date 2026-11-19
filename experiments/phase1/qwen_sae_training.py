"""Approved dual-GPU Qwen SAE capture and training primitives.

The CLI is deliberately phase-oriented so every corpus block and training epoch
can be persisted remotely by the Kaggle orchestration notebook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
from typing import Any, Iterable

import numpy as np
import torch
from torch import nn

from causal.interventions.sae import SAEProvenance, write_sae_metadata
from causal.interventions.sae import load_sae_checkpoint
from experiments.phase1.sae_training_freeze import (
    load_and_validate_amendment,
    load_and_validate_v1_2_amendment,
    load_and_validate_v1_3_amendment,
    verify_human_decision,
)
from instrumentation.adapters import Qwen2ModelAdapter


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "configs/experiments/qwen_sae_training_freeze_v1.json"
AMENDMENT = ROOT / "configs/experiments/qwen_sae_training_freeze_v1_1_amendment.json"
AMENDMENT_V1_2 = ROOT / "configs/experiments/qwen_sae_training_freeze_v1_2_amendment.json"
BASE_DECISION = ROOT / "results/phase1/sae_training_freeze/decision.json"
AMENDMENT_DECISION = ROOT / "results/phase1/sae_training_freeze/amendment_decision.json"
AMENDMENT_V1_2_DECISION = ROOT / "results/phase1/sae_training_freeze/v1_2_amendment_decision.json"
AMENDMENT_V1_3 = ROOT / "configs/experiments/qwen_sae_training_freeze_v1_3_amendment.json"
AMENDMENT_V1_3_DECISION = ROOT / "results/phase1/sae_training_freeze/v1_3_amendment_decision.json"


class NoEligibleSeed(RuntimeError):
    """All frozen seeds completed without an eligible checkpoint."""


def sha256_file(path: Path) -> str:
    """Return the streaming SHA-256 of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the approved chain and return the effective v1.3 amendment."""
    base = json.loads(BASE.read_text(encoding="utf-8"))
    verify_human_decision(BASE, BASE_DECISION)
    amendment = load_and_validate_amendment(AMENDMENT, BASE)
    decision = json.loads(AMENDMENT_DECISION.read_text(encoding="utf-8"))
    if decision.get("decision") != "APPROVED":
        raise PermissionError("SAE v1.1 is not approved")
    if decision.get("proposal_sha256") != sha256_file(AMENDMENT):
        raise PermissionError("SAE v1.1 approval hash mismatch")
    if decision.get("reviewer_role") != "human_project_owner":
        raise PermissionError("SAE v1.1 lacks a human project owner")
    correction = load_and_validate_v1_2_amendment(AMENDMENT_V1_2, AMENDMENT, BASE)
    v1_2_decision = json.loads(AMENDMENT_V1_2_DECISION.read_text(encoding="utf-8"))
    if v1_2_decision.get("decision") != "APPROVED":
        raise PermissionError("SAE v1.2 is not approved")
    if v1_2_decision.get("proposal_sha256") != sha256_file(AMENDMENT_V1_2):
        raise PermissionError("SAE v1.2 approval hash mismatch")
    if v1_2_decision.get("reviewer_role") != "human_project_owner":
        raise PermissionError("SAE v1.2 lacks a human project owner")
    load_and_validate_v1_3_amendment(
        AMENDMENT_V1_3, AMENDMENT_V1_2, AMENDMENT, BASE
    )
    v1_3_decision = json.loads(AMENDMENT_V1_3_DECISION.read_text(encoding="utf-8"))
    if v1_3_decision.get("decision") != "APPROVED":
        raise PermissionError("SAE v1.3 is not approved")
    if v1_3_decision.get("proposal_sha256") != sha256_file(AMENDMENT_V1_3):
        raise PermissionError("SAE v1.3 approval hash mismatch")
    if v1_3_decision.get("reviewer_role") != "human_project_owner":
        raise PermissionError("SAE v1.3 lacks a human project owner")
    effective = json.loads(json.dumps(amendment))
    effective["training_corpus"].update(correction["correction"])
    return base, effective


def select_corpus_tokens(
    texts: Iterable[str], tokenizer: Any, *, selected_token_count: int
) -> np.ndarray:
    """Apply the frozen ordered WikiText selection and EOS separation rule."""
    if selected_token_count < 1:
        raise ValueError("selected_token_count must be positive")
    eos = tokenizer.eos_token_id
    if not isinstance(eos, int) or eos < 0:
        raise ValueError("pinned tokenizer lacks an EOS token ID")
    selected: list[int] = []
    for raw in texts:
        if not isinstance(raw, str):
            raise TypeError("corpus text rows must be strings")
        text = raw.strip()
        if not text:
            continue
        tokens = tokenizer.encode(text, add_special_tokens=False)
        if not isinstance(tokens, list) or any(not isinstance(value, int) for value in tokens):
            raise TypeError("tokenizer returned invalid token IDs")
        selected.extend(tokens)
        selected.append(eos)
        if len(selected) >= selected_token_count:
            return np.asarray(selected[:selected_token_count], dtype=np.int64)
    raise ValueError("pinned corpus did not provide the frozen token count")


def write_token_artifacts(
    texts: Iterable[str], tokenizer: Any, output: Path, source_files: list[Path]
) -> Path:
    """Write exact token IDs and a hash-complete corpus source manifest."""
    _base, amendment = authorization()
    corpus = amendment["training_corpus"]
    expected_source_hash = corpus["source_file_sha256"]
    for source_file in source_files:
        observed = sha256_file(source_file)
        if observed != expected_source_hash:
            raise ValueError(f"WikiText parquet SHA-256 mismatch: {observed}")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    tokens = select_corpus_tokens(
        texts, tokenizer, selected_token_count=corpus["selected_token_count"]
    )
    token_path = output / "corpus_token_ids.npy"
    np.save(token_path, tokens, allow_pickle=False)
    (output / "corpus_token_ids.sha256").write_text(
        sha256_file(token_path) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "aether.sae-corpus-source.v1",
        "dataset": {key: corpus[key] for key in (
            "dataset_id", "dataset_revision", "dataset_config", "source_split",
            "selection_order", "empty_row_policy", "tokenization",
        )},
        "selected_token_count": int(tokens.size),
        "token_ids_sha256": sha256_file(token_path),
        "source_files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(source_files)
        ],
        "validation_executions": 0,
        "test_executions": 0,
    }
    destination = output / "corpus_source_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def capture_corpus_shard(
    token_path: Path,
    output: Path,
    snapshot: Path,
    cache: Path,
    *,
    shard_index: int,
    shard_count: int,
    device: str,
) -> dict[str, Any]:
    """Capture disjoint 256-token layer-22 blocks on one GPU."""
    base, amendment = authorization()
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("invalid capture shard")
    if snapshot.name != base["model_revision"]:
        raise ValueError("model snapshot revision mismatch")
    tokens = np.load(token_path, allow_pickle=False)
    sequence_length = amendment["training_corpus"]["sequence_length"]
    expected = amendment["training_corpus"]["selected_token_count"]
    if tokens.dtype != np.int64 or tokens.shape != (expected,):
        raise ValueError("corpus token artifact shape or dtype mismatch")
    block_count = expected // sequence_length
    output.mkdir(parents=True, exist_ok=True)
    adapter = Qwen2ModelAdapter(
        base["model_id"], base["model_revision"], cache,
        dtype=torch.float32, device=device, local_files_only=True,
    )
    adapter.load()
    site = next(
        site for site in adapter.identify_components([22])
        if site.component_type == "attention_output"
    )
    completed = 0
    for block in range(shard_index, block_count, shard_count):
        destination = output / f"block_{block:04d}.npy"
        if destination.is_file():
            existing = np.load(destination, allow_pickle=False, mmap_mode="r")
            if existing.shape != (sequence_length, base["hidden_width"]):
                raise ValueError(f"existing capture block has wrong shape: {destination}")
            completed += 1
            continue
        block_ids = tokens[block * sequence_length:(block + 1) * sequence_length]
        inputs = {
            "input_ids": torch.from_numpy(block_ids.copy()).view(1, -1).to(device),
            "attention_mask": torch.ones((1, sequence_length), dtype=torch.long, device=device),
        }
        try:
            adapter.install_capture_hooks([site])
            adapter.forward(inputs)
            activation = adapter.activations[site.component_id].squeeze(0).numpy()
        finally:
            adapter.remove_hooks()
        if activation.shape != (sequence_length, base["hidden_width"]):
            raise ValueError("captured corpus activation shape mismatch")
        temporary = destination.with_suffix(".tmp.npy")
        np.save(temporary, activation.astype(np.float32, copy=False), allow_pickle=False)
        temporary.replace(destination)
        completed += 1
        print(json.dumps({"event": "capture_block", "shard": shard_index,
                          "block": block, "sha256": sha256_file(destination)}), flush=True)
    return {"shard": shard_index, "completed": completed, "block_count": block_count}


class TorchSAE(nn.Module):
    """The frozen linear ReLU sparse autoencoder."""

    def __init__(self, input_dim: int, latent_dim: int) -> None:
        super().__init__()
        self.encoder = nn.Linear(input_dim, latent_dim)
        self.decoder = nn.Linear(latent_dim, input_dim)

    def forward(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return reconstruction and nonnegative latent features."""
        features = torch.relu(self.encoder(values))
        return self.decoder(features), features


def _metrics(model: TorchSAE, values: torch.Tensor, batch_size: int) -> dict[str, float]:
    squared_error = 0.0
    squared_input = 0.0
    active = 0
    feature_count = 0
    with torch.inference_mode():
        for batch in values.split(batch_size):
            reconstructed, features = model(batch)
            squared_error += float(torch.square(reconstructed - batch).sum().item())
            squared_input += float(torch.square(batch).sum().item())
            active += int((features != 0).sum().item())
            feature_count += features.numel()
    relative = (squared_error / max(squared_input, 1e-24)) ** 0.5
    return {"relative_reconstruction_error": relative,
            "active_fraction": active / feature_count}


def train_seed(
    activation_dir: Path,
    output: Path,
    *,
    seed: int,
    device: str,
) -> dict[str, Any]:
    """Train or resume one frozen seed and checkpoint after every epoch."""
    base, amendment = authorization()
    optimization = base["optimization"]
    if seed not in optimization["seeds"]:
        raise ValueError("seed is not frozen")
    files = sorted(activation_dir.glob("block_*.npy"))
    expected_blocks = amendment["training_corpus"]["selected_token_count"] // amendment["training_corpus"]["sequence_length"]
    if len(files) != expected_blocks:
        raise ValueError(f"expected {expected_blocks} corpus blocks, found {len(files)}")
    matrix = np.concatenate([np.load(path, allow_pickle=False) for path in files], axis=0)
    if matrix.shape != (65536, base["hidden_width"]):
        raise ValueError("corpus activation matrix shape mismatch")
    train_count = amendment["training_corpus"]["training_token_count"]
    train_np, selection_np = matrix[:train_count], matrix[train_count:]
    mean = train_np.mean(axis=0, dtype=np.float64).astype(np.float32)
    scale = train_np.std(axis=0, dtype=np.float64).astype(np.float32)
    scale = np.maximum(scale, 1e-8)
    train = torch.from_numpy((train_np - mean) / scale).to(device)
    selection = torch.from_numpy((selection_np - mean) / scale).to(device)
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
    model = TorchSAE(base["hidden_width"], base["architecture"]["latent_dim"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=optimization["learning_rate"])
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "training_checkpoint.pt"
    history_path = output / "training_history.jsonl"
    start_epoch, best, stale = 0, None, 0
    if checkpoint.is_file():
        state = torch.load(checkpoint, map_location=device, weights_only=True)
        model.load_state_dict(state["model"]); optimizer.load_state_dict(state["optimizer"])
        start_epoch = int(state["epoch"]); best = state["best"]; stale = int(state["stale"])
        history = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]
        if (len(history) != start_epoch
                or [row.get("epoch") for row in history] != list(range(1, start_epoch + 1))
                or any(row.get("seed") != seed for row in history)):
            raise ValueError("SAE retained checkpoint and history prefix differ")
        if best is None:
            stale = 0
    generator = torch.Generator(device="cpu").manual_seed(seed + start_epoch)
    batch_size = optimization["batch_size"]
    bounds = base["selection"]
    for epoch in range(start_epoch, optimization["maximum_epochs"]):
        permutation = torch.randperm(train.shape[0], generator=generator)
        model.train()
        total = 0.0
        for indices in permutation.split(batch_size):
            batch = train[indices.to(device)]
            optimizer.zero_grad(set_to_none=True)
            reconstructed, features = model(batch)
            loss = torch.mean(torch.square(reconstructed - batch))
            loss = loss + optimization["l1_coefficient"] * torch.mean(torch.abs(features))
            loss.backward(); optimizer.step(); total += float(loss.detach().item())
        model.eval(); metrics = _metrics(model, selection, batch_size)
        eligible = bounds["minimum_active_fraction"] <= metrics["active_fraction"] <= bounds["maximum_active_fraction"]
        score = metrics["relative_reconstruction_error"]
        if eligible and (best is None or score < best["relative_reconstruction_error"]):
            best = {**metrics, "epoch": epoch + 1, "state": {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }}
            stale = 0
        elif best is not None:
            stale += 1
        row = {"seed": seed, "epoch": epoch + 1, "mean_training_loss": total / len(permutation.split(batch_size)),
               **metrics, "eligible": eligible}
        with history_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush(); os.fsync(stream.fileno())
        temporary = checkpoint.with_suffix(".tmp")
        torch.save({"epoch": epoch + 1, "seed": seed,
                    "protocol_sha256": sha256_file(AMENDMENT_V1_3),
                    "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "best": best, "stale": stale}, temporary)
        temporary.replace(checkpoint)
        print(json.dumps({"event": "training_epoch", **row}), flush=True)
        if best is not None and stale >= optimization["early_stopping_patience"]:
            break
    if best is None:
        summary = {"schema_version": "aether.sae-seed-result.v1", "seed": seed,
                   "scientific_outcome": "SAE_SEED_REJECTED_NO_ELIGIBLE_CHECKPOINT",
                   "best_selection": None, "epochs_completed": epoch + 1,
                   "validation_executions": 0, "test_executions": 0}
        (output / "seed_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return summary
    best_state = best["state"]
    model.load_state_dict(best_state)
    weights = output / "weights.npz"
    np.savez(
        weights,
        encoder_weight=model.encoder.weight.detach().cpu().numpy().astype(np.float32),
        encoder_bias=model.encoder.bias.detach().cpu().numpy().astype(np.float32),
        decoder_weight=model.decoder.weight.detach().cpu().numpy().astype(np.float32),
        decoder_bias=model.decoder.bias.detach().cpu().numpy().astype(np.float32),
        mean=mean,
        scale=scale,
    )
    provenance = SAEProvenance(
        schema_version=1, sae_id=f"qwen15b-l22-seed{seed}", model_id=base["model_id"],
        model_revision=base["model_revision"], component_id=base["component_id"],
        input_dim=base["hidden_width"], latent_dim=base["architecture"]["latent_dim"],
        activation="relu", normalization="feature_standardization",
        max_relative_reconstruction_error=base["acceptance"]["maximum_relative_reconstruction_error"],
        training_dataset_hash=hashlib.sha256(matrix[:train_count].tobytes()).hexdigest(),
        training_seed=seed, weights_sha256=sha256_file(weights),
    )
    write_sae_metadata(output / "metadata.json", provenance)
    best_summary = {key: value for key, value in best.items() if key != "state"}
    summary = {"schema_version": "aether.sae-seed-result.v1", "seed": seed,
               "scientific_outcome": "SAE_SEED_ELIGIBLE",
               "best_selection": best_summary, "epochs_completed": epoch + 1,
               "validation_executions": 0, "test_executions": 0}
    (output / "seed_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def select_seed(seed_root: Path) -> Path:
    """Select the frozen lowest-error seed with deterministic seed tie-break."""
    candidates: list[tuple[float, int, Path]] = []
    observed_seeds: set[int] = set()
    for path in sorted(seed_root.glob("seed-*/seed_summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("validation_executions") != 0 or summary.get("test_executions") != 0:
            raise PermissionError("SAE seed result accessed a protected split")
        seed = summary.get("seed")
        if not isinstance(seed, int):
            raise ValueError("invalid SAE seed summary")
        observed_seeds.add(seed)
        if summary.get("scientific_outcome") == "SAE_SEED_REJECTED_NO_ELIGIBLE_CHECKPOINT":
            continue
        error = (summary.get("best_selection") or {}).get("relative_reconstruction_error")
        if summary.get("scientific_outcome") != "SAE_SEED_ELIGIBLE" or not isinstance(error, (int, float)):
            raise ValueError("invalid SAE seed summary")
        candidates.append((float(error), seed, path.parent))
    if observed_seeds != {11, 22, 33}:
        raise ValueError("all three frozen SAE seeds are required")
    if not candidates:
        raise NoEligibleSeed("all frozen SAE seeds were sparsity-ineligible")
    return min(candidates, key=lambda item: (item[0], item[1]))[2]


def finalize_rejected_seeds(seed_root: Path, output: Path) -> Path:
    """Retain a complete negative result when all three seeds are ineligible."""
    try:
        select_seed(seed_root)
    except NoEligibleSeed:
        output.mkdir(parents=True, exist_ok=False)
        summaries = [json.loads((seed_root / f"seed-{seed}/seed_summary.json").read_text(encoding="utf-8"))
                     for seed in (11, 22, 33)]
        result = {"schema_version": "aether.qwen-sae-result.v1", "overall": "FAIL",
                  "scientific_outcome": "SAE_REJECTED_NO_ELIGIBLE_SEED",
                  "selected_seed": None, "seed_summaries": summaries,
                  "validation_executions": 0, "test_executions": 0,
                  "claim_boundary": json.loads(BASE.read_text(encoding="utf-8"))["claim_boundary"]}
        destination = output / "summary.json"
        destination.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        bundle_root = output.parent
        inventory = {path.relative_to(bundle_root).as_posix(): sha256_file(path)
                     for path in sorted(bundle_root.rglob("*"))
                     if path.is_file() and path.name != "archive_contents.json"}
        (bundle_root / "archive_contents.json").write_text(
            json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")
        return destination
    raise ValueError("at least one eligible seed exists; capture and evaluate the audit")


def capture_aether_audit(
    output: Path, snapshot: Path, cache: Path, *, device: str
) -> Path:
    """Capture unchanged four-case AETHER audit only after seed selection."""
    base, amendment = authorization()
    if output.exists():
        raise FileExistsError(output)
    if snapshot.name != base["model_revision"]:
        raise ValueError("model snapshot revision mismatch")
    from instrumentation.run_qwen_development_capture import _load_inputs, _prompt

    capture_config, rows = _load_inputs()
    audit_ids = set(amendment["aether_final_audit"]["case_ids"])
    selected_rows = [row for row in rows if row["case_id"] in audit_ids]
    if {row["case_id"] for row in selected_rows} != audit_ids:
        raise ValueError("development capture registry lacks a frozen SAE audit case")
    adapter = Qwen2ModelAdapter(
        base["model_id"], base["model_revision"], cache,
        dtype=torch.float32, device=device, local_files_only=True,
    )
    adapter.load()
    site = next(site for site in adapter.identify_components([22])
                if site.component_type == "attention_output")
    pad_id = adapter.tokenizer.pad_token_id
    if pad_id is None:
        raise ValueError("pinned tokenizer lacks a pad token")
    output.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    for row in selected_rows:
        for condition in amendment["aether_final_audit"]["conditions"]:
            _text, token_ids = _prompt(row, "receiver", condition)
            first_content = 0
            while first_content < len(token_ids) and token_ids[first_content] == pad_id:
                first_content += 1
            mask = [0] * first_content + [1] * (len(token_ids) - first_content)
            inputs = {
                "input_ids": torch.tensor([token_ids], dtype=torch.long, device=device),
                "attention_mask": torch.tensor([mask], dtype=torch.long, device=device),
            }
            try:
                adapter.install_capture_hooks([site]); adapter.forward(inputs)
                full = adapter.activations[site.component_id].squeeze(0)
            finally:
                adapter.remove_hooks()
            activation = full[torch.tensor(mask, dtype=torch.bool)].numpy().astype(np.float32)
            destination = output / f"{row['case_id']}_{condition}.npy"
            np.save(destination, activation, allow_pickle=False)
            records.append({"case_id": row["case_id"], "condition": condition,
                            "shape": list(activation.shape), "sha256": sha256_file(destination)})
    manifest = {
        "schema_version": "aether.sae-aether-audit-activations.v1",
        "model_id": base["model_id"], "model_revision": base["model_revision"],
        "component_id": base["component_id"], "records": records,
        "validation_executions": 0, "test_executions": 0,
    }
    destination = output / "aether_audit_activation_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def evaluate_aether_audit(seed_root: Path, audit_root: Path, output: Path) -> Path:
    """Apply the frozen acceptance metrics to the preselected SAE exactly once."""
    base, _amendment = authorization()
    selected = select_seed(seed_root)
    codec = load_sae_checkpoint(
        selected, expected_model_id=base["model_id"],
        expected_model_revision=base["model_revision"],
        expected_component_id=base["component_id"],
    )
    rows: list[dict[str, Any]] = []
    all_features: list[torch.Tensor] = []
    audit_values: list[torch.Tensor] = []
    for path in sorted(audit_root.glob("v2_case_*_*.npy")):
        values = torch.from_numpy(np.load(path, allow_pickle=False))
        error = codec.relative_reconstruction_error(values)
        features = codec.encode(values)
        all_features.append(features); audit_values.append(values)
        rows.append({"artifact": path.name, "row_count": values.shape[0],
                     "relative_reconstruction_error": error,
                     "active_fraction": float((features != 0).float().mean().item())})
    if len(rows) != 8:
        raise ValueError("SAE AETHER audit requires eight case-condition artifacts")
    features = torch.cat(all_features)
    dead_fraction = float((features.abs().sum(dim=0) == 0).float().mean().item())
    values = torch.cat(audit_values)
    mean = values.mean(dim=0, keepdim=True)
    mean_error = float((torch.square(values - mean).sum() /
                        torch.square(values).sum().clamp_min(1e-24)).sqrt().item())
    maximum = max(row["relative_reconstruction_error"] for row in rows)
    acceptance = base["acceptance"]
    predicates = {
        "reconstruction": maximum <= acceptance["maximum_relative_reconstruction_error"],
        "dead_features": dead_fraction <= acceptance["maximum_dead_feature_fraction"],
        "mean_baseline": maximum < mean_error,
        "finite": all(np.isfinite(value) for value in (maximum, dead_fraction, mean_error)),
    }
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "schema_version": "aether.qwen-sae-result.v1",
        "overall": "PASS" if all(predicates.values()) else "FAIL",
        "scientific_outcome": "SAE_ACCEPTED" if all(predicates.values()) else "SAE_REJECTED",
        "selected_seed": codec.provenance.training_seed,
        "selected_sae_id": codec.provenance.sae_id,
        "maximum_relative_reconstruction_error": maximum,
        "mean_vector_relative_reconstruction_error": mean_error,
        "dead_feature_fraction": dead_fraction,
        "predicates": predicates, "rows": rows,
        "validation_executions": 0, "test_executions": 0,
        "claim_boundary": base["claim_boundary"],
    }
    destination = output / "summary.json"
    destination.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    bundle_root = output.parent
    inventory = {path.relative_to(bundle_root).as_posix(): sha256_file(path)
                 for path in sorted(bundle_root.rglob("*"))
                 if path.is_file() and path.name != "archive_contents.json"}
    (bundle_root / "archive_contents.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8"
    )
    return destination


def main() -> None:
    """Execute one restart-safe phase of the approved package."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture-corpus")
    capture.add_argument("--tokens", type=Path, required=True); capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--snapshot", type=Path, required=True); capture.add_argument("--cache", type=Path, required=True)
    capture.add_argument("--shard-index", type=int, required=True); capture.add_argument("--shard-count", type=int, required=True)
    capture.add_argument("--device", required=True)
    train = sub.add_parser("train-seed")
    train.add_argument("--activations", type=Path, required=True); train.add_argument("--output", type=Path, required=True)
    train.add_argument("--seed", type=int, required=True); train.add_argument("--device", required=True)
    audit = sub.add_parser("capture-audit")
    audit.add_argument("--output", type=Path, required=True); audit.add_argument("--snapshot", type=Path, required=True)
    audit.add_argument("--cache", type=Path, required=True); audit.add_argument("--device", required=True)
    evaluate = sub.add_parser("evaluate-audit")
    evaluate.add_argument("--seeds", type=Path, required=True); evaluate.add_argument("--audit", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    reject = sub.add_parser("finalize-rejected-seeds")
    reject.add_argument("--seeds", type=Path, required=True); reject.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture-corpus":
        result = capture_corpus_shard(args.tokens, args.output, args.snapshot, args.cache,
                                      shard_index=args.shard_index, shard_count=args.shard_count, device=args.device)
    elif args.command == "train-seed":
        result = train_seed(args.activations, args.output, seed=args.seed, device=args.device)
    elif args.command == "capture-audit":
        result = {"manifest": str(capture_aether_audit(args.output, args.snapshot, args.cache, device=args.device))}
    elif args.command == "evaluate-audit":
        result = {"summary": str(evaluate_aether_audit(args.seeds, args.audit, args.output))}
    else:
        result = {"summary": str(finalize_rejected_seeds(args.seeds, args.output))}
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
