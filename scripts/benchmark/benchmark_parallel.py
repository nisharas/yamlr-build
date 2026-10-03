import os
import shutil
import time
from pathlib import Path

from yamlr.core.engine import YamlrEngine

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
TEST_CORPUS = ROOT_DIR / "tests/corpus/parallel_benchmark"
FILE_COUNT = 50
FILE_SIZE_KB = 200

TEMPLATE = """
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: benchmark-app-{f}-{i}
  labels:
    app: benchmark
    instance: "{f}-{i}"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: benchmark-{f}-{i}
  template:
    metadata:
      labels:
        app: benchmark-{f}-{i}
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        resources:
          limits:
            cpu: "500m"
            memory: "128Mi"
"""


def prepare_corpus_directory(path: Path, overwrite: bool, confirm=input):
    """Refuse to replace an existing corpus without explicit path confirmation."""
    if not path.exists() and not path.is_symlink():
        return

    resolved_path = path.resolve()
    repository_root = Path(__file__).resolve().parents[2]
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlink corpus path: {path}")
    if resolved_path == Path(resolved_path.anchor) or resolved_path == repository_root:
        raise ValueError(f"Refusing to replace a filesystem or repository root: {resolved_path}")
    if not path.is_dir():
        raise ValueError(f"Corpus path exists and is not a directory: {path}")
    if not overwrite:
        raise FileExistsError(
            f"Corpus directory '{path}' already exists. Pass --overwrite and confirm to replace it."
        )

    confirmation = f"OVERWRITE {resolved_path}"
    try:
        response = confirm(f"This permanently removes '{resolved_path}'. Type '{confirmation}' to continue: ")
    except (EOFError, OSError):
        response = ""
    if response != confirmation:
        raise PermissionError("Corpus overwrite was not confirmed; existing files were preserved.")

    shutil.rmtree(path)


def setup_corpus(count: int, size_kb: int, overwrite: bool = False, confirm=input, corpus_path: Path = TEST_CORPUS):
    prepare_corpus_directory(corpus_path, overwrite, confirm)
    corpus_path.mkdir(parents=True)

    print(f"Generating {count} files of ~{size_kb}KB each...")
    for f in range(count):
        file_path = corpus_path / f"manifest_{f}.yaml"
        with open(file_path, "w", encoding="utf-8") as out:
            i = 0
            while file_path.exists() and file_path.stat().st_size < (size_kb * 1024):
                out.write(TEMPLATE.format(f=f, i=i))
                i += 1
    print("Corpus ready.")


def run_parallel_benchmark():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Use native fast-path")
    parser.add_argument("--count", type=int, default=FILE_COUNT)
    parser.add_argument("--size", type=int, default=FILE_SIZE_KB)
    parser.add_argument("--overwrite", action="store_true", help="Confirm before replacing the generated corpus")
    args = parser.parse_args()

    try:
        setup_corpus(args.count, args.size, overwrite=args.overwrite)
    except (FileExistsError, PermissionError, ValueError) as error:
        parser.error(str(error))

    print("\nInitializing Engine...")
    engine = YamlrEngine(
        workspace_path=str(ROOT_DIR),
        catalog_path=None,  # Use default distilled
    )
    # Set concurrency
    engine.concurrency = 4

    print(f"Starting Parallel Batch Heal on {args.count} files (fast={args.fast})...")
    start_time = time.time()

    results = engine.batch_heal(
        root_path=str(TEST_CORPUS), extensions=[".yaml"], dry_run=True, fast=args.fast, task_label="Benchmarking"
    )

    duration = time.time() - start_time
    total_size_mb = sum(p.stat().st_size for p in TEST_CORPUS.glob("*.yaml")) / (1024 * 1024)
    throughput = total_size_mb / duration

    print("\nRESULTS (Parallel):")
    print("--------------------------------------------------")
    print(f"Files Processed: {len(results)}")
    print(f"Total Size:      {total_size_mb:.2f} MB")
    print(f"Duration:        {duration:.4f} seconds")
    print(f"Throughput:      {throughput:.2f} MB/s")
    print("--------------------------------------------------")

    # shutil.rmtree(TEST_CORPUS)


if __name__ == "__main__":
    run_parallel_benchmark()
