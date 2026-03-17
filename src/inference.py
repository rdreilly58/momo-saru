#!/usr/bin/env python3
"""
Momo-Saru Inference Engine

Unified interface for local (MLX) and remote (AWS GPU) inference.
Handles fallback logic, cost tracking, and performance metrics.
"""

import os
import sys
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import subprocess
import socket

try:
    from mlx_lm import generate, load
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False


@dataclass
class InferenceResult:
    """Result from inference request."""
    text: str
    tokens_generated: int
    tokens_per_second: float
    latency_ms: float
    cost_usd: float
    model: str
    backend: str  # "mlx_local" or "aws_gpu"
    timestamp: str


class MomoSaruInference:
    """
    Unified inference engine for Momotaro.
    
    Supports:
    - Local MLX inference (Apple Silicon, fallback)
    - AWS GPU inference (primary for complex work)
    - Automatic fallback on GPU unavailable
    - Cost tracking per request
    """

    # Pricing (March 17, 2026)
    PRICING = {
        "mlx_local": 0.0,  # Free (local compute)
        "aws_gpu": {
            "per_hour": 1.36,
            "per_token": 0.00000085,  # Approximate: $1.36/hr ÷ 1.6M tokens/hr
        }
    }

    # Model configs
    MODELS = {
        "qwen35b": {
            "backend": "mlx_local",
            "path": os.path.expanduser("~/models/qwen35b-4bit"),
            "max_tokens": 2048,
            "context_window": 262144,
        },
        "mistral7b": {
            "backend": "aws_gpu",
            "remote_path": "/mnt/data/models/mistral-7b",
            "max_tokens": 2048,
            "context_window": 32768,
        },
    }

    def __init__(self, primary_model: str = "mistral7b", fallback_model: str = "qwen35b"):
        """
        Initialize inference engine.
        
        Args:
            primary_model: Primary model to use (mistral7b for GPU, qwen35b for local)
            fallback_model: Fallback model if primary unavailable
        """
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.gpu_available = self._check_gpu_available()
        self.local_model = None
        self.request_count = 0

    def _check_gpu_available(self) -> bool:
        """Check if AWS GPU instance is reachable."""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-i", 
                 os.path.expanduser("~/.ssh/vlm-deploy-key.pem"),
                 "ubuntu@54.81.20.218", "echo", "GPU ready"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def infer(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> InferenceResult:
        """
        Run inference with fallback logic.
        
        Args:
            prompt: Input prompt
            model: Model to use (None = auto-select based on availability)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            
        Returns:
            InferenceResult with generated text and metrics
        """
        self.request_count += 1
        start_time = time.time()

        # Auto-select model based on GPU availability
        if model is None:
            model = self.primary_model if self.gpu_available else self.fallback_model

        # Try primary inference
        if model == "mistral7b" and self.gpu_available:
            result = self._infer_aws_gpu(prompt, max_tokens, temperature, top_p)
            if result:
                return result

        # Fallback to local MLX
        if model == "qwen35b" or not self.gpu_available:
            result = self._infer_mlx_local(prompt, max_tokens, temperature, top_p)
            if result:
                return result

        # If both failed, raise error
        raise RuntimeError("No inference backends available")

    def _infer_aws_gpu(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> Optional[InferenceResult]:
        """Run inference on AWS GPU instance."""
        try:
            start_time = time.time()

            # Prepare Python command to run on remote instance
            python_code = f"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import time

model_id = "mistralai/Mistral-7B-Instruct-v0.1"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", torch_dtype=torch.float16)

prompt = {repr(prompt)}
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

start = time.time()
outputs = model.generate(**inputs, max_new_tokens={max_tokens}, temperature={temperature}, top_p={top_p})
latency = (time.time() - start) * 1000

text = tokenizer.decode(outputs[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
print(json.dumps({{"text": text, "tokens": {max_tokens}, "latency_ms": latency}}))
"""

            # SSH and run on remote
            result = subprocess.run(
                ["ssh", "-i", os.path.expanduser("~/.ssh/vlm-deploy-key.pem"),
                 "ubuntu@54.81.20.218", f"cd /mnt/data && python3 -c {repr(python_code)}"],
                capture_output=True,
                timeout=60,
                text=True,
            )

            if result.returncode != 0:
                print(f"AWS inference failed: {result.stderr}", file=sys.stderr)
                return None

            data = json.loads(result.stdout)
            elapsed = (time.time() - start_time) * 1000
            cost = self._calculate_cost("aws_gpu", data["tokens"])

            return InferenceResult(
                text=data["text"],
                tokens_generated=data["tokens"],
                tokens_per_second=data["tokens"] / (elapsed / 1000),
                latency_ms=elapsed,
                cost_usd=cost,
                model="mistral7b",
                backend="aws_gpu",
                timestamp=datetime.now().isoformat(),
            )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
            print(f"AWS inference error: {e}", file=sys.stderr)
            return None

    def _infer_mlx_local(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> Optional[InferenceResult]:
        """Run inference on local MLX."""
        if not MLX_AVAILABLE:
            print("MLX not available. Install: pip install mlx mlx-lm", file=sys.stderr)
            return None

        try:
            start_time = time.time()

            # Load model if not already loaded
            if self.local_model is None:
                model_path = self.MODELS["qwen35b"]["path"]
                print(f"Loading local model from {model_path}...", file=sys.stderr)
                model, tokenizer = load(model_path)
                self.local_model = (model, tokenizer)
            else:
                model, tokenizer = self.local_model

            # Generate text
            result = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )

            elapsed = (time.time() - start_time) * 1000
            tokens = len(tokenizer.encode(result)) - len(tokenizer.encode(prompt))

            return InferenceResult(
                text=result,
                tokens_generated=tokens,
                tokens_per_second=tokens / (elapsed / 1000),
                latency_ms=elapsed,
                cost_usd=0.0,
                model="qwen35b",
                backend="mlx_local",
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            print(f"MLX inference error: {e}", file=sys.stderr)
            return None

    def _calculate_cost(self, backend: str, tokens: int) -> float:
        """Calculate inference cost."""
        if backend == "mlx_local":
            return 0.0
        elif backend == "aws_gpu":
            # Rough estimate: $1.36/hr ÷ 1.6M tokens/hr
            return tokens * self.PRICING["aws_gpu"]["per_token"]
        return 0.0

    def get_stats(self) -> Dict:
        """Get inference statistics."""
        return {
            "total_requests": self.request_count,
            "gpu_available": self.gpu_available,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Momo-Saru inference CLI")
    parser.add_argument("--prompt", type=str, required=True, help="Input prompt")
    parser.add_argument("--model", type=str, choices=["mistral7b", "qwen35b"], help="Model to use")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Run inference
    engine = MomoSaruInference()
    result = engine.infer(
        prompt=args.prompt,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    # Output
    if args.json:
        print(json.dumps({
            "text": result.text,
            "model": result.model,
            "backend": result.backend,
            "tokens": result.tokens_generated,
            "tokens_per_sec": round(result.tokens_per_second, 2),
            "latency_ms": round(result.latency_ms, 2),
            "cost_usd": round(result.cost_usd, 6),
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Model: {result.model} ({result.backend})")
        print(f"Tokens: {result.tokens_generated} @ {result.tokens_per_second:.2f} tok/s")
        print(f"Latency: {result.latency_ms:.2f}ms | Cost: ${result.cost_usd:.6f}")
        print(f"{'='*60}\n")
        print(result.text)


if __name__ == "__main__":
    main()
