#!/usr/bin/env python3
"""
Argo CD Integration Verification Script
---------------------------------------
Simulates an Argo CD environment and verifies that Yamlr produces 'Clinical Output'.
Clinical Output requirements:
1. Final manifests on stdout.
2. Zero user-facing noise (no progress bars, no headers) on stdout.
3. Errors on stderr.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def run_simulation():
    print("Starting Argo CD 'Clinical Output' Simulation...")
    
    # 1. Create a dummy broken manifest
    broken_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: broken-service
spec:
  selector:
    app: typo-name
  ports:
  - port: 80
    targetPort: 8080
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "service.yaml"
        manifest_path.write_text(broken_yaml)
        
        # 2. Set Argo CD Environment Variables
        env = os.environ.copy()
        env["ARGOCD_APP_NAME"] = "yamlr-integration-test"
        # Ensure we can find the package in src/
        project_root = Path(__file__).parent.parent.parent
        src_path = str(project_root / "src")
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
        
        # 3. Execution: yamlr heal <path>
        # We use 'python -m yamlr.cli.main' to ensure we use the current source
        cmd = [sys.executable, "-m", "yamlr.cli.main", "heal", str(manifest_path)]
        
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        # 4. Verification
        stdout = result.stdout
        stderr = result.stderr
        
        print("\n--- STDOUT ANALYSIS ---")
        if not stdout.strip():
            print("FAIL: stdout is empty. Expected healed manifest.")
        else:
            if "apiVersion:" in stdout and "kind: Service" in stdout:
                print("PASS: Valid YAML detected in stdout.")
            else:
                print("FAIL: stdout does not look like a Kubernetes manifest.")
            
            # Check for escape codes or Rich noise
            if "[" in stdout and "m" in stdout:
                print("FAIL: ANSI escape codes detected in stdout (Output is not plain).")
            else:
                print("PASS: No ANSI noise in stdout.")

        print("\n--- STDERR ANALYSIS ---")
        if stderr.strip():
            print(f"INFO: Stderr output detected (allowed for logs/warnings):\n{stderr}")
        else:
            print("PASS: stderr is clean.")

        # 5. Exit Code Logic
        if result.returncode == 0:
            print(f"\nPASS: Exit code 0 (Success)")
        else:
            print(f"\nFAIL: Exit code {result.returncode}")

if __name__ == "__main__":
    run_simulation()
