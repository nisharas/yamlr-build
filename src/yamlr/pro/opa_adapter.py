"""
Yamlr Enterprise (Pro): Open Policy Agent (OPA) Adapter
-------------------------------------------------
Integrates OPA/Rego policy decisions into the Yamlr healing pipeline.
Acts as a translation layer between OPA Violation JSON and Yamlr AnalysisResult.

Capabilities:
1. Ingests OPA JSON output.
2. Maps "deny" rules to Yamlr Findings.
3. Suggests auto-fixes based on policy annotations.

Author: Nishar A Sunkesala / Yamlr Team
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import signal
import atexit
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, List, Optional

__all__ = ['OpaAnalyzer', 'PythonPolicyEvaluator']

try:
    from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
    from yamlr.models import ManifestIdentity
    from yamlr.core.remediation import RemediationRegistry
    from yamlr.core.exceptions import YamlrSecurityError
except ImportError:
    # Fallback for when running in isolation/tests
    from dataclasses import dataclass

    @dataclass
    class AnalysisResult:
        """Structured container for OPA violation findings.
        
        Why: To provide a lightweight result object when running the adapter in isolation.
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
        rationale: Optional[str] = None
        fix_available: bool = False
        fix_id: Optional[str] = None

    class BaseAnalyzer:
        """Abstract base for OPA-integrated analyzers.
        """
        pass


logger = logging.getLogger("yamlr.pro.opa")


class OpaAnalyzer(BaseAnalyzer):
    """
    Enterprise Adapter for OPA/Gatekeeper policies.
    """

    def __init__(self, policy_path: str = None):
        """Initializes the OPA adapter and extractsRego policies from source.
        
        Args:
            policy_path: Path to a .rego file, YAML template, or remote URL.
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
            return self._download_remote_policy(raw_path)
        else:
            target_path = raw_path

        # 2. Handle Gatekeeper ConstraintTemplate (YAML Wrapper)
        if target_path.endswith((".yaml", ".yml")):
            return self._extract_gatekeeper_rego(target_path)

        # 3. Handle Tarball Bundles
        if target_path.endswith(".tar.gz"):
            return self._extract_tar_bundle(target_path)

        return target_path

    def _is_bundle(self, path: str) -> bool:
        """
        Determines if the path is an OPA bundle.
        Why: OPA requires different flags for single policy files vs bundles.
        """
        if not path or not os.path.exists(path):
            return False
            
        if os.path.isdir(path):
            # If it's a directory, we treat it as a bundle
            return True
            
        if path.endswith(".tar.gz"):
            # OPA natively supports .tar.gz bundles
            return True
            
        return False

    def _extract_tar_bundle(self, path: str) -> str:
        """
        Extracts a .tar.gz bundle to a temporary directory if it's external.
        Note: OPA can read tarballs directly, but we might want to inspect it.
        For now, we just pass the path through as OPA handles it, 
        but we mark it for the execution logic.
        """
        return path

    def _download_remote_policy(self, url: str) -> Optional[str]:
        from yamlr.core.bridge import YamlrBridge
        if YamlrBridge.is_offline_mode():
            logger.debug(f"Offline Mode: Skipping remote policy download: {url}")
            return None
        
        # [Security] Enforce HTTPS and Domain Allowlist (VULN-003)
        if not url.startswith("https://"):
            logger.error(f"Insecure Remote Policy: Only HTTPS is permitted for policy downloads ({url})")
            return None
            
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        ALLOWED_DOMAINS = {"github.com", "raw.githubusercontent.com", "auth.yamlr.dev"}
        if domain not in ALLOWED_DOMAINS:
             logger.error(f"Untrusted Policy Domain: '{domain}' is not in the trusted allowlist.")
             return None
        
        MAX_SIZE = 5 * 1024 * 1024
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".rego") as tmp:
                tmp_path = tmp.name
                with self.urllib.urlopen(url, timeout=30) as response:
                    # [Security] Don't trust Content-Length alone; it can be spoofed or missing
                    # We read in chunks and enforce MAX_SIZE manually.
                    total_downloaded = 0
                    CHUNK_SIZE = 8192
                    
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        total_downloaded += len(chunk)
                        if total_downloaded > MAX_SIZE:
                            raise IOError(f"Policy Too Large: Exceeded {MAX_SIZE} bytes during streaming")
                        tmp.write(chunk)
                return tmp_path
        except Exception as e:
            logger.error(f"Remote policy error for {url}: {e}")
            if tmp_path and os.path.exists(tmp_path): os.unlink(tmp_path)
            return None

    def _extract_gatekeeper_rego(self, path: str) -> str:
        MAX_REGO_SIZE = 10 * 1024 * 1024 # 10MB [PARTIAL-3]
        if not self.yaml:
            logger.warning(
                "ruamel.yaml not installed - cannot parse Gatekeeper templates"
            )
            return path
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = self.yaml.load(f)
            if content and content.get("kind") == "ConstraintTemplate":
                rego = content.get("spec", {}).get("targets", [{}])[0].get("rego", "")
                if rego:
                    if len(rego) > MAX_REGO_SIZE:
                        raise ValueError(f"Extracted Rego too large: {len(rego)} bytes")
                    logger.debug(
                        f"Extracted Rego from Gatekeeper ConstraintTemplate: {path}"
                    )
                    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".rego", encoding="utf-8") as tmp:
                        tmp.write(rego)
                    return tmp.name
                else:
                    logger.warning(
                        f"ConstraintTemplate found but no Rego target: {path}"
                    )
        except (OSError, IOError, AttributeError) as e:
            logger.warning(f"Failed to parse potential Gatekeeper YAML: {e}")
        return path

    @property
    def name(self) -> str:
        """Returns the strategic identifier for the OPA adapter."""
        return "opa-universal-adapter"

    @property
    def analyzer_type(self) -> str:
        """Categorizes this analyzer as a content-based validator."""
        # We analyze content structure against policies
        return "content"


    def analyze(self, identities: List[Any], **kwargs) -> List[AnalysisResult]:
        # [PHASE-9] Support static reports
        if self.policy_path and self.policy_path.endswith(".json"):
            report = self._read_static_report(self.policy_path)
            if report: return self.ingest_opa_json(report, identities)

        opa_input = [item.to_dict() if hasattr(item, "to_dict") else item for item in identities]
        policy = self.policy_path or self._get_embedded_policy()
        
        opa_exe = shutil.which("opa")
        if opa_exe and policy:
            return self._run_opa_binary(opa_exe, policy, opa_input, identities)

        try:
            from yamlr.core.bridge import YamlrBridge
            YamlrBridge.get_license_manager().track_usage("opa_analysis_triggered", 1)
        except Exception: pass

        logger.warning(
            "🛡️ OPA binary not detected - Falling back to Native Engine. "
            "WARNING: Native engine provides reduced security coverage compared to OPA-based scanning."
        )
        return PythonPolicyEvaluator().evaluate(identities)

    def _read_static_report(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if '"result"' in content or '"expressions"' in content:
                    return content
        except Exception: pass
        return None

    def _get_embedded_policy(self) -> Optional[str]:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        embedded = os.path.join(base_dir, "policies", "core.rego")
        return embedded if os.path.exists(embedded) else None

    def _run_opa_binary(self, exe: str, policy: str, input_data: list, identities: list) -> List[AnalysisResult]:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
                json.dump(input_data, tmp)
                tmp_path = tmp.name
                # [PARTIAL-2] Register persistent cleanup for abnormal exits
                self._register_cleanup(tmp_path)
            
            is_bundle = self._is_bundle(policy)
            eval_flag = "--bundle" if is_bundle else "--data"
            
            # [Security] Use '--' to prevent Option Injection (VULN-002)
            # Why: Ensures 'policy' is always treated as a positional argument even if it starts with '-'.
            cmd = [exe, "eval", "--input", tmp_path, eval_flag, "--", policy, "data.yamlr.deny.violation", "--format", "json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                return self.ingest_opa_json(proc.stdout, identities)
            else:
                msg = f"OPA eval failed with exit code {proc.returncode}: {proc.stderr}"
                logger.error(msg)
                raise YamlrSecurityError(
                    f"OPA Policy Execution Failure: {proc.stderr[:200]}",
                    remediation="Verify your OPA policies for syntax errors or check if the 'opa' binary is functional."
                )
        except YamlrSecurityError:
            raise
        except Exception as e:
            logger.error(f"OPA error: {e}")
            raise YamlrSecurityError(f"Unexpected OPA error: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path): os.unlink(tmp_path)

    def _register_cleanup(self, path: str):
        """Ensures file is removed even on SIGTERM or abnormal exit."""
        def _silent_remove():
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception: pass

        atexit.register(_silent_remove)
        # Register for common termination signals
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                def _handle_signal(s, f):
                    _silent_remove()
                    import sys
                    sys.exit(1)
                signal.signal(sig, _handle_signal)
            except (ValueError, RuntimeError):
                pass # Skip if not in main thread or not supported

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
                res_kind = v.get("kind") or v.get("resource_kind", "Unknown")
                res_name = v.get("resource_name") or v.get("name", "Unknown")
                
                # Handle "Deployment/name" format if present
                if v.get("resource") and "/" in v["resource"]:
                    res_kind, res_name = v["resource"].split("/", 1)

                results.append(
                    AnalysisResult(
                        analyzer_name="OPA Policy Engine",
                        severity=v.get("severity", "WARNING").upper(),
                        message=v.get("msg", "Policy Violation"),
                        resource_name=res_name,
                        resource_kind=res_kind,
                        file_path=v.get(
                            "file_path", "unknown"
                        ),  # OPA needs to pass this back
                        rule_id=v.get("rule_id", "custom-policy"),
                        suggestion=v.get("fix", None),
                        fix_available=bool(v.get("fix_id")) or bool(RemediationRegistry.get_fix_id(v.get("rule_id", ""))),
                        fix_id=v.get("fix_id") or RemediationRegistry.get_fix_id(v.get("rule_id", "")),
                    )
                )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse OPA JSON: {e}")
            # [Security] Fail-Closed on parsing errors (VULN_012)
            raise YamlrSecurityError(
                f"OPA Result Processing Failure: {e}",
                remediation="Ensure the OPA policy returns the expected JSON structure for violations."
            )

        return results

class PythonPolicyEvaluator:
    """
    Enterprise Native Policy Engine execution when OPA binary is unavailable.
    Performs standard organizational checks (Labels, Registries, Workload Configs).
    """
    
    ENGINE_NAME = "Native Policy Engine"

    def evaluate(self, identities: List[Any]) -> List[AnalysisResult]:
        results = []
        for item in identities:
            doc = item.to_dict() if hasattr(item, "to_dict") else item
            fpath = getattr(item, "file_path", "unknown") if hasattr(item, "file_path") else "unknown"
            
            self._check_org_labels(doc, fpath, results)
            self._check_ingress_tls(doc, fpath, results)
            self._check_service_account(doc, fpath, results)
                    
        return results

    def _check_org_labels(self, doc: dict, fpath: str, results: list):
        kind, name = doc.get("kind"), doc.get("name", "Unnamed")
        labels = doc.get("labels") or {}
        if kind in ["Deployment", "StatefulSet", "DaemonSet"]:
            missing = [l for l in ["cost-center", "owner"] if l not in labels]
            if missing:
                results.append(AnalysisResult(
                    analyzer_name=self.ENGINE_NAME,
                    severity="error",
                    message=f"[Policy] Missing: {', '.join(missing)}",
                    resource_name=name, resource_kind=kind, file_path=fpath,
                    rule_id="org-policy/required-labels",
                    fix_available=True, fix_id="inject_required_labels"
                ))

    def _check_ingress_tls(self, doc: dict, fpath: str, results: list):
        if doc.get("kind") == "Ingress" and not doc.get("spec", {}).get("tls"):
            results.append(AnalysisResult(
                analyzer_name=self.ENGINE_NAME,
                severity="high",
                message="[Policy] Ingress missing TLS",
                resource_name=doc.get("name", "Unnamed"), resource_kind="Ingress", file_path=fpath,
                rule_id="org-policy/require-ingress-tls"
            ))

    def _check_service_account(self, doc: dict, fpath: str, results: list):
        kind = doc.get("kind")
        if kind in ["Deployment", "StatefulSet", "DaemonSet", "Job", "Pod"]:
            spec = doc.get("spec", {}) if kind == "Pod" else doc.get("spec", {}).get("template", {}).get("spec", {})
            if spec.get("serviceAccountName") in ["default", None]:
                results.append(AnalysisResult(
                    analyzer_name=self.ENGINE_NAME,
                    severity="warning",
                    message="[Policy] Prohibited default ServiceAccount",
                    resource_name=doc.get("name", "Unnamed"), resource_kind=kind, file_path=fpath,
                    rule_id="org-policy/no-default-sa"
                ))
