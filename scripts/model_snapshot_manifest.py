"""Create and verify a transferable pinned Qwen snapshot manifest."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path

from demo.backend.config import MODEL_ID, MODEL_REVISION

MANIFEST = "aether_model_snapshot_manifest.json"

def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def create(snapshot: Path) -> dict:
    files = []
    for path in sorted(snapshot.rglob("*")):
        if path.is_file() and path.name != MANIFEST:
            files.append({"path": path.relative_to(snapshot).as_posix(), "size": path.stat().st_size, "sha256": _hash(path)})
    names = {record["path"] for record in files}
    if "config.json" not in names or not any(name.endswith(".safetensors") for name in names):
        raise ValueError("snapshot lacks config.json or safetensors weights")
    if not ({"tokenizer.json", "tokenizer_config.json"} <= names):
        raise ValueError("snapshot lacks required tokenizer files")
    payload = {"schema_version": "aether.demo.model-snapshot.v1", "model_id": MODEL_ID,
               "resolved_revision": MODEL_REVISION, "files": files}
    (snapshot / MANIFEST).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

def verify(snapshot: Path) -> dict:
    payload = json.loads((snapshot / MANIFEST).read_text(encoding="utf-8"))
    if payload["model_id"] != MODEL_ID or payload["resolved_revision"] != MODEL_REVISION:
        raise ValueError("model identity or revision mismatch")
    expected = {record["path"]: record for record in payload["files"]}
    actual = {path.relative_to(snapshot).as_posix(): path for path in snapshot.rglob("*") if path.is_file() and path.name != MANIFEST}
    if set(expected) != set(actual):
        raise ValueError("model snapshot file set differs from manifest")
    for name, record in expected.items():
        path = actual[name]
        if path.stat().st_size != record["size"] or _hash(path) != record["sha256"]:
            raise ValueError(f"model snapshot integrity failure: {name}")
    return payload

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    payload = create(args.snapshot) if args.action == "create" else verify(args.snapshot)
    print(json.dumps({"action": args.action, "model_id": payload["model_id"], "resolved_revision": payload["resolved_revision"], "file_count": len(payload["files"])}))

if __name__ == "__main__":
    main()
