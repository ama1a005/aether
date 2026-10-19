"""Create or verify the offline demo wheelhouse integrity manifest."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

MANIFEST_NAME = "wheelhouse_manifest.json"
PYPI_INDEX = "https://pypi.org/simple"
PYTORCH_INDEX = "https://download.pytorch.org/whl/cu126"

def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _identity(filename: str) -> tuple[str, str]:
    match = re.match(r"(?P<name>.+?)-(?P<version>\d[^-]*)-", filename)
    if not match:
        raise ValueError(f"cannot parse wheel identity: {filename}")
    return match.group("name").replace("_", "-"), match.group("version")

def create_manifest(wheelhouse: Path) -> dict[str, Any]:
    """Hash every wheel and record its authoritative source index."""
    wheels = sorted(wheelhouse.glob("*.whl"), key=lambda path: path.name.lower())
    if not wheels:
        raise ValueError(f"no wheels found in {wheelhouse}")
    files = []
    for path in wheels:
        package, version = _identity(path.name)
        files.append({"filename": path.name, "package": package, "version": version,
                      "size": path.stat().st_size, "sha256": _digest(path),
                      "source_index": PYTORCH_INDEX if package.lower() == "torch" else PYPI_INDEX})
    payload = {"schema_version": "aether.demo.wheelhouse.v1", "python": "CPython 3.11",
               "platform": "Windows x86_64", "torch": "2.8.0+cu126", "files": files}
    (wheelhouse / MANIFEST_NAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

def verify_manifest(wheelhouse: Path) -> dict[str, Any]:
    """Fail on missing, extra, resized, or hash-mismatched wheels."""
    payload = json.loads((wheelhouse / MANIFEST_NAME).read_text(encoding="utf-8"))
    expected = {record["filename"]: record for record in payload["files"]}
    actual = {path.name: path for path in wheelhouse.glob("*.whl")}
    if set(expected) != set(actual):
        raise ValueError(f"wheel set differs: missing={sorted(set(expected)-set(actual))}, extra={sorted(set(actual)-set(expected))}")
    for filename, record in expected.items():
        path = actual[filename]
        if path.stat().st_size != record["size"] or _digest(path) != record["sha256"]:
            raise ValueError(f"wheel integrity failure: {filename}")
    return payload

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("wheelhouse", type=Path)
    args = parser.parse_args()
    result = create_manifest(args.wheelhouse) if args.action == "create" else verify_manifest(args.wheelhouse)
    print(json.dumps({"action": args.action, "wheel_count": len(result["files"])}))

if __name__ == "__main__":
    main()
