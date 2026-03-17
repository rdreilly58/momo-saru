#!/usr/bin/env python3
"""
GPU Instance Health Check

Monitors AWS GPU instance availability, performance, and health.
Used for detecting failures and triggering fallback to local inference.
"""

import subprocess
import json
import time
import os
import sys
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import socket


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    healthy: bool
    gpu_available: bool
    inference_latency_ms: Optional[float]
    vram_usage_percent: Optional[float]
    error_message: Optional[str]
    timestamp: str
    checks: Dict


class GPUHealthCheck:
    """
    Monitor AWS GPU instance health.
    
    Checks:
    1. SSH connectivity (basic reachability)
    2. GPU driver (nvidia-smi)
    3. CUDA availability
    4. Quick inference test (small model)
    5. VRAM usage
    """

    SSH_KEY = os.path.expanduser("~/.ssh/vlm-deploy-key.pem")
    GPU_HOST = "ubuntu@54.81.20.218"
    TIMEOUT = 30  # seconds

    def __init__(self, quick: bool = False):
        """
        Initialize health check.
        
        Args:
            quick: If True, only check SSH connectivity (faster)
        """
        self.quick = quick

    def run(self) -> HealthCheckResult:
        """Run full health check."""
        checks = {}
        start_time = time.time()

        # Check 1: SSH connectivity
        checks["ssh"] = self._check_ssh()
        if not checks["ssh"]["ok"]:
            return HealthCheckResult(
                healthy=False,
                gpu_available=False,
                inference_latency_ms=None,
                vram_usage_percent=None,
                error_message=f"SSH failed: {checks['ssh']['error']}",
                timestamp=datetime.now().isoformat(),
                checks=checks,
            )

        if self.quick:
            return HealthCheckResult(
                healthy=True,
                gpu_available=True,
                inference_latency_ms=None,
                vram_usage_percent=None,
                error_message=None,
                timestamp=datetime.now().isoformat(),
                checks=checks,
            )

        # Check 2: GPU driver
        checks["gpu_driver"] = self._check_gpu_driver()

        # Check 3: CUDA
        checks["cuda"] = self._check_cuda()

        # Check 4: Quick inference test
        checks["inference"] = self._check_inference()

        # Check 5: VRAM usage
        checks["vram"] = self._check_vram()

        elapsed = time.time() - start_time
        healthy = all(c.get("ok", False) for c in checks.values())

        return HealthCheckResult(
            healthy=healthy,
            gpu_available=checks["gpu_driver"].get("ok", False),
            inference_latency_ms=checks["inference"].get("latency_ms"),
            vram_usage_percent=checks["vram"].get("used_percent"),
            error_message=None if healthy else self._get_error_message(checks),
            timestamp=datetime.now().isoformat(),
            checks=checks,
        )

    def _check_ssh(self) -> Dict:
        """Check SSH connectivity."""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-i", self.SSH_KEY,
                 self.GPU_HOST, "echo", "OK"],
                capture_output=True,
                timeout=self.TIMEOUT,
                text=True,
            )
            ok = result.returncode == 0
            return {
                "ok": ok,
                "error": None if ok else result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "SSH timeout"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _check_gpu_driver(self) -> Dict:
        """Check NVIDIA GPU driver."""
        try:
            result = subprocess.run(
                ["ssh", "-i", self.SSH_KEY, self.GPU_HOST,
                 "nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                capture_output=True,
                timeout=self.TIMEOUT,
                text=True,
            )
            if result.returncode == 0:
                name, driver = result.stdout.strip().split(",")
                return {
                    "ok": True,
                    "gpu_name": name.strip(),
                    "driver_version": driver.strip(),
                }
            else:
                return {"ok": False, "error": "nvidia-smi not found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _check_cuda(self) -> Dict:
        """Check CUDA availability."""
        try:
            result = subprocess.run(
                ["ssh", "-i", self.SSH_KEY, self.GPU_HOST,
                 "python3", "-c", "import torch; print(f'CUDA: {torch.cuda.is_available()}')"],
                capture_output=True,
                timeout=self.TIMEOUT,
                text=True,
            )
            cuda_available = "True" in result.stdout
            return {
                "ok": cuda_available,
                "cuda_available": cuda_available,
                "error": None if cuda_available else "CUDA not available",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _check_inference(self) -> Dict:
        """Run quick inference test."""
        try:
            start = time.time()
            python_code = """
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1")
model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1", 
                                             device_map="auto", torch_dtype=torch.float16)

inputs = tokenizer("Hello", return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=10)
text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print("OK")
"""
            result = subprocess.run(
                ["ssh", "-i", self.SSH_KEY, self.GPU_HOST,
                 "python3", "-c", python_code],
                capture_output=True,
                timeout=60,  # Inference can take longer
                text=True,
            )
            latency = (time.time() - start) * 1000
            ok = result.returncode == 0
            return {
                "ok": ok,
                "latency_ms": latency if ok else None,
                "error": None if ok else result.stderr[:100],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "latency_ms": None, "error": "Inference timeout"}
        except Exception as e:
            return {"ok": False, "latency_ms": None, "error": str(e)}

    def _check_vram(self) -> Dict:
        """Check GPU VRAM usage."""
        try:
            result = subprocess.run(
                ["ssh", "-i", self.SSH_KEY, self.GPU_HOST,
                 "nvidia-smi", "--query-gpu=memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                timeout=self.TIMEOUT,
                text=True,
            )
            if result.returncode == 0:
                used, total = result.stdout.strip().split(",")
                used_mb = int(float(used.strip()))
                total_mb = int(float(total.strip()))
                percent = (used_mb / total_mb) * 100
                return {
                    "ok": True,
                    "used_mb": used_mb,
                    "total_mb": total_mb,
                    "used_percent": percent,
                }
            else:
                return {"ok": False, "error": "nvidia-smi query failed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_error_message(self, checks: Dict) -> str:
        """Extract first error message from checks."""
        for check_name, check_result in checks.items():
            if not check_result.get("ok", False):
                error = check_result.get("error", "Unknown error")
                return f"{check_name}: {error}"
        return "Unknown error"


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="GPU health check")
    parser.add_argument("--quick", action="store_true", help="Quick check (SSH only)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    checker = GPUHealthCheck(quick=args.quick)
    result = checker.run()

    if args.json:
        print(json.dumps({
            "healthy": result.healthy,
            "gpu_available": result.gpu_available,
            "inference_latency_ms": result.inference_latency_ms,
            "vram_usage_percent": round(result.vram_usage_percent, 1) if result.vram_usage_percent else None,
            "error": result.error_message,
            "timestamp": result.timestamp,
            "checks": result.checks if args.verbose else None,
        }, indent=2))
    else:
        status = "✅ HEALTHY" if result.healthy else "❌ UNHEALTHY"
        print(f"\n{status}")
        print(f"GPU Available: {result.gpu_available}")
        if result.inference_latency_ms:
            print(f"Inference Latency: {result.inference_latency_ms:.2f}ms")
        if result.vram_usage_percent:
            print(f"VRAM Usage: {result.vram_usage_percent:.1f}%")
        if result.error_message:
            print(f"Error: {result.error_message}")
        print(f"Timestamp: {result.timestamp}\n")

        if args.verbose:
            print("Detailed Checks:")
            for check_name, check_result in result.checks.items():
                check_status = "✓" if check_result.get("ok") else "✗"
                print(f"  {check_status} {check_name}: {check_result}")


if __name__ == "__main__":
    main()
