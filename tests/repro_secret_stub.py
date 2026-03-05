import logging
import sys
from yamlr.core.pipeline import HealingPipeline

# Set logger to info to see suggestions
logging.basicConfig(level=logging.INFO)

def test_secret_volume_stubbing():
    raw_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secured-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: nginx
        volumeMounts:
        - name: secret-vol
          mountPath: /etc/secrets
      volumes:
      - name: secret-vol
        secret:
          secretName: missing-secret-vol  # This should be stubbed!
"""
    catalog = {"apps/v1/Deployment": {}}
    # By default, stub_refs=True is passed in StageGhostResourceGeneration config if enabled.
    # In HealingPipeline init, we can enable it via flags.
    
    print("\n--- TEST: DEFAULT STUBBING (Should skip Secret) ---")
    pipeline = HealingPipeline(catalog=catalog)
    # The pipeline is hardcoded to run StageGhostResourceGeneration(stub_refs=True)
    result = pipeline.heal(raw_yaml)
    
    print("\nHEALED CONTENT:")
    print(result.content)
    
    if "kind: Secret" in result.content:
        print("\n[PASS] Secret was stubbed automatically! (Success)")
    else:
        print("\n[FAIL] Secret was NOT stubbed.")
        
    print("\n--- TEST: ASKING FOR UNSAFE (Should stub Secret) ---")
    # We need to see if HealingPipeline passes unsafe flag to StageGhostResourceGeneration
    # Actually, StageGhostResourceGeneration DOES NOT take unsafe flag yet.
    # It hardcodes {"stub_refs": True} inside run().
    
    # This confirms a gap: even if user wants unsafe stubs, the stage doesn't support passing it.

if __name__ == "__main__":
    test_secret_volume_stubbing()
