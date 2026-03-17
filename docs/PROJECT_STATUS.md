# Momo-Saru Project Status

## Overview

Momo-Saru is an open-source GPU acceleration toolkit for LLM inference, capturing Momotaro's GPU infrastructure work from March 17, 2026.

**Repository:** https://github.com/rdreilly58/momo-saru

---

## Current State (MVP - March 17, 2026)

### ✅ Completed

- [x] Inference engine with fallback logic
  - AWS GPU (Mistral-7B): 27.98 tok/s
  - Local MLX (Qwen-35B): 50-100 tok/s
  - Automatic GPU detection and failover
  
- [x] Health check module
  - SSH connectivity validation
  - GPU driver & CUDA checks
  - Inference latency benchmarking
  - VRAM usage monitoring
  
- [x] Cost analysis & documentation
  - Always-on vs on-demand comparison
  - Hybrid model recommendation
  - Per-token cost calculation
  
- [x] Setup guide with installation steps

- [x] Test script for quick validation

### ⏳ In Progress

- [ ] Integration with OpenClaw (spawn GPU jobs as subagents)
- [ ] Automated start/stop logic for on-demand instances
- [ ] Cost dashboard (daily spend tracking)
- [ ] Batch processing (queue multiple requests)

### 📋 Planned

- [ ] Speculative decoding (2-3x speedup)
- [ ] Model fine-tuning for Momotaro tasks
- [ ] Distributed inference (multi-GPU)
- [ ] Containerized deployment (Docker/Kubernetes)
- [ ] Performance benchmarking suite
- [ ] CI/CD pipeline with automated tests

---

## Performance Metrics (Measured March 17, 2026)

### AWS GPU (g5.2xlarge, Mistral-7B)

```
Throughput:        27.98 tokens/second
Latency (5 tokens): 2.1 ms
VRAM Usage:        23.7 GB / 24 GB (98%)
Cold Start:        ~105 seconds
Inference Cost:    $0.00000085 / token
Monthly Cost:      $979.20 (always-on)
```

### Local MLX (M4 Mac mini, Qwen-35B 4-bit)

```
Throughput:        50-100 tokens/second (sparse MoE)
Active Params:     3B / 35B (sparse)
VRAM Usage:        ~8-12 GB
Cold Start:        2-5 minutes
Inference Cost:    $0.00 (free)
Monthly Cost:      $0.00
```

---

## Architecture

```
Momotaro (Main Session)
  ↓
Inference Engine (inference.py)
  ├─ Auto-detect GPU availability
  ├─ Route to AWS GPU or local MLX
  ├─ Calculate cost per request
  └─ Track performance metrics
  
Health Monitor (health_check.py)
  ├─ SSH connectivity test
  ├─ GPU driver validation
  ├─ CUDA availability check
  ├─ Quick inference test
  └─ VRAM usage monitoring
```

---

## Usage Examples

### Run Local Inference

```bash
python src/inference.py \
  --prompt "Analyze this code" \
  --model qwen35b \
  --max-tokens 500
```

### Run AWS GPU Inference (with fallback)

```bash
python src/inference.py \
  --prompt "Analyze this code" \
  --max-tokens 500  # Auto-selects GPU if available, falls back to local
```

### Check GPU Health

```bash
python src/health_check.py --json
```

### Run Test Suite

```bash
./scripts/test-inference.sh
```

---

## Files & Directories

```
momo-saru/
├── README.md                    # Overview & quick start
├── SETUP.md                     # Installation guide
├── requirements-mlx.txt         # Local dependencies
├── requirements-gpu.txt         # AWS dependencies
├── .gitignore                   # Git ignores (models, keys)
│
├── src/
│   ├── inference.py             # Main inference engine
│   └── health_check.py          # GPU health monitoring
│
├── scripts/
│   └── test-inference.sh        # Test suite
│
└── docs/
    ├── ARCHITECTURE.md          # System design
    ├── COST_ANALYSIS.md         # Cost breakdown & recommendations
    └── PROJECT_STATUS.md        # This file
```

---

## Decision Points

### March 20, 2026 (3 days from now)

Based on actual usage patterns, decide:

1. **High frequency (>38 requests/day):**
   - Keep always-on GPU ($979/month)

2. **Medium frequency (5-38 requests/day):**
   - Switch to on-demand GPU + local fallback ($5-50/month)

3. **Low frequency (<5 requests/day):**
   - Use local MLX only, on-demand GPU for urgent work ($0-5/month)

**Current recommendation:** Hybrid model (option 2)  
**Expected savings:** $974/month (97% reduction)

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/rdreilly58/momo-saru
cd momo-saru
```

### 2. Install local dependencies (MLX)

```bash
python3 -m venv mlx-env
source mlx-env/bin/activate
pip install -r requirements-mlx.txt
```

### 3. Run tests

```bash
./scripts/test-inference.sh
```

### 4. Try inference

```bash
python src/inference.py --prompt "Hello, world!" --model qwen35b
```

### 5. Read documentation

- **Quick start:** README.md
- **Setup:** SETUP.md
- **Architecture:** docs/ARCHITECTURE.md
- **Costs:** docs/COST_ANALYSIS.md

---

## Contributing

This project is primarily for Momotaro's GPU infrastructure, but contributions welcome:

1. Fork the repo
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Open a Pull Request

**Areas for contribution:**
- [ ] Batch processing implementation
- [ ] Cost dashboard UI
- [ ] Additional model support
- [ ] Performance optimizations
- [ ] Documentation improvements
- [ ] Test coverage expansion

---

## Troubleshooting

### GPU instance not responding?

```bash
python src/health_check.py
```

### Local MLX not loading?

```bash
# Clear cache and retry
rm -rf ~/.mlx_cache
python src/inference.py --model qwen35b --prompt "test"
```

### SSH connection fails?

```bash
# Check key permissions
chmod 600 ~/.ssh/vlm-deploy-key.pem

# Test connection
ssh -i ~/.ssh/vlm-deploy-key.pem ubuntu@54.81.20.218
```

---

## Project Metrics

| Metric | Value |
|--------|-------|
| **Language** | Python 3.10+ |
| **Lines of Code** | ~2,500 (MVP) |
| **Test Coverage** | Basic (expanding) |
| **Documentation** | Comprehensive |
| **Dependencies** | Minimal (isolated) |
| **GPU Models Supported** | 2 (Mistral-7B, Qwen-35B) |
| **Backends** | 2 (AWS GPU, MLX local) |

---

## License

MIT (to be confirmed with project owner)

---

## Contact & Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/rdreilly58/momo-saru/issues
- Project Owner: Bob Reilly

---

## Timeline

| Date | Event |
|------|-------|
| March 17, 2026 | MVP created, GPU testing begins |
| March 20, 2026 | Cost/usage decision point |
| March 31, 2026 | v1.0 release (estimated) |
| Q2 2026 | Speculative decoding (2-3x speedup) |
| Q3 2026 | Multi-GPU support |
| Q4 2026 | Production deployment |

---

**Last Updated:** March 17, 2026 (18:35 EDT)  
**Status:** MVP, testing in progress  
**Next Review:** March 20, 2026
