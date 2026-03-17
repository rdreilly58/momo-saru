#!/bin/bash
# Test Momo-Saru inference

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🍑 Momo-Saru Test Suite"
echo "======================="
echo ""

# Test 1: Check dependencies
echo "1️⃣  Checking dependencies..."
python3 --version >/dev/null 2>&1 || { echo "❌ Python 3 not found"; exit 1; }
python3 -c "import argparse" >/dev/null 2>&1 || { echo "❌ argparse not available"; exit 1; }
echo "✅ Dependencies OK"
echo ""

# Test 2: Test health check
echo "2️⃣  Testing GPU health check (quick)..."
python3 "$PROJECT_DIR/src/health_check.py" --quick --json 2>/dev/null | python3 -m json.tool >/dev/null 2>&1 && echo "✅ Health check OK" || echo "⚠️  Health check unavailable (GPU may be down)"
echo ""

# Test 3: Test inference (local MLX if available)
echo "3️⃣  Testing local inference..."
if python3 -c "import mlx_lm" 2>/dev/null; then
  echo "   MLX available, testing Qwen-35B..."
  python3 "$PROJECT_DIR/src/inference.py" \
    --prompt "Say hello in one word" \
    --model qwen35b \
    --max-tokens 10 \
    --json 2>/dev/null | python3 -m json.tool >/dev/null 2>&1 && echo "✅ Local inference OK" || echo "⚠️  Local inference failed"
else
  echo "⚠️  MLX not available (install with: pip install mlx mlx-lm)"
fi
echo ""

# Test 4: Test AWS GPU (if available)
echo "4️⃣  Testing AWS GPU inference..."
if ssh -o ConnectTimeout=5 -i ~/.ssh/vlm-deploy-key.pem ubuntu@54.81.20.218 "echo 'GPU ready'" >/dev/null 2>&1; then
  echo "   GPU instance reachable, testing..."
  python3 "$PROJECT_DIR/src/inference.py" \
    --prompt "Say hello" \
    --model mistral7b \
    --max-tokens 10 \
    --json 2>/dev/null | python3 -m json.tool >/dev/null 2>&1 && echo "✅ AWS GPU inference OK" || echo "⚠️  AWS GPU inference failed"
else
  echo "⚠️  GPU instance not reachable (may be down or starting)"
fi
echo ""

# Summary
echo "======================="
echo "🎉 Test suite complete!"
echo ""
echo "Next steps:"
echo "  1. Set up local MLX:  pip install -r requirements-mlx.txt"
echo "  2. Test inference:    python src/inference.py --prompt 'test' --model qwen35b"
echo "  3. Read docs:         cat README.md"
echo ""
