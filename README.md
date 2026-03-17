# Momo-Saru 🍑

**GPU acceleration for Momotaro** — MLX-based inference on AWS instances.

A toolkit for running large language models efficiently on AWS GPU infrastructure, with a focus on cost optimization and real-time inference.

## What is Momo-Saru?

Momo-Saru (Momo Monkey) bridges the gap between local LLM inference and cloud GPU acceleration. It provides:

- **MLX Runtime** — Apple Silicon-optimized inference (local dev)
- **AWS GPU Offload** — Mistral-7B and other models on g5.2xlarge instances
- **Cost Monitoring** — Track inference costs per request
- **Health Checks** — Automated instance health validation
- **Fallback Logic** — Graceful degradation when GPU is unavailable

## Quick Start

### Local (MLX - Apple Silicon)

```bash
source ~/mlx-env/bin/activate
python3 -c "
from mlx_lm import generate, load
model, tokenizer = load('~/models/qwen35b-4bit')
result = generate(model, tokenizer, prompt='Hello, world!', max_tokens=100)
print(result)
"
```

### AWS GPU Instance

```bash
# SSH to GPU instance
ssh -i ~/.ssh/vlm-deploy-key.pem ubuntu@54.81.20.218

# Run inference
cd /mnt/data
python3 inference.py --prompt "Your prompt here" --model mistral-7b
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Momotaro (Main Session)                 │
│    (Claude, GPT-4, Local Haiku)                 │
└──────────────┬──────────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
   ┌────────┐   ┌──────────────────┐
   │  MLX   │   │   AWS GPU        │
   │ Local  │   │  (g5.2xlarge)    │
   │        │   │ • Mistral-7B     │
   │ 50 tok │   │ • Qwen-35B       │
   │ /sec   │   │ • 27.98 tok/sec  │
   └────────┘   └──────────────────┘
```

## Performance (March 17, 2026)

### Mistral-7B on g5.2xlarge

| Metric | Value |
|--------|-------|
| **Speed** | 27.98 tok/s (14.3x vs CPU) |
| **Load Time** | ~105 sec (cached) |
| **Latency (3 tokens)** | ~2.1 sec |
| **VRAM Usage** | 23.7GB / 24GB |
| **Cost** | $1.36/hr ($980/month) |

### Local MLX (M4 Mac mini)

| Metric | Value |
|--------|-------|
| **Speed** | ~50-100 tok/s (sparse MoE) |
| **Active Params** | 3B / 35B (sparse) |
| **Memory** | ~8-12GB during inference |
| **Cold Start** | 2-5 min (first load) |

## Project Structure

```
momo-saru/
├── README.md                 # This file
├── SETUP.md                  # Installation guide
├── GPU_HEALTH_CHECK.md       # Health monitoring docs
├── COST_ANALYSIS.md          # Cost breakdown
├── src/
│   ├── inference.py          # Main inference engine
│   ├── health_check.py       # Instance health validation
│   ├── cost_tracker.py       # Cost per request
│   └── fallback.py           # Local/remote fallback logic
├── scripts/
│   ├── aws-setup.sh          # AWS instance bootstrap
│   ├── health-check.sh       # Daily health check
│   └── cost-report.sh        # Generate cost reports
├── tests/
│   ├── test_inference.py
│   ├── test_fallback.py
│   └── test_health.py
├── docker/
│   ├── Dockerfile            # GPU instance image
│   └── docker-compose.yml
└── docs/
    ├── architecture.md
    ├── deployment.md
    └── benchmarks.md
```

## Instance Status (March 17, 2026)

**AWS GPU Instance (g5.2xlarge)**
- **IP:** 54.81.20.218
- **Status:** ✅ Running (3-day test, then reassess cost model)
- **Model:** Mistral-7B (cached, ~105 sec cold start)
- **Daily Cost:** ~$32.64
- **Decision Point:** March 20, 2026

**Local MLX (M4 Mac mini)**
- **Status:** ✅ Available (backup, slower)
- **Model:** Qwen-35B (4-bit quantized, 38GB)
- **Use Case:** Dev/testing when GPU is down

## Next Steps

1. **Move GPU health scripts** from `~/.openclaw/workspace/scripts/` into this repo
2. **Containerize inference** (Dockerfile for reproducibility)
3. **Add cost dashboard** (track daily spend, optimize)
4. **Document fallback patterns** (graceful degradation when GPU unavailable)
5. **Add benchmarks** (latency, throughput, cost per token)
6. **CI/CD pipeline** (automated tests on PR)

## Contributing

This is primarily for capturing Momotaro's GPU infrastructure work, but contributions welcome:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/something`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/something`)
5. Open a Pull Request

## License

MIT (TBD — confirm with project owner)

## Author

Built by [Momotaro](https://github.com/rdreilly58) for efficient LLM inference on AWS.

---

**Last Updated:** March 17, 2026  
**Status:** Early development (MVP)
