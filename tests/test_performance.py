from __future__ import annotations

import time
import pytest
import os
import shutil
import tempfile
from pathlib import Path
from yamlr.core.engine import YamlrEngine
from yamlr.cli.main import main as cli_main
import sys
from unittest.mock import patch

@pytest.fixture
def performance_corpus():
    """Generates a synthetic corpus for benchmarking."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_perf_")
    
    # 100 small, valid manifests (Realistic for pre-commit / small CI)
    for i in range(100):
        content = f"""apiVersion: v1
kind: Pod
metadata:
  name: perf-pod-{i}
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
"""
        with open(os.path.join(temp_dir, f"pod_{i}.yaml"), "w") as f:
            f.write(content)
            
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.mark.performance
def test_slo_ide_incremental():
    """SLO: IDE/Incremental single-file scan must be < 500ms."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write("apiVersion: v1\nkind: Service\nmetadata:\n  name: test\nspec:\n  ports:\n  - port: 80")
        tmp_path = f.name
    
    try:
        engine = YamlrEngine(workspace_path=os.path.dirname(tmp_path))
        rel_path = os.path.basename(tmp_path)
        
        start = time.perf_counter()
        engine.audit_and_heal_file(rel_path)
        duration = (time.perf_counter() - start) * 1000 
        
        print(f"\n[BENCHMARK] IDE Latency: {duration:.2f}ms")
        assert duration < 500
    finally:
        os.unlink(tmp_path)

@pytest.mark.performance
def test_slo_hook_fast(performance_corpus):
    """SLO: Pre-commit Hook / Fast scan must be < 2.0s for 100 files."""
    engine = YamlrEngine(workspace_path=performance_corpus, concurrency=1) # Hook is usually sequential
    
    start = time.perf_counter()
    engine.batch_heal(performance_corpus, fast=True, dry_run=True)
    duration = time.perf_counter() - start
    
    print(f"\n[BENCHMARK] Hook Latency (100 files, sequential): {duration:.2f}s")
    assert duration < 2.0

@pytest.mark.performance
def test_slo_ci_parallel(performance_corpus):
    """SLO: CI/Parallel healing/scanning must be < 5.0s for 100 files."""
    engine = YamlrEngine(workspace_path=performance_corpus, concurrency=4)
    
    start = time.perf_counter()
    engine.batch_heal(performance_corpus, dry_run=True)
    duration = time.perf_counter() - start
    
    print(f"\n[BENCHMARK] CI/Parallel Latency (100 files, full scan): {duration:.2f}s")
    assert duration < 5.0
