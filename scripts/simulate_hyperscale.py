#!/usr/bin/env python3
"""
HYPERSCALE SIMULATOR
--------------------
Generates massive synthetic clusters mimicking the architectures of
Google, Amazon, and Netflix to verify Yamlr's performance and logical
integrity at scale.

Author: Antigravity / Yamlr Team
"""

import argparse
import concurrent.futures
import os
import random
from pathlib import Path

BASE_DIR = Path("tests/simulation/hyperscale")


def write_manifest(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_google_cluster(count: int):
    """Borg-style: High density of Jobs, CronJobs, and complex OwnerReferences."""
    print(f"Generating Google-style cluster ({count} files)...")
    cluster_dir = BASE_DIR / "google"
    for i in range(count):
        name = f"google-job-{i}"
        content = f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: {name}
  namespace: prod
  uid: "uid-job-{i}"
spec:
  template:
    spec:
      containers:
      - name: worker
        image: gcr.io/google-containers/worker:v1
      restartPolicy: OnFailure
---
apiVersion: v1
kind: Pod
metadata:
  name: {name}-pod
  namespace: prod
  ownerReferences:
  - apiVersion: batch/v1
    kind: Job
    name: {name}
    uid: "uid-job-{i}"
spec:
  containers:
  - name: worker
    image: gcr.io/google-containers/worker:v1
"""
        write_manifest(cluster_dir / f"jobs/job-{i}.yaml", content.strip())


def generate_amazon_cluster(count: int):
    """VPC-style: Complex Ingress/Gateway API meshes."""
    print(f"Generating Amazon-style cluster ({count} files)...")
    cluster_dir = BASE_DIR / "amazon"
    for i in range(count):
        name = f"aws-svc-{i}"
        content = f"""
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: us-east-1
spec:
  selector:
    app: {name}
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}-ingress
  namespace: us-east-1
spec:
  rules:
  - http:
      paths:
      - path: /api/{i}
        pathType: Prefix
        backend:
          service:
            name: {name}
            port:
              number: 80
"""
        write_manifest(cluster_dir / f"networking/svc-{i}.yaml", content.strip())


def generate_netflix_cluster(count: int):
    """Microservice Chaos: Massive graph with high inter-dependency."""
    print(f"Generating Netflix-style cluster ({count} files)...")
    cluster_dir = BASE_DIR / "netflix"
    for i in range(count):
        name = f"ms-{i}"
        target = f"ms-{(i + 1) % count}"  # Circular dependecies for graph stress
        content = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  labels:
    app: {name}
    dependency: {target}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: main
        image: netflix/service:latest
        env:
        - name: TARGET_SERVICE
          value: {target}
"""
        write_manifest(cluster_dir / f"services/ms-{i}.yaml", content.strip())


def main():
    parser = argparse.ArgumentParser(description="Yamlr Hyperscale Simulator")
    parser.add_argument("--count", type=int, default=1000, help="Number of files per architecture style")
    parser.add_argument("--out", type=str, default="tests/simulation/hyperscale", help="Output directory")
    args = parser.parse_args()

    global BASE_DIR
    BASE_DIR = Path(args.out)

    if BASE_DIR.exists():
        import shutil

        shutil.rmtree(BASE_DIR)

    # Generate files per mode (Default 1000, Scalable to 150k+)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(generate_google_cluster, args.count),
            executor.submit(generate_amazon_cluster, args.count),
            executor.submit(generate_netflix_cluster, args.count),
        ]
        concurrent.futures.wait(futures)

    print(f"\nHyperscale Simulation Clusters Generated: {args.count * 3} total files.")


if __name__ == "__main__":
    main()
