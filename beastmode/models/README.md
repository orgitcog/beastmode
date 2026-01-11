# God Mode LLM Models

This directory contains pre-packaged GGUF models for use with the local llama.cpp server.

## Included Models

| Model | Size | Parameters | Description |
|-------|------|------------|-------------|
| SmolLM2-135M-Instruct-Q4_K_M | 101 MB | 135M | Ultra-compact model for testing and low-resource environments |

## Usage

### Quick Start

```bash
# Start the llama server with the included model
llama-start --model ~/beastmode/models/SmolLM2-135M-Instruct-Q4_K_M.gguf

# Or use GodChat directly (auto-detects available models)
godchat
```

### Model Details

**SmolLM2-135M-Instruct-Q4_K_M**

- **Source**: [bartowski/SmolLM2-135M-Instruct-GGUF](https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF)
- **Quantization**: Q4_K_M (4-bit, medium quality)
- **Context Length**: 2048 tokens
- **Best For**: Quick testing, low-memory systems, edge devices
- **SHA256**: `ed5fa30c487b282ec156c29062f1222e5c20875a944ac98289dbd242e947f747`

## Downloading Additional Models

Use the `llama_server.py` script to download additional models:

```bash
# List available models
llama-server list

# Download a model
llama-download mistral-7b
llama-download phi-3-mini
llama-download llama-3.2-3b
```

## Model Recommendations

| Use Case | Recommended Model | RAM Required |
|----------|-------------------|--------------|
| Testing / Edge | SmolLM2-135M | 512 MB |
| General Use | Phi-3 Mini | 4 GB |
| Coding | DeepSeek Coder 6.7B | 8 GB |
| High Quality | Llama 3.1 8B | 10 GB |

## Custom Models

To use your own GGUF models:

1. Place the `.gguf` file in this directory
2. Start the server with the model path:
   ```bash
   llama-start --model ~/beastmode/models/your-model.gguf
   ```

## Performance Tips

- **CPU Backend**: The server auto-detects your CPU capabilities and selects the optimal backend (SSE4.2, AVX2, AVX-512)
- **Threads**: Adjust thread count based on your CPU: `llama-start --threads 8`
- **Context Size**: Reduce context size for faster inference: `llama-start --ctx-size 1024`
- **Batch Size**: Increase batch size for better throughput: `llama-start --batch-size 1024`
