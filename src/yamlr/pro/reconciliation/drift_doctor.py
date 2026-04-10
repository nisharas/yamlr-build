"""
Yamlr Enterprise (Pro): Drift Doctor
------------------------------------
Reconciles live Kubernetes cluster state with local manifests.

Why: To detect 'Infrastructure Drift' where manual changes in the cluster
     diverge from the GitOps source of truth.
"""

from __future__ import annotations

import difflib
import logging
import os
from typing import Any, Dict, List, Optional

import yaml
# Kubernetes imports are deferred to runtime in ClusterStateRetriever
# from kubernetes import client, config
# from kubernetes.client.rest import ApiException

from yamlr.core.engine.models import AnalysisResult

logger = logging.getLogger("yamlr.pro.drift")
__all__ = ["DriftDoctor", "ClusterStateRetriever"]


class ClusterStateRetriever:
    """Handles fetching live resources from the Kubernetes API.

    Why: To decouple cluster-state retrieval from reconciliation logic,
         allowing for offline simulation and mock-based testing of drift scenarios.
    """

    def __init__(self, context: Optional[str] = None):
        """Initializes the K8s client with optional context."""
        self.context = context
        self._initialized = False
        self._client = None
        self.loaded = True

    def _initialize(self):
        """Lazy initialization of the K8s client."""
        if self._initialized:
            return
        
        try:
            from kubernetes import client, config
            # Check for in-cluster config first (ArgoCD/Flux mode)
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                config.load_incluster_config()
            else:
                config.load_kube_config(context=self.context)
            self._client = client
            self._initialized = True
        except ImportError:
            logger.error("The 'kubernetes' Python package is required for drift detection.")
            raise ImportError("Please install 'kubernetes-python' to use this feature.")
        except Exception as e:
            logger.debug(f"Kubeconfig load failed: {e}")
            self._initialized = True # Mark as attempted
            self.loaded = False

    def get_live_resource(self, api_version: str, kind: str, name: str, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """Fetches a specific resource from the cluster."""
        self._initialize()
        if not self.loaded or not self._client:
            return None

        # [Mastery Pass] Dynamic API Client Resolution
        try:
            from kubernetes.client.rest import ApiException
            api_client = self._client.ApiClient()
            
            # 1. Handle Core V1 Types (Pod, Service, ConfigMap, Secret)
            if api_version == "v1":
                v1 = client.CoreV1Api(api_client)
                method_name = f"read_namespaced_{self._to_snake(kind)}"
                if hasattr(v1, method_name):
                    method = getattr(v1, method_name)
                    res = method(name, namespace)
                    return api_client.sanitize_for_serialization(res)
            
            # 2. Handle Grouped Types (Apps, Networking, etc.)
            group, version = api_version.split("/") if "/" in api_version else ("", api_version)
            resource_plural = f"{kind.lower()}s"
            
            # Specific AppsV1 fallback for high-traffic resources
            if group == "apps":
                apps_v1 = client.AppsV1Api(api_client)
                method_name = f"read_namespaced_{self._to_snake(kind)}"
                if hasattr(apps_v1, method_name):
                    method = getattr(apps_v1, method_name)
                    res = method(name, namespace)
                    return api_client.sanitize_for_serialization(res)
            
            # 3. Dynamic Custom Object Fallback
            dynamic_api = client.CustomObjectsApi(api_client)
            return dynamic_api.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=resource_plural,
                name=name
            )
            
        except ApiException as e:
            if e.status == 404:
                return None
            logger.debug(f"Drift: API error fetching {kind}/{name}: {e.status} {e.reason}")
        except Exception as e:
            logger.debug(f"Drift: Unexpected error: {e}")
        return None

    def _to_snake(self, name: str) -> str:
        """Converts CamelCase to snake_case for kubernetes-python methods."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class DriftDoctor:
    """Reconciles local manifests against live cluster state.

    Why: Provides the core forensic logic for 'Desired vs. Actual' state 
         reconciliation, enabling the Zero-Drift Trust Pillar.
    """

    def __init__(self, retriever: Optional[ClusterStateRetriever] = None):
        self.retriever = retriever or ClusterStateRetriever()

    def reconcile(self, local_manifest: Dict[str, Any], file_path: str = "unknown") -> List[AnalysisResult]:
        """
        Detects drift between local manifest and live resource.
        
        Reporting-only mode: Does not modify the cluster.
        """
        kind = local_manifest.get("kind")
        api_version = local_manifest.get("apiVersion")
        metadata = local_manifest.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace", "default")

        if not all([kind, api_version, name]):
            return []

        # [Mastery Pass] Resource Retrival
        live_manifest = self.retriever.get_live_resource(api_version, kind, name, namespace)
        if not live_manifest:
            return [
                AnalysisResult(
                    analyzer_name="DriftDoctor",
                    severity="WARNING",
                    message=f"Resource {kind}/{name} not found in cluster.",
                    resource_name=name,
                    resource_kind=kind,
                    file_path=file_path,
                    rule_id="drift/resource-missing",
                    suggestion="Ensure the resource is deployed or the kubeconfig context is correct."
                )
            ]

        # [Hardening] Filter out tactical metadata (UID, resourceVersion, status)
        local_clean = self._clean_manifest(local_manifest)
        live_clean = self._clean_manifest(live_manifest)

        if self._is_semantically_equal(local_clean, live_clean):
            return []

        # Generate Unified Diff for reporting
        diff = self._generate_diff(local_clean, live_clean, name)
        
        return [
            AnalysisResult(
                analyzer_name="DriftDoctor",
                severity="ERROR",
                message=f"Drift detected in {kind}/{name}. Live state differs from local manifest.",
                resource_name=name,
                resource_kind=kind,
                file_path=file_path,
                rule_id="drift/detected",
                suggestion="Review live changes or sync local manifest.",
                impact_description=f"Cluster state has diverged from GitOps source.\n\nDiff (Live vs Local):\n{diff}"
            )
        ]

    def _is_semantically_equal(self, local: Dict[str, Any], live: Dict[str, Any]) -> bool:
        """Deep comparison of manifest structure.

        Why: String comparison of YAML is O(N) and inconsistent across parsers.
             Deep dict comparison ensures we only flag real structural drift.
        """
        return self._dict_compare(local, live)

    def _dict_compare(self, d1: Any, d2: Any) -> bool:
        """Recursive semantic comparison of nested structures."""
        if type(d1) is not type(d2):
            return False

        if isinstance(d1, dict):
            if len(d1) != len(d2):
                return False
            for k, v in d1.items():
                if k not in d2:
                    return False
                if not self._dict_compare(v, d2[k]):
                    return False
            return True

        if isinstance(d1, list):
            if len(d1) != len(d2):
                return False
            # [Hardening] Order-sensitive list comparison for K8s arrays
            for i in range(len(d1)):
                if not self._dict_compare(d1[i], d2[i]):
                    return False
            return True

        return d1 == d2

    def _clean_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Removes status and transient metadata for semantic comparison."""
        # Work on a copy
        try:
            m = yaml.safe_load(yaml.dump(manifest))
        except Exception:
            return manifest
            
        m.pop("status", None)
        
        metadata = m.get("metadata", {})
        if isinstance(metadata, dict):
            # Transient K8s fields
            transient = [
                "uid", "resourceVersion", "generation", "creationTimestamp", 
                "managedFields", "selfLink"
            ]
            for field in transient:
                metadata.pop(field, None)
            
            # Filter specifically for kubectl.kubernetes.io/last-applied-configuration
            # and other noise-heavy annotations
            ann = metadata.get("annotations", {})
            if isinstance(ann, dict):
                ann.pop("kubectl.kubernetes.io/last-applied-configuration", None)
                ann.pop("deployment.kubernetes.io/revision", None)
                if not ann:
                    metadata.pop("annotations", None)
            
            m["metadata"] = metadata
        
        return m

    def _generate_diff(self, local: Dict[str, Any], live: Dict[str, Any], name: str) -> str:
        """Generates a color-neutral unified diff string."""
        local_yaml = yaml.dump(local, sort_keys=True).splitlines()
        live_yaml = yaml.dump(live, sort_keys=True).splitlines()
        
        diff = difflib.unified_diff(
            local_yaml, live_yaml, 
            fromfile=f"local/{name}", 
            tofile=f"live/{name}", 
            lineterm=""
        )
        return "\n".join(diff)


def handle_drift_command(args: Any):
    """Entrypoint for the 'yamlr drift' CLI command."""
    from yamlr.core.entrypoints.display import print_custom_header, print_analysis_report
    from yamlr.core.engine import YamlrEngine
    from yamlr.cli.context import get_active_workspace
    from yamlr.core.gatekeeper import ProGate
    
    # 🔒 Tier 1 Gate: Drift Doctor is a PRO feature
    ProGate.check("drift")
    
    print_custom_header("drift", True, title_override="Drift Doctor: Forensic Cluster Reconciliation")
    
    workspace = get_active_workspace()
    retriever = ClusterStateRetriever(context=getattr(args, "context", None))
    doctor = DriftDoctor(retriever=retriever)
    
    # Use Engine to find manifests
    engine = YamlrEngine.quick(workspace)
    manifest_paths = engine.discovery.find_manifests(workspace)
    
    all_findings = []
    print(f"🔍 Analyzing drift across {len(manifest_paths)} manifests...")
    
    for path in manifest_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                # Handle multi-document YAML
                docs = yaml.safe_load_all(f)
                for doc in docs:
                    if not doc: continue
                    findings = doctor.reconcile(doc, file_path=path)
                    all_findings.extend(findings)
        except Exception as e:
            logger.debug(f"Failed to process {path}: {e}")

    if not all_findings:
        print("\n✅ ZERO DRIFT: All local manifests match live cluster state.")
        return 0

    # Sort and print findings
    print_analysis_report(all_findings, output_format="text")
    
    # Return error if drift detected
    has_drift = any(f.rule_id == "drift/detected" for f in all_findings)
    return 1 if has_drift else 0
