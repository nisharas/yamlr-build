import os
import time
from pathlib import Path

def generate_100k_manifests(target_dir: str):
    """Generates 100,000 unique, valid Kubernetes manifests for benchmark testing."""
    path = Path(target_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[!] Scale Generator: Creating 100,000 manifests in {target_dir}...")
    start_time = time.perf_counter()
    
    # Template categories to ensure schema diversity
    templates = {
        "deploy": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: stress-deploy-{id}
  namespace: default
  labels:
    app: stress-test
    tier: backend
    id: "{id}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stress-test
      id: "{id}"
  template:
    metadata:
      labels:
        app: stress-test
        id: "{id}"
    spec:
      containers:
      - name: main
        image: nginx:latest
        ports:
        - containerPort: 80
""",
        "service": """apiVersion: v1
kind: Service
metadata:
  name: stress-svc-{id}
  namespace: default
spec:
  selector:
    app: stress-test
    id: "{id}"
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
""",
        "cm": """apiVersion: v1
kind: ConfigMap
metadata:
  name: stress-cm-{id}
  namespace: default
data:
  config-key: "value-{id}"
  checksum: "{id}"
"""
    }
    
    counts = {"deploy": 0, "service": 0, "cm": 0}
    
    # Generate in batches to avoid file system thrashing
    for i in range(100000):
        if i % 3 == 0:
            category = "deploy"
        elif i % 3 == 1:
            category = "service"
        else:
            category = "cm"
            
        content = templates[category].format(id=i)
        file_name = f"{category}-{i}.yaml"
        
        with open(path / file_name, "w", encoding="utf-8") as f:
            f.write(content)
        
        counts[category] += 1
        
        if i > 0 and i % 10000 == 0:
            print(f"    ... Progress: {i} files created")
            
    end_time = time.perf_counter()
    print(f"\n[OK] Generated 100,000 files in {end_time - start_time:.2f}s")
    print(f"     Summary: {counts['deploy']} Deploys, {counts['service']} Services, {counts['cm']} ConfigMaps")

if __name__ == "__main__":
    generate_100k_manifests("tests/stress_test")
