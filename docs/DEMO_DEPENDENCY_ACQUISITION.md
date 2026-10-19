# Demo Dependency Acquisition Record

## Target platform

- Python: CPython 3.11.9, 64-bit
- OS/architecture: Windows x86-64
- Demo environment: `.venv-demo-gpu` (research `.venv` is not modified)
- PyTorch: `torch==2.8.0`, official CUDA 12.6 index
- MCP SDK: `mcp==2.3.0`
- torchvision/torchaudio: not used by the repository and intentionally excluded

## Network diagnosis — 2026-10-19

- pip: 24.0
- pip configuration files: none present at global, site, or user locations
- `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`: absent
- `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`: absent
- `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `PIP_CERT`: absent
- WinINET proxy: disabled
- WinHTTP: direct access
- uv: not installed
- system trust-store mode resolves the initial certificate-validation failure
- `packaging==25.0` (66 KB) downloaded successfully
- `mcp==2.3.0` metadata repeatedly failed with `InvalidChunkLength`

Classification: **NETWORK_TRANSPORT_CORRUPTION**. Attempts stopped before transformers and CUDA PyTorch to avoid repeated large transfers.

## Reproducible acquisition

Online/stable network:

```powershell
.\scripts\build_demo_wheelhouse.ps1 -Wheelhouse .local\wheelhouse
```

Offline installation on the AETHER machine:

```powershell
.\scripts\install_demo_wheelhouse.ps1 -Wheelhouse .local\wheelhouse
```

The build performs bounded, verified HTTPS downloads in small-package, MCP, runtime, then PyTorch order. Installation verifies every size and SHA-256 from `wheelhouse_manifest.json`, then uses only `--no-index --find-links`. Wheels and manifests remain under ignored `.local/` and must not be committed.

Official package sources only:

- PyPI: `https://pypi.org/simple`
- PyTorch CUDA 12.6: `https://download.pytorch.org/whl/cu126`
