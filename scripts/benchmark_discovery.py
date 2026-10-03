import time
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from yamlr.core.engine.base import YamlrEngine
from yamlr.core.pipeline.discovery import DiscoveryPhase
from yamlr.core.stages.base import PipelineState
from yamlr.core.engine.models import PipelineStats
from yamlr.core.context import HealContext

def run_benchmark(iterations=100):
    # Sample K8s content (Deployment)
    content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: default
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
"""
    
    engine = YamlrEngine(workspace_path=Path("."))
    phase = DiscoveryPhase()
    
    # 1. Force Python path
    print("Benchmarking Python Lexer...")
    start_py = time.time()
    for _ in range(iterations):
        state = PipelineState(content=content, shards=[], identities=[], context=HealContext(workspace=".", catalog={}, use_rust=False))
        phase.execute(state, engine=engine)
    end_py = time.time()
    avg_py = (end_py - start_py) / iterations
    print(f"Python Average: {avg_py*1000:.4f}ms")

    # 2. Try Rust path
    print("\nBenchmarking Rust Lexer...")
    start_rs = time.time()
    for _ in range(iterations):
        state = PipelineState(content=content, shards=[], identities=[], context=HealContext(workspace=".", catalog={}, use_rust=True))
        phase.execute(state, engine=engine)
        if not state.metadata.get("is_native"):
            print("⚠ WARNING: Rust Lexer FAILED/FELL BACK to Python!")
            break
    end_rs = time.time()
    avg_rs = (end_rs - start_rs) / iterations
    print(f"Rust Average: {avg_rs*1000:.4f}ms")
    
    if avg_rs > 0:
        print(f"\nSpeedup: {avg_py / avg_rs:.2f}x")

if __name__ == "__main__":
    run_benchmark()
