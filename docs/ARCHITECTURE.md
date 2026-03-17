# Momo-Saru Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Momotaro (Main Session)                   │
│              (Claude, GPT-4, Local Haiku LLM)                │
└─────────────────────┬────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
   ┌─────────────┐        ┌──────────────────┐
   │  MLX Local  │        │   AWS GPU        │
   │             │        │  (g5.2xlarge)    │
   │ Apple Si... │        │                  │
   │ Qwen-35B    │        │ • Mistral-7B     │
   │ 4-bit       │        │ • 24GB VRAM      │
   │             │        │ • 27.98 tok/s    │
   │ 50-100 t/s  │        │                  │
   │ 0ms cost    │        │ $1.36/hr cost    │
   └──────┬──────┘        └────────┬─────────┘
          │                        │
          └────────────┬───────────┘
                       │
              ┌────────▼────────┐
              │  Fallback Logic │
              │  Health Checks  │
              │  Cost Tracking  │
              └─────────────────┘
```

## Components

### 1. **Inference Engine** (`src/inference.py`)

**Purpose:** Unified interface for local and remote inference

**Key Features:**
- Auto-select model based on GPU availability
- Automatic fallback to local MLX if GPU unavailable
- Cost tracking per request
- Performance metrics (latency, tokens/sec)

**Workflow:**
```
User Request
    ↓
Auto-detect GPU availability
    ↓
Is GPU available?
    ├─ YES → SSH to AWS GPU → Run Mistral-7B → Return result
    └─ NO → Load local MLX → Run Qwen-35B → Return result
```

**Cost Model:**
- **Local (MLX):** $0/request (uses existing compute)
- **AWS GPU:** ~$0.00000085/token (estimated from $1.36/hr rate)

### 2. **Health Check** (`src/health_check.py`)

**Purpose:** Monitor GPU instance health and detect failures

**Checks Performed:**
1. SSH connectivity (5s timeout)
2. NVIDIA GPU driver presence
3. CUDA availability
4. Quick inference test (5-10 tokens)
5. VRAM usage monitoring

**Output:**
```json
{
  "healthy": true,
  "gpu_available": true,
  "inference_latency_ms": 2100,
  "vram_usage_percent": 78.5,
  "timestamp": "2026-03-17T18:30:00"
}
```

**Integration:**
- Runs before GPU inference attempts
- Cached for 5 minutes (avoid repeated checks)
- Triggers fallback if GPU unhealthy

### 3. **Cost Tracker** (Planned)

**Purpose:** Track cumulative inference costs

**Metrics:**
- Daily/weekly/monthly spend
- Cost per model
- Cost per request
- Budget alerts

### 4. **Fallback Logic** (Planned)

**Purpose:** Graceful degradation when GPU unavailable

**Strategy:**
- Detect GPU failure → Switch to MLX automatically
- Queue requests if both backends busy
- Retry with exponential backoff
- Alert user if both backends fail

## Data Flow

### Example: Complex Task Inference

```
1. User asks: "Analyze this codebase"
   └─> Request hits Momotaro (main)

2. Momotaro routes to GPU (preferred for analysis)
   └─> Create InferenceResult object
   └─> Call inference.infer(prompt, model="mistral7b")

3. Inference engine checks GPU availability
   ├─ health_check.run()
   │  └─ SSH to 54.81.20.218, run quick test
   │  └─ Return: GPU healthy ✓
   │
   ├─ GPU available: YES
   │  └─ infer_aws_gpu()
   │  └─ SSH command + Python code
   │  └─ Mistral-7B generates response
   │  └─ Parse output, calculate cost
   │
   └─> Return InferenceResult
       - text: "Analysis..."
       - tokens: 512
       - latency_ms: 2100
       - cost_usd: 0.000435
       - backend: "aws_gpu"
       - model: "mistral7b"

4. Momotaro returns result to user
   └─> "Here's the analysis of your codebase..."
```

### Example: Simple Task Inference (GPU Down)

```
1. User asks: "What's the weather?"
   └─> Quick task

2. Momotaro checks GPU availability
   └─> health_check.run()
   └─> SSH timeout! GPU unavailable

3. Fallback to local MLX
   └─> Load Qwen-35B (if not cached)
   └─> Generate response locally
   └─> Much slower, but free

4. Return result
   └─> Cost: $0.00
   └─> Latency: 3200ms (slower but functional)
```

## Performance Characteristics

### AWS GPU (g5.2xlarge, Mistral-7B)

| Metric | Value | Notes |
|--------|-------|-------|
| Model Size | 7.2B params | 4-bit quantized |
| VRAM | 23.7GB / 24GB | Good headroom |
| Throughput | 27.98 tok/s | Measured March 17 |
| Latency (prompt) | ~2.1 sec | 3-token test prompt |
| Cost/Hour | $1.36 | Always-on pricing |
| Cost/Token | ~$0.00000085 | Estimated |
| Cold Start | ~105 sec | Model cached after |
| Availability | 3/24 hours | Test period ends March 20 |

### Local MLX (M4 Mac mini, Qwen-35B)

| Metric | Value | Notes |
|--------|-------|-------|
| Model Size | 35B params | 4-bit quantized, sparse MoE |
| Active Params | 3B | Only 3B active (sparse) |
| VRAM | ~8-12GB | During inference |
| Throughput | 50-100 tok/s | Depends on sparsity |
| Latency | Variable | Slower, suitable for fallback |
| Cost | $0.00 | Free (local compute) |
| Cold Start | 2-5 min | First load only |
| Availability | 24/7 | Always available |

## Decision Points

### When to Use GPU

**Use GPU if:**
- Complex reasoning required (>5 steps)
- Large context (>10K tokens)
- Fast response needed (<5 sec)
- Code generation/review
- Analysis tasks
- User willing to pay

**Cost-benefit:** 27.98 tok/s vs 50-100 tok/s = 2-3x speedup, costs ~$0.00000085/token

### When to Use Local

**Use Local if:**
- Simple Q&A (weather, facts)
- GPU unavailable/slow
- Latency insensitive (5-30 sec acceptable)
- Cost-conscious (free vs $0.00085/token)
- Testing/development

**Cost-benefit:** Free, but 2-3x slower

## Monitoring & Alerting

### Health Check Schedule

- **Quick (SSH only):** Every 5 minutes
- **Full check:** Every heartbeat (~30 min)
- **Inference test:** Every 2 hours
- **Cost report:** Daily at 9 AM

### Alerts

- GPU unreachable: Switch to MLX, log incident
- VRAM >90%: Warning, consider queuing
- Inference latency >10s: Log, monitor trend
- Daily cost >$50: Alert user
- SSH auth fails: Possible key issue

## Scaling Considerations

### If Usage Increases (>5 requests/day)

1. **Always-on GPU instance** ✓ Currently viable
2. **Add request queue** (handle concurrent requests)
3. **Multi-GPU setup** (multiple g5.2xlarge for parallel inference)
4. **Caching layer** (cache common prompts)

### If Usage Decreases (<1 request/day)

1. **Switch to on-demand** (save $980/month)
2. **Spot instances** (70% cheaper, interruptible)
3. **Pure local MLX** (free, acceptable latency)
4. **Serverless** (AWS Lambda, even cheaper)

## Future Enhancements

1. **Speculative Decoding** — Draft model on local, verify on GPU (2-3x speedup without quality loss)
2. **Batch Processing** — Queue multiple requests, process in parallel
3. **Model Fine-tuning** — Custom models for Momotaro's tasks
4. **Distributed Inference** — Split model across multiple GPUs
5. **Real-time Metrics Dashboard** — Web UI for monitoring

---

**Last Updated:** March 17, 2026
