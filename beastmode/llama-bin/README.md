# Llama.cpp Windows Binaries

This directory contains pre-built llama.cpp binaries for Windows x64.

## Contents

| File | Description |
|------|-------------|
| `llama-server.exe` | HTTP server for running LLMs (OpenAI-compatible API) |
| `llama.dll` | Main llama.cpp library |
| `ggml.dll` / `ggml-base.dll` | GGML tensor library foundation |
| `mtmd.dll` | Multi-modal support for vision models |

## CPU-Optimized Backends

The following DLLs provide optimized inference for different CPU architectures:

| File | CPU Target | Features |
|------|------------|----------|
| `ggml-cpu-sse42.dll` | Older CPUs (2008+) | SSE4.2 |
| `ggml-cpu-x64.dll` | Generic x64 | Baseline |
| `ggml-cpu-sandybridge.dll` | Sandy Bridge (2011+) | AVX |
| `ggml-cpu-haswell.dll` | Haswell (2013+) | AVX2 |
| `ggml-cpu-alderlake.dll` | Alder Lake (2021+) | AVX2 + hybrid cores |
| `ggml-cpu-skylakex.dll` | Skylake-X (2017+) | AVX-512 |
| `ggml-cpu-icelake.dll` | Ice Lake (2019+) | AVX-512 VNNI |

## Usage

The `llama_server.py` script automatically detects your CPU capabilities and selects the optimal backend.

### Quick Start

```bash
# Start the server with auto-detected backend
python llama_server.py start

# Download a model first if needed
python llama_server.py download phi-3-mini

# Check status
python llama_server.py status
```

### Manual Usage (Windows)

```cmd
# Set the backend (optional - auto-detected)
set GGML_CPU_BACKEND=ggml-cpu-haswell.dll

# Start the server
llama-server.exe -m path/to/model.gguf --host 127.0.0.1 --port 8080
```

## API Endpoints

Once running, the server provides an OpenAI-compatible API:

- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `POST /v1/embeddings` - Text embeddings
- `GET /health` - Health check

## Integration with GodChat

GodChat automatically connects to the local llama server when available:

```bash
# Start llama server
llama-start

# Start GodChat (will use local LLM)
godchat
```

## Licenses

See the LICENSE-* files for third-party licenses:
- LICENSE-curl - libcurl
- LICENSE-httplib - cpp-httplib
- LICENSE-jsonhpp - nlohmann/json
- LICENSE-linenoise - linenoise
