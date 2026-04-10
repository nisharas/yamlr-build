"""
Yamlr Emulation Stage - Phase 2 (Hybrid)
----------------------------------------
What: Injects ghost containers (sidecars) and performs server-side shadowing.
Why: To resolve 'Runtime Blindspots' where late-binding mutations break manifest logic.
"""

import logging
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from yamlr.core.stages.base import PipelineStage, StageResult, PipelineState
from yamlr.core.k8s_utils import find_pod_spec

logger = logging.getLogger("yamlr.stages.emulation")

class EmulationStage(PipelineStage):
    """
    Principal Stage for Manifest Virtualization.
    
    Why: To bridge the gap between static 'Git Intent' and dynamic 'Cluster Reality'.
    """

    def __init__(self):
        super().__init__(name="Emulation")
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """Loads sidecar ghost-templates from the core data vault."""
        try:
            # Determine data path relative to this file
            data_file = Path(__file__).parent.parent / "data" / "sidecars.json"
            if data_file.exists():
                with open(data_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load sidecar templates: {e}")
        return {}

    def execute(self, state: PipelineState, engine: Optional[Any] = None) -> StageResult:
        """
        Executes Emulation Logic (2A Offline or 2C Shadow).
        """
        # 1. Plan 2C: Server-Side Shadowing (The Gold Standard)
        if state.context.shadow:
            return self._execute_shadow_mode(state, engine)

        # 2. Plan 2A: Ghost Node Emulation (The Local Proxy)
        return self._execute_ghost_emulation(state)

    def _execute_ghost_emulation(self, state: PipelineState) -> StageResult:
        """Injects virtual ghost-nodes into the manifest graph."""
        global_providers = state.context.emulate or []

        if not global_providers and not self._detect_injection_labels(state):
             return StageResult(success=True)

        emulated_count = 0
        for doc in state.documents:
            emulated_count += self._emulate_single_doc(doc, global_providers, state)

        return StageResult(
            success=True,
            metadata={"emulated_containers": emulated_count}
        )

    def _emulate_single_doc(self, doc: Any, global_providers: List[str], state: PipelineState) -> int:
        """Processes emulation for a single document."""
        pod_spec = find_pod_spec(doc)
        if not pod_spec:
            return 0

        count = 0
        doc_providers = self._get_doc_providers(doc, global_providers)
        
        for provider in doc_providers:
            template = self.templates.get(provider.lower())
            if template:
                self._inject_ghost_container(pod_spec, template)
                count += 1
                state.context.audit_log.append(f"👻 Emulated: Injected {provider} ghost container.")
        return count

    def _get_doc_providers(self, doc: Any, global_providers: List[str]) -> List[str]:
        """Calculates the effective list of providers for a document (Explicit + Auto-Detected)."""
        providers = list(global_providers)
        labels = self._get_labels(doc)
        
        if labels.get("istio-injection") == "enabled" and "istio" not in providers:
            providers.append("istio")
            
        return providers

    def _execute_shadow_mode(self, state: PipelineState, engine: Any) -> StageResult:
        """
        Captures dynamic mutations via server-side dry-run.
        (Requires live KUBECONFIG/cluster connectivity).
        """
        if not engine:
            return StageResult(success=False, errors=["Engine instance required for shadow mode"])

        # We only shadow if we have the full content
        if not state.content:
            return StageResult(success=True) # Nothing to shadow

        try:
            # [Phase 4] PII Scrubbing: Sanitize env to prevent leakage of host-bound secrets
            scrubbed_env = self._scrub_env(os.environ.copy())

            # [SECURITY] We use --server-dry-run to capture mutations like Istio/Linkerd injections
            cmd = ["kubectl", "apply", "-f", "-", "--server-dry-run", "-o", "yaml"]
            
            # Use specific context if provided
            if hasattr(state.context, "kube_context") and state.context.kube_context:
                cmd.extend(["--context", state.context.kube_context])

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=scrubbed_env,
                text=True
            )
            
            stdout, stderr = process.communicate(input=state.content)

            if process.returncode != 0:
                logger.warning(f"Shadow mode failed (API error): {stderr}")
                return StageResult(success=False, errors=[f"Shadow mode API error: {stderr}"])

            # Reload documents from the server-synthesized output
            # This replaces the local AST with the mutated 'Final Reality'
            mutated_docs = engine.parser.load_all(stdout)
            state.documents = mutated_docs
            state.context.audit_log.append("🛰️ Shadow Mode: Manifest synchronized with cluster admission mutations.")
            
            return StageResult(success=True, metadata={"shadowed": True})

        except Exception as e:
            logger.error(f"Shadow mode execution failure: {e}")
            return StageResult(success=False, errors=[f"Subprocess failure: {e}"])

    def _scrub_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """
        Removes sensitive PII and non-K8s secrets from the environment.
        Why: Prevents accidental host-bound credential leakage into shadow logs or API calls.
        """
        sensitive_keys = {
            "AWS_SECRET_ACCESS_KEY", "AZURE_CLIENT_SECRET", "GOOGLE_APPLICATION_CREDENTIALS",
            "DB_PASSWORD", "SECRET_KEY", "API_KEY", "GCP_TOKEN", "SSH_AUTH_SOCK"
        }
        # Keep essential K8s/System vars
        for key in list(env.keys()):
            if any(s in key.upper() for s in ["PASSWORD", "SECRET", "TOKEN", "KEY"]):
                if key not in ("KUBECONFIG", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY"):
                    del env[key]
            elif key.upper() in sensitive_keys:
                del env[key]
        return env

    def _get_labels(self, doc: Any) -> Dict[str, str]:
        """Safely extracts labels from a manifest."""
        metadata = doc.get("metadata", {})
        if hasattr(metadata, "get"):
            return metadata.get("labels", {})
        return {}

    def _detect_injection_labels(self, state: PipelineState) -> bool:
        """Checks if any document in the state has injection-trigger labels."""
        for doc in state.documents:
            labels = self._get_labels(doc)
            if "istio-injection" in labels:
                return True
        return False

    def _inject_ghost_container(self, pod_spec: Any, template: Dict[str, Any]):
        """Inserts the ghost container into the in-memory pod_spec."""
        containers = pod_spec.get("containers")
        if containers is None:
            pod_spec["containers"] = []
            containers = pod_spec["containers"]

        # Check if already exists to avoid double-injection
        for c in containers:
            if c.get("name") == template.get("name"):
                return

        # [MODULARITY] We mark the node as virtual so cleaners don't try to save it to disk
        # (ruamel.yaml allows setting attributes on CommentedMap)
        from ruamel.yaml.comments import CommentedMap
        ghost = CommentedMap(template)
        ghost.yaml_set_start_comment("Yamlr Virtual Ghost Node: Emulated runtime sidecar")
        
        containers.append(ghost)
