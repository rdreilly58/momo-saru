# Momo-Saru Setup Guide

## Quick Start

### 1. Local Development (MLX - Apple Silicon)

**Prerequisites:**
- Python 3.10+
- Apple Silicon Mac (M1/M2/M3/M4)
- 40GB+ free disk space (for models)

**Installation:**

```bash
# Clone repo
git clone https://github.com/rdreilly58/momo-saru
cd momo-saru

# Create virtual environment
python3 -m venv mlx-env
source mlx-env/bin/activate

# Install dependencies
pip install -r requirements-mlx.txt

# Download model (first time only)
python3 src/download_model.py --model qwen35b-4bit

# Test inference
python3 src/inference.py --prompt "Hello, world!" --max-tokens 100
```

### 2. AWS GPU Instance (g5.2xlarge)

**Prerequisites:**
- AWS Account with EC2 permissions
- SSH key pair configured
- Budget: ~$980/month for always-on, or $1.36/hr on-demand

**Launch Instance:**

```bash
# Step 1: Get SSH key
# (already exists at ~/.ssh/vlm-deploy-key.pem)

# Step 2: SSH to instance
ssh -i ~/.ssh/vlm-deploy-key.pem ubuntu@54.81.20.218

# Step 3: Verify setup
cd /mnt/data
python3 -c "import torch; print(f'GPU: {torch.cuda.get_device_name()}')"

# Step 4: Run inference
python3 inference.py --prompt "Your prompt" --model mistral-7b
```

**Health Check:**

```bash
# Local machine
~/.openclaw/workspace/scripts/gpu-health-check-full.sh
```

## Configuration

### Environment Variables

**Local (MLX):**

```bash
export MLX_MODEL_PATH=~/models/qwen35b-4bit
export MLX_CACHE_DIR=~/.mlx_cache
```

**AWS GPU:**

```bash
export GPU_INSTANCE_IP=54.81.20.218
export GPU_MODEL=mistral-7b
export GPU_MAX_TOKENS=512
```

## Model Downloads

### Qwen-35B (4-bit, Local MLX)

```bash
python3 src/download_model.py --model qwen35b-4bit --output ~/models/
```

**Stats:**
- Size: 38GB
- Quantization: 4-bit
- Framework: MLX
- Active Parameters: 3B (sparse MoE)

### Mistral-7B (AWS GPU)

```bash
# Pre-cached on instance at /mnt/data/.cache/hf/models/
# Already available — no download needed
```

## Testing

```bash
# Run test suite
python3 -m pytest tests/ -v

# Test local inference
python3 tests/test_inference.py

# Test GPU fallback logic
python3 tests/test_fallback.py

# Test health checks
python3 tests/test_health.py
```

## Troubleshooting

### GPU Instance Not Responding

```bash
# Check instance status
aws ec2 describe-instances --instance-ids i-046d1154c0f4a9b2e --query 'Reservations[0].Instances[0].State.Name'

# Reboot if stuck
aws ec2 reboot-instances --instance-ids i-046d1154c0f4a9b2e

# Restart from scratch (not recommended, costs money)
aws ec2 start-instances --instance-ids i-046d1154c0f4a9b2e
```

### MLX Model Fails to Load

```bash
# Clear cache and retry
rm -rf ~/.mlx_cache
python3 src/download_model.py --model qwen35b-4bit --force

# Check available disk space
df -h ~/models/
```

### SSH Connection Timeout

```bash
# Verify security group allows SSH (port 22)
aws ec2 describe-security-groups --group-ids sg-xxxxxx

# Try with verbose output
ssh -vvv -i ~/.ssh/vlm-deploy-key.pem ubuntu@54.81.20.218
```

## Cost Optimization

### Option 1: Always-On (Current)
- **Monthly Cost:** $980
- **Best for:** High frequency inference (>10 requests/day)
- **Setup:** Instance stays running 24/7

### Option 2: On-Demand (Recommended for Low Usage)
- **Hourly Cost:** $1.36
- **Best for:** Occasional inference (<3 requests/day)
- **Setup:** Start instance when needed, stop when done

### Option 3: Spot Instances (Cheapest, Less Reliable)
- **Hourly Cost:** ~$0.40 (70% savings)
- **Risk:** Can be interrupted with 2-min notice
- **Best for:** Non-critical work, testing

**Cost Calculator:**

```bash
# Monthly cost (always-on)
daily_hours=24
hourly_rate=1.36
daily_cost=$(python3 -c "print($daily_hours * $hourly_rate)")
monthly_cost=$(python3 -c "print($daily_cost * 30)")
echo "Daily: \$$daily_cost | Monthly: \$$monthly_cost"
```

## Next Steps

1. ✅ Set up local MLX environment
2. ✅ Test inference on both local + AWS
3. ⏳ Integrate health checks into CI/CD
4. ⏳ Add cost dashboard
5. ⏳ Document all trade-offs

---

**Last Updated:** March 17, 2026
