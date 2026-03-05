import logging
from yamlr.core.pipeline import HealingPipeline

# Set logger to info to see suggestions
logging.basicConfig(level=logging.INFO)

def test_secret_env_safety():
    raw_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sensitive-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: nginx
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: missing-secret-env  # This should NOT be stubbed automatically!
              key: password
"""
    catalog = {"apps/v1/Deployment": {}}
    
    print("\n--- TEST: SENSITIVE ENV STUBBING (Should skip Secret) ---")
    pipeline = HealingPipeline(catalog=catalog)
    result = pipeline.heal(raw_yaml)
    
    print("\nHEALED CONTENT:")
    print(result.content)
    
    if "kind: Secret" in result.content:
        print("\n[FAIL] Sensitive Secret was stubbed automatically!")
    else:
        print("\n[PASS] Sensitive Secret was NOT stubbed (Security preserved).")

if __name__ == "__main__":
    test_secret_env_safety()
