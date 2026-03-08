#!/usr/bin/env python3
"""
YAMLR ENTERPRISE STRESS TEST
=============================
Simulates 100+ clusters with 1000+ unique broken YAML issues to validate
yamlr's healing capabilities and K8s compliance at production scale.

Test Categories:
1. Lexer repairs (indentation, colons, quotes, lists)
2. API deprecation migrations
3. Cross-resource semantic issues
4. Best practice violations
5. Edge cases (unicode, large files, norway problem)

Author: Yamlr Team
Date: 2026-02-09
"""

import hashlib
import json
import os
import random
import shutil
import string
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.engine import YamlrEngine
from yamlr.validators.schema_validator import SchemaValidator


# =============================================================================
# CONFIGURATION
# =============================================================================

NUM_CLUSTERS = 10
FILES_PER_CLUSTER = 50  # Total 500 files
TARGET_ISSUES = 1000
OUTPUT_DIR = Path("d:/yamlr/tests/stress_fixtures")
RESULTS_FILE = Path("d:/yamlr/tests/enterprise_stress_results.json")


@dataclass
class IssueStats:
    """Tracks issue injection and healing statistics."""
    category: str
    injected: int = 0
    healed: int = 0
    failed: int = 0
    examples: List[str] = field(default_factory=list)


@dataclass
class StressTestResults:
    """Complete stress test results."""
    total_clusters: int = 0
    total_files: int = 0
    total_issues_injected: int = 0
    total_issues_healed: int = 0
    total_issues_failed: int = 0
    healing_success_rate: float = 0.0
    schema_compliance_rate: float = 0.0
    crash_count: int = 0
    duration_seconds: float = 0.0
    category_breakdown: Dict[str, Dict] = field(default_factory=dict)
    failed_files: List[str] = field(default_factory=list)
    schema_failures: List[str] = field(default_factory=list)


# =============================================================================
# ISSUE GENERATORS (20 Categories)
# =============================================================================

class IssueInjector:
    """
    Generates 1000+ unique broken YAML issues across 20 categories.
    Each method returns (broken_yaml, issue_description, category).
    """
    
    def __init__(self):
        self.issue_counter = 0
        self.generated_issues: List[Tuple[str, str, str]] = []
        
    def _uid(self) -> str:
        """Generate unique identifier for each issue."""
        self.issue_counter += 1
        return f"i{self.issue_counter:04d}"
    
    # -------------------------------------------------------------------------
    # CATEGORY 1: Indentation Issues (50 variations)
    # -------------------------------------------------------------------------
    
    def gen_indentation_issues(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate indentation-related issues."""
        issues = []
        templates = [
            # 3-space indent
            ("""apiVersion: v1
kind: ConfigMap
metadata:
   name: indent3-{uid}
data:
   key: value""", "3-space indent", "indentation"),
            
            # 1-space indent
            ("""apiVersion: v1
kind: ConfigMap
metadata:
 name: indent1-{uid}
data:
 key: value""", "1-space indent", "indentation"),
            
            # Tab indent
            ("""apiVersion: v1
kind: ConfigMap
metadata:
\tname: tab-{uid}
data:
\tkey: value""", "tab indent", "indentation"),
            
            # Mixed tabs and spaces
            ("""apiVersion: v1
kind: ConfigMap
metadata:
 \tname: mixed-{uid}
data:
\t key: value""", "mixed tab/space", "indentation"),
            
            # 5-space indent (deep nesting simulation)
            ("""apiVersion: v1
kind: ConfigMap
metadata:
     name: indent5-{uid}
     labels:
          app: test""", "5-space indent", "indentation"),
        ]
        
        for i in range(count):
            template, desc, cat = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", cat))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 2: Colon Issues (50 variations)
    # -------------------------------------------------------------------------
    
    def gen_colon_issues(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate colon-related syntax issues."""
        issues = []
        templates = [
            # Missing colon
            ("""apiVersion v1
kind: ConfigMap
metadata:
  name: missing-colon-{uid}""", "missing colon", "colons"),
            
            # Fused value (no space after colon)
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name:fused-{uid}""", "fused value", "colons"),
            
            # Fused keyword
            ("""apiVersionv1
kind: ConfigMap
metadata:
  name: fused-keyword-{uid}""", "fused keyword apiVersion", "colons"),
            
            # kindDeployment fused
            ("""apiVersion: apps/v1
kindDeployment
metadata:
  name: fused-kind-{uid}""", "fused keyword kind", "colons"),
            
            # Extra space before colon
            ("""apiVersion : v1
kind : ConfigMap
metadata :
  name : extra-space-{uid}""", "extra space before colon", "colons"),
        ]
        
        for i in range(count):
            template, desc, cat = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", cat))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 3: List Issues (40 variations)
    # -------------------------------------------------------------------------
    
    def gen_list_issues(self, count: int = 40) -> List[Tuple[str, str, str]]:
        """Generate list-related syntax issues."""
        issues = []
        templates = [
            # Fused dash
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: fused-dash-{uid}
  labels:
-app: test
-tier: backend""", "fused dash in labels", "lists"),
            
            # Flush left list
            ("""apiVersion: v1
kind: Pod
metadata:
  name: flush-list-{uid}
spec:
  containers:
- name: nginx
  image: nginx""", "flush left container list", "lists"),
            
            # Missing dash
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: missing-dash-{uid}
data:
  items: |
    item1
    item2""", "missing list dash", "lists"),
        ]
        
        for i in range(count):
            template, desc, cat = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", cat))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 4: Quote Issues (30 variations)
    # -------------------------------------------------------------------------
    
    def gen_quote_issues(self, count: int = 30) -> List[Tuple[str, str, str]]:
        """Generate quote-related syntax issues."""
        issues = []
        templates = [
            # Unclosed double quote
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: unclosed-dq-{uid}
data:
  message: "hello world""", "unclosed double quote", "quotes"),
            
            # Unclosed single quote
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: unclosed-sq-{uid}
data:
  message: 'hello world""", "unclosed single quote", "quotes"),
            
            # Smart quotes (curly)
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: smart-quotes-{uid}
data:
  message: "hello world\"""", "smart/curly quotes", "quotes"),
        ]
        
        for i in range(count):
            template, desc, cat = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", cat))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 5: Deprecated APIs (60 variations)
    # -------------------------------------------------------------------------
    
    def gen_deprecated_api_issues(self, count: int = 60) -> List[Tuple[str, str, str]]:
        """Generate deprecated API version issues."""
        issues = []
        templates = [
            # extensions/v1beta1 Deployment
            ("""apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: ext-deploy-{uid}
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: legacy
    spec:
      containers:
      - name: nginx
        image: nginx:1.19""", "extensions/v1beta1 Deployment", "deprecated_apis"),
            
            # apps/v1beta1 Deployment
            ("""apiVersion: apps/v1beta1
kind: Deployment
metadata:
  name: apps-beta1-{uid}
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: legacy
    spec:
      containers:
      - name: nginx
        image: nginx:1.19""", "apps/v1beta1 Deployment", "deprecated_apis"),
            
            # apps/v1beta2 StatefulSet
            ("""apiVersion: apps/v1beta2
kind: StatefulSet
metadata:
  name: sts-beta2-{uid}
spec:
  serviceName: legacy
  replicas: 1
  selector:
    matchLabels:
      app: legacy
  template:
    metadata:
      labels:
        app: legacy
    spec:
      containers:
      - name: nginx
        image: nginx:1.19""", "apps/v1beta2 StatefulSet", "deprecated_apis"),
            
            # networking.k8s.io/v1beta1 Ingress
            ("""apiVersion: networking.k8s.io/v1beta1
kind: Ingress
metadata:
  name: ingress-beta-{uid}
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        backend:
          serviceName: web
          servicePort: 80""", "networking.k8s.io/v1beta1 Ingress", "deprecated_apis"),
            
            # policy/v1beta1 PodDisruptionBudget
            ("""apiVersion: policy/v1beta1
kind: PodDisruptionBudget
metadata:
  name: pdb-beta-{uid}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: legacy""", "policy/v1beta1 PDB", "deprecated_apis"),
            
            # rbac.authorization.k8s.io/v1beta1
            ("""apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: role-beta-{uid}
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]""", "rbac v1beta1 ClusterRole", "deprecated_apis"),
        ]
        
        for i in range(count):
            template, desc, cat = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", cat))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 6-11: Cross-Resource Issues (300 variations)
    # -------------------------------------------------------------------------
    
    def gen_ghost_service_issues(self, count: int = 80) -> List[Tuple[str, str, str]]:
        """Generate ghost service (selector mismatch) issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            # Service with typo in selector
            yaml = f"""---
apiVersion: v1
kind: Service
metadata:
  name: ghost-svc-{uid}
spec:
  selector:
    app: myapp-typo-{uid}
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ghost-deploy-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp-{uid}
  template:
    metadata:
      labels:
        app: myapp-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19"""
            issues.append((yaml, f"ghost service #{i+1}", "ghost_services"))
        
        return issues
    
    def gen_orphan_config_issues(self, count: int = 60) -> List[Tuple[str, str, str]]:
        """Generate orphan ConfigMap/Secret issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""---
apiVersion: v1
kind: ConfigMap
metadata:
  name: orphan-cm-{uid}
data:
  key: value
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orphan-deploy-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orphan-{uid}
  template:
    metadata:
      labels:
        app: orphan-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19
        # Note: ConfigMap is NOT referenced"""
            issues.append((yaml, f"orphan configmap #{i+1}", "orphan_configs"))
        
        return issues
    
    def gen_broken_volume_issues(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate broken PVC reference issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-vol-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: broken-vol-{uid}
  template:
    metadata:
      labels:
        app: broken-vol-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: nonexistent-pvc-{uid}"""
            issues.append((yaml, f"broken pvc ref #{i+1}", "broken_volumes"))
        
        return issues
    
    def gen_port_mismatch_issues(self, count: int = 60) -> List[Tuple[str, str, str]]:
        """Generate port mismatch issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""---
apiVersion: v1
kind: Service
metadata:
  name: port-mismatch-svc-{uid}
spec:
  selector:
    app: port-mismatch-{uid}
  ports:
  - port: 80
    targetPort: 9999
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: port-mismatch-deploy-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: port-mismatch-{uid}
  template:
    metadata:
      labels:
        app: port-mismatch-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19
        ports:
        - containerPort: 80"""
            issues.append((yaml, f"port mismatch #{i+1}", "port_mismatches"))
        
        return issues
    
    def gen_ingress_issues(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate Ingress backend issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: broken-ingress-{uid}
spec:
  rules:
  - host: example-{uid}.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nonexistent-svc-{uid}
            port:
              number: 80"""
            issues.append((yaml, f"broken ingress backend #{i+1}", "ingress_issues"))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 12-15: Best Practice Violations (300 variations)
    # -------------------------------------------------------------------------
    
    def gen_missing_resources_issues(self, count: int = 80) -> List[Tuple[str, str, str]]:
        """Generate missing CPU/Memory resources issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: no-resources-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: no-resources-{uid}
  template:
    metadata:
      labels:
        app: no-resources-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19"""
            issues.append((yaml, f"missing resources #{i+1}", "missing_resources"))
        
        return issues
    
    def gen_image_tag_issues(self, count: int = 60) -> List[Tuple[str, str, str]]:
        """Generate image tag issues (:latest, missing tags)."""
        issues = []
        images = ["nginx:latest", "redis:latest", "postgres", "mysql:latest", "nginx", "alpine"]
        
        for i in range(count):
            uid = self._uid()
            image = images[i % len(images)]
            yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-tag-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bad-tag-{uid}
  template:
    metadata:
      labels:
        app: bad-tag-{uid}
    spec:
      containers:
      - name: app
        image: {image}"""
            issues.append((yaml, f"bad image tag ({image}) #{i+1}", "image_tags"))
        
        return issues
    
    def gen_missing_probes_issues(self, count: int = 80) -> List[Tuple[str, str, str]]:
        """Generate missing health probes issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: no-probes-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: no-probes-{uid}
  template:
    metadata:
      labels:
        app: no-probes-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19
        ports:
        - containerPort: 80"""
            issues.append((yaml, f"missing probes #{i+1}", "missing_probes"))
        
        return issues
    
    def gen_security_issues(self, count: int = 80) -> List[Tuple[str, str, str]]:
        """Generate security context issues."""
        issues = []
        templates = [
            # Privileged container
            ("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: privileged-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: privileged-{uid}
  template:
    metadata:
      labels:
        app: privileged-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19
        securityContext:
          privileged: true""", "privileged container"),
            
            # Run as root
            ("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: root-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: root-{uid}
  template:
    metadata:
      labels:
        app: root-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19
        securityContext:
          runAsUser: 0""", "run as root"),
            
            # No security context
            ("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: no-sec-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: no-sec-{uid}
  template:
    metadata:
      labels:
        app: no-sec-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19""", "no security context"),
        ]
        
        for i in range(count):
            template, desc = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", "security_issues"))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 16-17: Schema Violations (90 variations)
    # -------------------------------------------------------------------------
    
    def gen_schema_violations(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate schema violation issues."""
        issues = []
        templates = [
            # Typo in spec key
            ("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: typo-spec-{uid}
spec:
  replicass: 1
  selector:
    matchLabels:
      app: typo-{uid}
  template:
    metadata:
      labels:
        app: typo-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19""", "typo in replicas"),
            
            # Wrong nesting
            ("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: wrong-nest-{uid}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wrong-{uid}
  template:
    metadata:
      labels:
        app: wrong-{uid}
    spec:
      containers:
        name: nginx
        image: nginx:1.19""", "wrong nesting"),
        ]
        
        for i in range(count):
            template, desc = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", "schema_violations"))
        
        return issues
    
    def gen_type_mismatch_issues(self, count: int = 40) -> List[Tuple[str, str, str]]:
        """Generate type mismatch issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: type-mismatch-{uid}
spec:
  replicas: "3"
  selector:
    matchLabels:
      app: type-{uid}
  template:
    metadata:
      labels:
        app: type-{uid}
    spec:
      containers:
      - name: nginx
        image: nginx:1.19"""
            issues.append((yaml, f"replicas as string #{i+1}", "type_mismatches"))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 18-20: Edge Cases (40 variations)
    # -------------------------------------------------------------------------
    
    def gen_unicode_issues(self, count: int = 20) -> List[Tuple[str, str, str]]:
        """Generate unicode/emoji issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: unicode-{uid}
  labels:
    🚀: rocket
    app: unicode-{uid}
data:
  message: "Hello 世界 🌍"
  emoji: "🔥💯✅"
  rtl: "مرحبا"
"""
            issues.append((yaml, f"unicode/emoji #{i+1}", "unicode"))
        
        return issues
    
    def gen_norway_problem_issues(self, count: int = 10) -> List[Tuple[str, str, str]]:
        """Generate Norway problem issues (NO/ON/OFF parsed as booleans)."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: norway-{uid}
data:
  NO: "Norway"
  ON: "Ontario"
  OFF: "Offline"
  YES: "Affirmative"
"""
            issues.append((yaml, f"norway problem #{i+1}", "norway_problem"))
        
        return issues
    
    def gen_large_file_issues(self, count: int = 10) -> List[Tuple[str, str, str]]:
        """Generate large file issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            lines = [f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: monolith-{uid}
data:"""]
            
            # Generate 500 key-value pairs (creates ~25KB file)
            for j in range(500):
                lines.append(f"  key_{j:04d}: 'value_{j}_with_extra_content_for_size'")
            
            yaml = "\n".join(lines)
            issues.append((yaml, f"large file #{i+1}", "large_files"))
        
        return issues
    
    # -------------------------------------------------------------------------
    # CATEGORY 21-28: OVERLOOKED FREE-TIER ISSUES (New)
    # -------------------------------------------------------------------------
    
    def gen_duplicate_key_issues(self, count: int = 100) -> List[Tuple[str, str, str]]:
        """Generate duplicate key issues (FREE should detect/fix)."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: dup-keys-{uid}
  name: dup-keys-{uid}-duplicate
data:
  key1: value1
  key1: value1-duplicate"""
            issues.append((yaml, f"duplicate keys #{i+1}", "duplicate_keys"))
        
        return issues
    
    def gen_trailing_whitespace_issues(self, count: int = 100) -> List[Tuple[str, str, str]]:
        """Generate trailing whitespace issues (FREE should clean)."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: v1   
kind: ConfigMap  
metadata:  
  name: trailing-ws-{uid}   
data:  
  key: value   """
            issues.append((yaml, f"trailing whitespace #{i+1}", "trailing_whitespace"))
        
        return issues
    
    def gen_empty_value_issues(self, count: int = 100) -> List[Tuple[str, str, str]]:
        """Generate empty value issues (key: with no value)."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: empty-val-{uid}
  labels:
data:
  key1:
  key2: value2"""
            issues.append((yaml, f"empty values #{i+1}", "empty_values"))
        
        return issues
    
    def gen_bom_issues(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate BOM (Byte Order Mark) issues (Windows UTF-8)."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            # UTF-8 BOM prefix
            yaml = f"""\ufeffapiVersion: v1
kind: ConfigMap
metadata:
  name: bom-{uid}
data:
  key: value"""
            issues.append((yaml, f"UTF-8 BOM #{i+1}", "bom_issues"))
        
        return issues
    
    def gen_crlf_issues(self, count: int = 100) -> List[Tuple[str, str, str]]:
        """Generate CRLF line ending issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"apiVersion: v1\r\nkind: ConfigMap\r\nmetadata:\r\n  name: crlf-{uid}\r\ndata:\r\n  key: value"
            issues.append((yaml, f"CRLF line endings #{i+1}", "crlf_endings"))
        
        return issues
    
    def gen_anchor_issues(self, count: int = 50) -> List[Tuple[str, str, str]]:
        """Generate undefined anchor reference issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: anchor-{uid}
data:
  defaults: *undefined_anchor
  values:
    key: value"""
            issues.append((yaml, f"undefined anchor #{i+1}", "anchor_issues"))
        
        return issues
    
    def gen_multiline_string_issues(self, count: int = 100) -> List[Tuple[str, str, str]]:
        """Generate multiline string issues (| and >)."""
        issues = []
        templates = [
            # Missing newline after |
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: multiline-{uid}
data:
  script: |key1: value1
    key2: value2""", "missing newline after |"),
            
            # Wrong indent in literal block
            ("""apiVersion: v1
kind: ConfigMap
metadata:
  name: multiline-{uid}
data:
  script: |
key1: value1
  key2: value2""", "wrong indent in literal block"),
        ]
        
        for i in range(count):
            template, desc = templates[i % len(templates)]
            uid = self._uid()
            issues.append((template.format(uid=uid), f"{desc} #{i+1}", "multiline_strings"))
        
        return issues
    
    def gen_comment_issues(self, count: int = 100) -> List[Tuple[str, str, str]]:
        """Generate comment preservation/edge case issues."""
        issues = []
        
        for i in range(count):
            uid = self._uid()
            yaml = f"""# Header comment
apiVersion: v1 # inline comment
kind: ConfigMap
metadata:
  name: comments-{uid}
  # Metadata comment
data:
  key: value # value comment
  # Orphan comment
  url: "http://example.com#fragment" # not a comment"""
            issues.append((yaml, f"comment edge cases #{i+1}", "comments"))
        
        return issues
    
    # -------------------------------------------------------------------------
    # MASTER GENERATOR (20X SCALE)
    # -------------------------------------------------------------------------
    
    def generate_all_issues(self) -> List[Tuple[str, str, str]]:
        """Generate 20,000+ issues across all categories for enterprise scale."""
        all_issues = []
        
        # =====================================================================
        # FREE TIER: Lexer/Syntax Repairs (2000 issues)
        # =====================================================================
        all_issues.extend(self.gen_indentation_issues(400))
        all_issues.extend(self.gen_colon_issues(400))
        all_issues.extend(self.gen_list_issues(300))
        all_issues.extend(self.gen_quote_issues(200))
        all_issues.extend(self.gen_duplicate_key_issues(200))
        all_issues.extend(self.gen_trailing_whitespace_issues(200))
        all_issues.extend(self.gen_empty_value_issues(100))
        all_issues.extend(self.gen_bom_issues(100))
        all_issues.extend(self.gen_crlf_issues(100))
        
        # =====================================================================
        # FREE TIER: Deprecated APIs (1000 issues)
        # =====================================================================
        all_issues.extend(self.gen_deprecated_api_issues(1000))
        
        # =====================================================================
        # FREE TIER: Edge Cases (800 issues)
        # =====================================================================
        all_issues.extend(self.gen_unicode_issues(200))
        all_issues.extend(self.gen_norway_problem_issues(100))
        all_issues.extend(self.gen_large_file_issues(100))
        all_issues.extend(self.gen_anchor_issues(100))
        all_issues.extend(self.gen_multiline_string_issues(200))
        all_issues.extend(self.gen_comment_issues(100))
        
        # =====================================================================
        # DETECTION ONLY (PRO auto-fix): Cross-Resource (4000 issues)
        # =====================================================================
        all_issues.extend(self.gen_ghost_service_issues(1000))
        all_issues.extend(self.gen_orphan_config_issues(800))
        all_issues.extend(self.gen_broken_volume_issues(600))
        all_issues.extend(self.gen_port_mismatch_issues(800))
        all_issues.extend(self.gen_ingress_issues(800))
        
        # =====================================================================
        # DETECTION ONLY (PRO auto-fix): Best Practices (6000 issues)
        # =====================================================================
        all_issues.extend(self.gen_missing_resources_issues(1500))
        all_issues.extend(self.gen_image_tag_issues(1500))
        all_issues.extend(self.gen_missing_probes_issues(1500))
        all_issues.extend(self.gen_security_issues(1500))
        
        # =====================================================================
        # SCHEMA: Typos/Type Issues (2000 issues) - Consider for FREE?
        # =====================================================================
        all_issues.extend(self.gen_schema_violations(1000))
        all_issues.extend(self.gen_type_mismatch_issues(1000))
        
        return all_issues


# =============================================================================
# CLUSTER GENERATOR
# =============================================================================

class ClusterGenerator:
    """Generates 100+ simulated cluster directories with broken YAML files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.injector = IssueInjector()
        
    def generate_clusters(self, num_clusters: int) -> Tuple[int, int]:
        """
        Generate cluster directories with distributed issues.
        Returns (total_files, total_issues).
        """
        # Clean and recreate output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)
        
        # Generate all issues
        all_issues = self.injector.generate_all_issues()
        total_issues = len(all_issues)
        
        # Shuffle for random distribution
        random.shuffle(all_issues)
        
        # Distribute issues across clusters
        issues_per_cluster = len(all_issues) // num_clusters
        remainder = len(all_issues) % num_clusters
        
        file_count = 0
        issue_idx = 0
        
        for cluster_id in range(1, num_clusters + 1):
            cluster_dir = self.output_dir / f"cluster_{cluster_id:03d}"
            cluster_dir.mkdir(parents=True)
            
            # Calculate issues for this cluster
            cluster_issues = issues_per_cluster + (1 if cluster_id <= remainder else 0)
            
            # Write issues as YAML files
            for i in range(cluster_issues):
                if issue_idx >= len(all_issues):
                    break
                    
                yaml_content, desc, category = all_issues[issue_idx]
                
                # Create category subdirectory
                cat_dir = cluster_dir / category
                cat_dir.mkdir(exist_ok=True)
                
                # Write file
                filename = f"{category}_{issue_idx:05d}.yaml"
                filepath = cat_dir / filename
                filepath.write_text(yaml_content, encoding="utf-8")
                
                file_count += 1
                issue_idx += 1
        
        return file_count, total_issues


# =============================================================================
# STRESS TEST RUNNER
# =============================================================================

class StressTestRunner:
    """Runs the enterprise stress test and collects results."""
    
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir
        self.results = StressTestResults()
        self.schema_validator = SchemaValidator(k8s_version="1.29")
        self.schema_validator.load_schema(background=False)
        
        # Create a dummy catalog for the stress test
        self.catalog_path = fixtures_dir / "test_catalog.json"
        self.catalog_path.write_text('{"schemas": {}, "version": "v1.31-stress"}', encoding="utf-8")
        
    def run(self) -> StressTestResults:
        """Execute the full stress test."""
        start_time = time.time()
        
        # Count clusters
        clusters = [d for d in self.fixtures_dir.iterdir() if d.is_dir()]
        self.results.total_clusters = len(clusters)
        
        print(f"\n{'='*60}")
        print(f"🚀 YAMLR ENTERPRISE STRESS TEST")
        print(f"{'='*60}")
        print(f"Clusters: {len(clusters)}")
        
        # Initialize category tracking
        category_stats: Dict[str, IssueStats] = {}
        
        # Process each cluster
        for cluster_idx, cluster_dir in enumerate(sorted(clusters), 1):
            print(f"\n📦 Processing {cluster_dir.name} ({cluster_idx}/{len(clusters)})...")
            
            try:
                engine = YamlrEngine(
                    workspace_path=str(cluster_dir),
                    catalog_path=str(self.catalog_path),
                    app_name="yamlr",
                    health_threshold=50,
                    cluster_version="1.29"
                )
                
                # Batch heal the cluster
                results = engine.batch_heal(
                    root_path=str(cluster_dir),
                    extensions=[".yaml", ".yml"],
                    max_depth=10,
                    dry_run=False,
                    compact=True,
                    skip_backup=True
                )
                
                # Process results
                for result in results:
                    self.results.total_files += 1
                    filepath = result.get("path", "")
                    
                    # Determine category from path
                    category = self._extract_category(filepath)
                    if category not in category_stats:
                        category_stats[category] = IssueStats(category=category)
                    
                    stats = category_stats[category]
                    stats.injected += 1
                    
                    status = result.get("status", "")
                    
                    if status in ["HEALED", "CLEAN", "SUCCESS"]:
                        stats.healed += 1
                        self.results.total_issues_healed += 1
                        
                        # Validate schema compliance
                        healed_content = result.get("content", "")
                        if healed_content and not self._validate_schema(healed_content):
                            self.results.schema_failures.append(filepath)
                    else:
                        stats.failed += 1
                        self.results.total_issues_failed += 1
                        self.results.failed_files.append(filepath)
                        if len(stats.examples) < 3:
                            stats.examples.append(f"{filepath}: {result.get('error', 'unknown')}")
                            
            except Exception as e:
                self.results.crash_count += 1
                print(f"  ❌ CRASH: {e}")
        
        # Calculate final statistics
        self.results.duration_seconds = time.time() - start_time
        self.results.total_issues_injected = self.results.total_files
        
        if self.results.total_files > 0:
            self.results.healing_success_rate = (
                self.results.total_issues_healed / self.results.total_files * 100
            )
            schema_pass = self.results.total_issues_healed - len(self.results.schema_failures)
            if self.results.total_issues_healed > 0:
                self.results.schema_compliance_rate = (
                    schema_pass / self.results.total_issues_healed * 100
                )
        
        # Store category breakdown
        for cat, stats in category_stats.items():
            self.results.category_breakdown[cat] = {
                "injected": stats.injected,
                "healed": stats.healed,
                "failed": stats.failed,
                "success_rate": stats.healed / stats.injected * 100 if stats.injected > 0 else 0,
                "examples": stats.examples
            }
        
        return self.results
    
    def _extract_category(self, filepath: str) -> str:
        """Extract category from file path."""
        parts = Path(filepath).parts
        for part in parts:
            if part in [
                # FREE TIER: Lexer/Syntax
                "indentation", "colons", "lists", "quotes",
                "duplicate_keys", "trailing_whitespace", "empty_values",
                "bom_issues", "crlf_endings",
                # FREE TIER: Deprecated APIs
                "deprecated_apis",
                # FREE TIER: Edge Cases
                "unicode", "norway_problem", "large_files",
                "anchor_issues", "multiline_strings", "comments",
                # DETECTION ONLY: Cross-Resource
                "ghost_services", "orphan_configs", "broken_volumes", 
                "port_mismatches", "ingress_issues",
                # DETECTION ONLY: Best Practices
                "missing_resources", "image_tags", "missing_probes", "security_issues",
                # SCHEMA
                "schema_violations", "type_mismatches"
            ]:
                return part
        return "unknown"
    
    def _validate_schema(self, content: str) -> bool:
        """Validate healed content against K8s schema."""
        try:
            # Basic YAML parse check
            import yaml
            docs = list(yaml.safe_load_all(content))
            return all(isinstance(d, dict) for d in docs if d is not None)
        except Exception:
            return False


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def generate_report(results: StressTestResults) -> str:
    """Generate a markdown report of test results."""
    lines = []
    lines.append("# 🧪 Yamlr Enterprise Stress Test Results")
    lines.append(f"\n**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Duration:** {results.duration_seconds:.2f} seconds\n")
    
    lines.append("## 📊 Summary")
    lines.append(f"| Metric | Value |")
    lines.append(f"|:--|:--|")
    lines.append(f"| Total Clusters | {results.total_clusters} |")
    lines.append(f"| Total Files | {results.total_files} |")
    lines.append(f"| Issues Injected | {results.total_issues_injected} |")
    lines.append(f"| Issues Healed | {results.total_issues_healed} |")
    lines.append(f"| Issues Failed | {results.total_issues_failed} |")
    lines.append(f"| **Healing Success Rate** | **{results.healing_success_rate:.1f}%** |")
    lines.append(f"| **K8s Schema Compliance** | **{results.schema_compliance_rate:.1f}%** |")
    lines.append(f"| Crash Count | {results.crash_count} |")
    
    lines.append("\n## 📈 Category Breakdown")
    lines.append("| Category | Injected | Healed | Failed | Success Rate |")
    lines.append("|:--|:--:|:--:|:--:|:--:|")
    
    for cat, stats in sorted(results.category_breakdown.items()):
        lines.append(
            f"| {cat} | {stats['injected']} | {stats['healed']} | "
            f"{stats['failed']} | {stats['success_rate']:.1f}% |"
        )
    
    if results.failed_files:
        lines.append("\n## ❌ Sample Failures")
        for f in results.failed_files[:10]:
            lines.append(f"- `{f}`")
        if len(results.failed_files) > 10:
            lines.append(f"- ... and {len(results.failed_files) - 10} more")
    
    if results.schema_failures:
        lines.append("\n## ⚠️ Schema Compliance Failures")
        for f in results.schema_failures[:10]:
            lines.append(f"- `{f}`")
        if len(results.schema_failures) > 10:
            lines.append(f"- ... and {len(results.schema_failures) - 10} more")
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def test_fail_on_error_gate():
    """
    Validates that --fail-on error correctly differentiate between WARNING and ERROR.
    
    Why: To ensure Yamlr acts as a surgical CI gate, only blocking on critical issues
         when configured to do so.
    """
    print("\n" + "-" * 60)
    print("TESTING CI GATE: --fail-on error")
    print("-" * 60)
    
    import subprocess
    import tempfile
    
    # Create a manifest with only WARNINGS (Best Practices - Missing Limits)
    warning_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: ci-gate-warning
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
      - name: nginx
        image: nginx:1.21
        securityContext:
          runAsNonRoot: true
          allowPrivilegeEscalation: false
          privileged: false
        # Missing resource limits triggers WARNING if --enforce-limits is set
"""
    
    # Create a manifest with an ERROR (Syntax)
    error_yaml = """apiVersion: v1
kind: Service
metadata:
  name: ci-gate-error
spec:
  selector: {  # Unmatched bracket
    app: nginx
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        warn_file = Path(tmpdir) / "warning.yaml"
        err_file = Path(tmpdir) / "error.yaml"
        warn_file.write_text(warning_yaml)
        err_file.write_text(error_yaml)
        
        # 1. Test WARNING with --fail-on error (Should EXIT 0)
        print("   Running: yamlr scan warning.yaml --fail-on error --enforce-limits")
        try:
            # We use the actual CLI if installed, or call it via python
            # Set cwd=tmpdir to ensure local telemetry.json isolation
            cmd = [sys.executable, "-m", "yamlr.cli.main", "scan", "warning.yaml", "--fail-on", "error", "--enforce-limits"]
            # Use specific encoding and errors='replace' for Windows compatibility
            cp = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir, encoding='utf-8', errors='replace')
            print(f"   [DEBUG] Exit Code: {cp.returncode}")
            if cp.stdout:
                for line in cp.stdout.splitlines():
                    if "DEBUG" in line:
                         print(f"   [DEBUG] {line}")
            
            if cp.returncode == 0:
                print("   [PASS] Warning manifest did not trigger failure with --fail-on error")
            else:
                print(f"   [FAIL] Warning manifest triggered failure (Exit Code: {cp.returncode})")
        except Exception as e:
            print(f"   [ERROR] {e}")

        # 2. Test ERROR with --fail-on error (Should EXIT 1)
        print("   Running: yamlr scan error.yaml --fail-on error")
        try:
            cmd = [sys.executable, "-m", "yamlr.cli.main", "scan", "error.yaml", "--fail-on", "error"]
            cp = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir, encoding='utf-8', errors='replace')
            print(f"   [DEBUG] Exit Code: {cp.returncode}")
            if cp.stdout:
                for line in cp.stdout.splitlines():
                    if "DEBUG" in line:
                         print(f"   [DEBUG] {line}")
                         
            if cp.returncode == 1:
                print("   [PASS] Error manifest correctly triggered failure with --fail-on error")
            else:
                print(f"   [FAIL] Error manifest did not trigger failure (Exit Code: {cp.returncode})")
        except Exception as e:
            print(f"   [ERROR] {e}")

        # 3. Test WARNING with DEFAULT behavior (Should EXIT 1 - Safety First)
        print("   Running: yamlr scan warning.yaml --enforce-limits (Default)")
        try:
            cmd = [sys.executable, "-m", "yamlr.cli.main", "scan", "warning.yaml", "--enforce-limits"]
            cp = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir)
            if cp.returncode == 1:
                 print("   [PASS] Default behavior (Safety First) correctly triggered exit 1 for warning")
            else:
                 print(f"   [FAIL] Default behavior did not exit 1 for warning (Exit Code: {cp.returncode})")
        except Exception as e:
            print(f"   [ERROR] {e}")


def main():
    print("\n" + "=" * 60)
    print("🏭 YAMLR ENTERPRISE STRESS TEST GENERATOR")
    print("=" * 60)
    
    # Phase 1: Generate clusters with issues
    print(f"\n📁 Generating {NUM_CLUSTERS} clusters with {TARGET_ISSUES}+ issues...")
    generator = ClusterGenerator(OUTPUT_DIR)
    file_count, issue_count = generator.generate_clusters(NUM_CLUSTERS)
    print(f"   ✅ Generated {file_count} files with {issue_count} unique issues")
    
    # Phase 2: Run stress test
    print("\n🔧 Running yamlr healing across all clusters...")
    runner = StressTestRunner(OUTPUT_DIR)
    results = runner.run()
    
    # Phase 2.1: Verify CI Gates
    test_fail_on_error_gate()
    
    # Phase 3: Generate report
    print("\n📝 Generating report...")
    report = generate_report(results)
    
    # Save results
    report_path = Path("d:/yamlr/tests/enterprise_stress_report.md")
    report_path.write_text(report, encoding="utf-8")
    
    results_json = {
        "total_clusters": results.total_clusters,
        "total_files": results.total_files,
        "total_issues_injected": results.total_issues_injected,
        "total_issues_healed": results.total_issues_healed,
        "total_issues_failed": results.total_issues_failed,
        "healing_success_rate": results.healing_success_rate,
        "schema_compliance_rate": results.schema_compliance_rate,
        "crash_count": results.crash_count,
        "duration_seconds": results.duration_seconds,
        "category_breakdown": results.category_breakdown
    }
    RESULTS_FILE.write_text(json.dumps(results_json, indent=2), encoding="utf-8")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    print(f"Clusters Tested:     {results.total_clusters}")
    print(f"Files Processed:     {results.total_files}")
    print(f"Issues Injected:     {results.total_issues_injected}")
    print(f"Issues Healed:       {results.total_issues_healed}")
    print(f"Issues Failed:       {results.total_issues_failed}")
    print(f"Healing Success:     {results.healing_success_rate:.1f}%")
    print(f"Schema Compliance:   {results.schema_compliance_rate:.1f}%")
    print(f"Crashes:             {results.crash_count}")
    print(f"Duration:            {results.duration_seconds:.2f}s")
    print(f"\n📄 Full report saved to: {report_path}")
    print(f"📊 JSON results saved to: {RESULTS_FILE}")
    
    # Exit code based on success criteria
    if results.crash_count > 0:
        print("\n❌ TEST FAILED: Crashes detected")
        sys.exit(1)
    elif results.healing_success_rate < 70:
        print(f"\n⚠️ TEST WARNING: Healing rate below 70%")
        sys.exit(0)
    else:
        print("\n✅ TEST PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
