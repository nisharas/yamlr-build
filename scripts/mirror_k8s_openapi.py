"""Automated Kubernetes OpenAPI Schema Bundle Mirroring Pipeline.

Why: Continuously fetches upstream official Kubernetes OpenAPI schemas from
     kubernetes/kubernetes GitHub releases, distills them into compact
     zero-copy schemas, and embeds them into Yamlr native core.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

K8S_VERSIONS = ["1.28", "1.29", "1.30", "1.31", "1.32"]

def fetch_and_distill_openapi(version: str, output_dir: Path):
    """Fetches official Kubernetes swagger.json and extracts core resource schemas.

    Why: Reduces raw 15MB Swagger specs into lean, deterministic schema bundles (<200KB).
    """
    url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/release-{version}/api/openapi-spec/swagger.json"
    print(f"[*] Fetching K8s v{version} schema from: {url}")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Yamlr-Schema-Pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            
        definitions = data.get("definitions", {})
        distilled = {}
        
        for k, v in definitions.items():
            # Retain only core workloads, networking, rbac, and config definitions
            if any(prefix in k for prefix in [
                "io.k8s.api.core.v1",
                "io.k8s.api.apps.v1",
                "io.k8s.api.networking.v1",
                "io.k8s.api.rbac.v1",
                "io.k8s.api.policy.v1",
                "io.k8s.api.batch.v1"
            ]):
                distilled[k] = {
                    "description": v.get("description", ""),
                    "properties": v.get("properties", {}),
                    "required": v.get("required", []),
                    "type": v.get("type", "object")
                }
                
        out_file = output_dir / f"schema_v{version.replace('.', '_')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(distilled, f, indent=2, sort_keys=True)
            
        print(f"[OK] Distilled {len(distilled)} schemas to {out_file}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to fetch v{version}: {e}")
        return False

def main():
    repo_root = Path(__file__).resolve().parent.parent
    schemas_dir = repo_root / "native_core" / "schemas" / "bundles"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== Yamlr Continuous OpenAPI Schema Mirroring ===")
    for ver in K8S_VERSIONS:
        fetch_and_distill_openapi(ver, schemas_dir)

if __name__ == "__main__":
    main()
