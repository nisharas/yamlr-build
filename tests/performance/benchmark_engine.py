import os
import sys
import time
from pathlib import Path

# Add project root and src to path before any yamlr imports
sys.path.append(r"d:\yamlr")
sys.path.append(r"d:\yamlr\src")
from yamlr.core import YamlrEngine


def generate_large_fixture(base_file, target_size_mb):
    with open(base_file, "r") as f:
        content = f.read()

    large_file = r"d:\yamlr\tests\fixtures\large_perf_test.yaml"
    target_bytes = target_size_mb * 1024 * 1024

    with open(large_file, "w") as f:
        current_bytes = 0
        while current_bytes < target_bytes:
            f.write(content)
            f.write("\n---\n")
            current_bytes += len(content) + 5

    return large_file


def benchmark_engine(file_path):
    print(f"Scanning {file_path}...")

    from yamlr.core.engine import YamlrEngine
    from yamlr.models import HealConfig

    engine = YamlrEngine.quick("d:\\yamlr")
    pipeline = engine.pipeline

    content = ""
    with open(file_path, "r") as f:
        content = f.read()

    ctx = pipeline.create_context(content, HealConfig(file_path=file_path, fast=True, skip_repair=True))
    ctx.shadow_engine = pipeline.shadow
    ctx.physicist = pipeline.physicist

    start_total = time.time()
    _ = pipeline.heal(content, config=ctx.config)
    end_total = time.time()
    duration = end_total - start_total

    file_size = os.path.getsize(file_path)

    print(f"File Size: {file_size / (1024 * 1024):.2f} MB")
    print(f"Total Time: {duration:.4f}s")
    print(f"Total Throughput: {(file_size / (1024 * 1024)) / duration:.2f} MB/s")
    return (file_size / (1024 * 1024)) / duration


if __name__ == "__main__":
    base = r"d:\yamlr\tests\fixtures\healthy_manifest.yaml"
    large = r"d:\yamlr\tests\fixtures\mid_style.yaml"

    print("Benchmarking YamlrEngine Pipeline (Native Fast-Path)...")
    benchmark_engine(large)
