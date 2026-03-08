"""
Yamlr Enterprise: Open Policy Agent (OPA) Adapter
-------------------------------------------------
Integrates OPA/Rego policy decisions into the Yamlr healing pipeline.
Acts as a translation layer between OPA Violation JSON and Yamlr AnalysisResult.

Capabilities:
1. Ingests OPA JSON output.
2. Maps "deny" rules to Yamlr Findings.
3. Suggests auto-fixes based on policy annotations.

Author: Nishar A Sunkesala / Yamlr Team
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, List, Optional

try:
    from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
    from yamlr.models import ManifestIdentity
except ImportError:
    # Fallback for when running in isolation/tests
    from dataclasses import dataclass

    @dataclass
    class AnalysisResult:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        analyzer_name: str
        severity: str
        message: str
        resource_name: str
        resource_kind: str
        file_path: str
        rule_id: Optional[str] = None
        line_number: Optional[int] = None
        suggestion: Optional[str] = None
        fix_available: bool = False
        fix_id: Optional[str] = None

    class BaseAnalyzer:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        pass


logger = logging.getLogger("yamlr.pro.opa")


class OpaAnalyzer(BaseAnalyzer):
    """
    Enterprise Adapter for OPA/Gatekeeper policies.
    """

    def __init__(self, policy_path: str = None):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        import urllib.request

        # Use ruamel.yaml as it is our core dependency (avoiding extra PyYAML req)
        try:
            from yamlr.core.utils import get_hardened_yaml

            self.yaml = get_hardened_yaml(typ="safe")
        except ImportError:
            self.yaml = None

        self.urllib = urllib.request

        self.policy_path = self._prepare_policy(policy_path)
        self._rules = {}

    def _prepare_policy(self, raw_path: str) -> Optional[str]:
        """
        Zero Burden: Auto-download URLs and auto-extract Gatekeeper Rego.
        """
        if not raw_path:
            return None

        # 1. Handle Remote URL
        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            from yamlr.core.bridge import YamlrBridge
            if YamlrBridge.is_offline_mode():
                logger.debug(f"Offline Mode: Skipping remote policy download: {raw_path}")
                return None
            
            try:
                logger.debug(f"Downloading remote policy bundle: {raw_path}")
                # Use a temp file for the download (cache could be better but temp is safe)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".rego") as tmp:
                    # Security Hardening: Add explicit 30s timeout for remote policy fetch
                    with self.urllib.urlopen(raw_path, timeout=30) as response:
                        shutil.copyfileobj(response, tmp)
                    target_path = tmp.name
            except Exception as e:
                logger.error(f"Failed to download remote policy: {e}")
                return None
        else:
            target_path = raw_path

        # 2. Handle Gatekeeper ConstraintTemplate (YAML Wrapper)
        # Check by extension first, then content?
        if target_path.endswith((".yaml", ".yml")):
            if not self.yaml:
                logger.warning(
                    "ruamel.yaml not installed - cannot parse Gatekeeper templates"
                )
                return target_path

            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = self.yaml.load(f)

                if content and content.get("kind") == "ConstraintTemplate":
                    rego_code = (
                        content.get("spec", {}).get("targets", [{}])[0].get("rego", "")
                    )
                    if rego_code:
                        logger.debug(
                            f"Extracted Rego from Gatekeeper ConstraintTemplate: {target_path}"
                        )
                        with tempfile.NamedTemporaryFile(
                            mode="w", delete=False, suffix=".rego", encoding="utf-8"
                        ) as tmp:
                            tmp.write(rego_code)
                        return tmp.name
                    else:
                        logger.warning(
                            f"ConstraintTemplate found but no Rego target: {target_path}"
                        )
            except Exception as e:
                logger.warning(f"Failed to parse potential Gatekeeper YAML: {e}")
                # Fallthrough to treat it as a bundle (maybe it's a tar.gz named incorrectly? or just OPA data)

        return target_path

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "opa-universal-adapter"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        # We analyze content structure against policies
        return "content"

    def analyze(self, identities: List[Any]) -> List[AnalysisResult]:
        """
        Executes OPA policies against the discovered manifest identities.
        """
        results = []

        # 1. Serialize Input for OPA
        # Input can be List[ManifestIdentity] (Metadata) or List[Dict] (Content)
        opa_input = []
        for item in identities:
            if hasattr(item, "to_dict"):
                opa_input.append(item.to_dict())
            else:
                opa_input.append(item)

        # 2. Locate Policy
        policy = self.policy_path
        if not policy:
            # Fallback to embedded: src/yamlr/policies/core.rego
            # Mapping: yamlr/pro/opa_adapter.py -> yamlr/pro/ -> yamlr/policies/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            embedded_policy = os.path.join(base_dir, "policies", "core.rego")
            if os.path.exists(embedded_policy):
                policy = embedded_policy
                logger.debug(f"Using embedded OPA policy: {policy}")

        # 3. Try to run Real OPA Binary
        opa_exe = shutil.which("opa")
        opa_ran = False

        if opa_exe and policy:
            try:
                # Write input to temp file to avoid CLI arg length limits
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                ) as tmp:
                    json.dump(opa_input, tmp)
                    tmp_path = tmp.name

                try:
                    # Run OPA eval
                    # Query: data.yamlr.deny.violation
                    cmd = [
                        opa_exe,
                        "eval",
                        "--input",
                        tmp_path,
                        "--data",
                        policy,
                        "data.yamlr.deny.violation",
                        "--format",
                        "json",
                    ]

                    logger.debug(f"Executing OPA: {' '.join(cmd)}")
                    # Security Hardening: Add timeout to prevent DoS
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=30,
                    )

                    if proc.returncode == 0:
                        opa_ran = True
                        results.extend(self.ingest_opa_json(proc.stdout, identities))
                    else:
                        logger.warning(
                            f"OPA execution failed (RC={proc.returncode}): {proc.stderr}"
                        )

                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            except subprocess.TimeoutExpired:
                logger.error(
                    "OPA execution timed out (limit: 30s) - Skipping policy checks."
                )
            except Exception as e:
                logger.error(f"OPA Runner Critical Error: {e}")

        if opa_ran:
            return results

        # 4. Fallback: Python Policy Evaluator (Native Engine)
        logger.info(
            "OPA binary not detected - Falling back to Native Enterprise Policy Engine"
        )
        
        evaluator = PythonPolicyEvaluator()
        return evaluator.evaluate(identities)
        
    def ingest_opa_json(
        self, opa_output: str, identities: List[Any]
    ) -> List[AnalysisResult]:
        """
        Parses OPA JSON: { "result": [ { "expressions": [ { "value": [VIOLATIONS...] } ] } ] }
        """
        results = []
        try:
            data = json.loads(opa_output)
            if not data.get("result"):
                return []

            # Extract violations from the first result expression
            # Rego: package yamlr.deny
            # violation[{"msg": msg, "id": id, ...}] { ... }
            violations = data["result"][0]["expressions"][0]["value"]

            for v in violations:
                results.append(
                    AnalysisResult(
                        analyzer_name="OPA Policy Engine",
                        severity=v.get("severity", "WARNING").upper(),
                        message=v.get("msg", "Policy Violation"),
                        resource_name=v.get("resource_name", "Unknown"),
                        resource_kind=v.get("kind", "Unknown"),
                        file_path=v.get(
                            "file_path", "unknown"
                        ),  # OPA needs to pass this back
                        rule_id=v.get("rule_id", "custom-policy"),
                        suggestion=v.get("fix", None),
                        fix_available=bool(v.get("fix_id")),
                        fix_id=v.get("fix_id"),
                    )
                )

        except Exception as e:
            logger.error(f"Failed to parse OPA JSON: {e}")

        return results

class PythonPolicyEvaluator:
    """
    Enterprise Native Policy Engine execution when OPA binary is unavailable.
    Performs standard organizational checks (Labels, Registries, Workload Configs).
    """
    
    def evaluate(self, identities: List[Any]) -> List[AnalysisResult]:
        results = []
        for item in identities:
            doc = item.to_dict() if hasattr(item, "to_dict") else item
            fpath = getattr(item, "file_path", "unknown") if hasattr(item, "file_path") else "unknown"
            
            kind = doc.get("kind", "Unknown")
            metadata = doc.get("metadata", {})
            name = metadata.get("name", "Unnamed")
            labels = metadata.get("labels", {}) or {}
            annotations = metadata.get("annotations", {}) or {}
            
            # 1. Organization Enforcement: Required Labels
            required_labels = ["cost-center", "owner"]
            if kind in ["Deployment", "StatefulSet", "DaemonSet"]:
                missing = [l for l in required_labels if l not in labels]
                if missing:
                    results.append(
                        AnalysisResult(
                            analyzer_name="Native Policy Engine",
                            severity="error",
                            message=f"[Policy] Missing required organizational labels: {', '.join(missing)}",
                            rationale="Organizational policies mandate all workloads have ownership and billing tags for finops tracking.",
                            resource_name=name,
                            resource_kind=kind,
                            file_path=fpath,
                            rule_id="org-policy/required-labels",
                            suggestion=f"Add {', '.join(missing)} to metadata.labels",
                            fix_available=True,
                            fix_id="inject_required_labels"
                        )
                    )
            
            # 2. Ingress Enforcement: TLS Requirement
            if kind == "Ingress":
                spec = doc.get("spec", {})
                if not spec.get("tls"):
                    results.append(
                        AnalysisResult(
                            analyzer_name="Native Policy Engine",
                            severity="high",
                            message="[Policy] Ingress is missing TLS configuration.",
                            rationale="All external ingress routes must be encrypted with TLS per SOC2 compliance.",
                            resource_name=name,
                            resource_kind=kind,
                            file_path=fpath,
                            rule_id="org-policy/require-ingress-tls",
                        )
                    )
                    
            # 3. Workload: Disallow Default ServiceAccount
            if kind in ["Deployment", "StatefulSet", "DaemonSet", "Job", "Pod"]:
                spec = doc.get("spec", {}) if kind == "Pod" else doc.get("spec", {}).get("template", {}).get("spec", {})
                sa_name = spec.get("serviceAccountName")
                if sa_name == "default" or not sa_name:
                    results.append(
                        AnalysisResult(
                            analyzer_name="Native Policy Engine",
                            severity="warning",
                            message="[Policy] Usage of default ServiceAccount is prohibited.",
                            rationale="The default service account often has excessive permissions. Explicit, least-privilege service accounts must be used.",
                            resource_name=name,
                            resource_kind=kind,
                            file_path=fpath,
                            rule_id="org-policy/no-default-sa",
                        )
                    )
                    
        return results

