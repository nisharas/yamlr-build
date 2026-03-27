from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from yamlr.core.k8s_utils import extract_containers

if TYPE_CHECKING:
    from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.resources")
__all__ = ['ResourcesHealer']


class ResourcesHealer:
    """
    [Best Practice Healer]
    Ensures all containers have CPU/Memory requests and limits.
    """
    
    # Context-Aware Defaults (Pro Tier)
    CONTEXT_DEFAULTS = {
        "app": {
            "requests": {"cpu": "250m", "memory": "128Mi"},
            "limits": {"cpu": "500m", "memory": "256Mi"}
        },
        "sidecar": {
            "requests": {"cpu": "50m", "memory": "32Mi"},
            "limits": {"cpu": "100m", "memory": "64Mi"}
        },
        "pause": {
            "requests": {"cpu": "5m", "memory": "8Mi"},
            "limits": {"cpu": "10m", "memory": "16Mi"}
        }
    }

    def __init__(self, profiles: Optional[Dict[str, Any]] = None, vpa_targets: Optional[List[str]] = None):
        """
        Why: Support dynamic policy injection. [Phase 8]
        """
        self.resource_profiles = profiles if profiles else self.CONTEXT_DEFAULTS
        self.vpa_targets = vpa_targets or []

    
    def _detect_context(self, container_name: str, image: str = "") -> str:
        """Heuristically detects the container context."""
        name = container_name.lower()
        img = image.lower()
        
        # Sidecar detection
        sidecar_indicators = ["istio-proxy", "envoy", "vault-agent", "linkerd", "proxy", "agent", "logger", "fluent-bit"]
        if any(ind in name for ind in sidecar_indicators) or any(ind in img for ind in sidecar_indicators):
            return "sidecar"
            
        # Pause/Infrastructure detection
        if "pause" in name or "pause" in img or "k8s.gcr.io/pause" in img:
            return "pause"
            
        return "app"

    def heal_doc(
        self, 
        doc: Dict[str, Any], 
        enforce_defaults: bool = False,
        context: Optional[HealContext] = None
    ) -> bool:
        """
        Injects resource limits into the document in-place.
        Returns: True if changes were made.
        """
        modified = False
        kind = doc.get("kind", "unknown")
        name = doc.get("metadata", {}).get("name", "unknown")
        
        # Determine if we have findings that require a fix
        has_finding_requests = False
        has_finding_limits = False
        
        if context:
            from yamlr.analyzers.rules import Rules
            has_finding_requests = any(f.rule_id == Rules.RESOURCE_REQUESTS and f.resource_name == name for f in context.findings)
            has_finding_limits = any(f.rule_id == Rules.RESOURCE_LIMITS and f.resource_name == name for f in context.findings)

        # [PARITY] Run structural normalization first
        all_containers = context.container_context if context and context.container_context else extract_containers(doc, kind)
        
        for c in all_containers:
            if self.normalize_structure(c, context):
                modified = True

        should_fix = enforce_defaults or has_finding_requests or has_finding_limits
        if not should_fix:
            return modified

        for c in all_containers:
            if not isinstance(c, dict) and not (hasattr(c, "is_map") and c.is_map):
                continue

            container_name = c.get("name", "")
            res = c.get("resources") or {}
            if not isinstance(res, dict): res = {}
            
            req = res.get("requests") or {}
            lim = res.get("limits") or {}
            local_mod = False
            
            ctx = self._detect_context(container_name, c.get("image", ""))
            profiles = getattr(self, "resource_profiles", self.CONTEXT_DEFAULTS)
            defaults = profiles.get(ctx, profiles.get("app", self.CONTEXT_DEFAULTS["app"]))
            
            if "cpu" not in req and (enforce_defaults or has_finding_requests):
                req["cpu"] = defaults["requests"]["cpu"]
                local_mod = True
            if "memory" not in req and (enforce_defaults or has_finding_requests):
                req["memory"] = defaults["requests"]["memory"]
                local_mod = True
                
            if "cpu" not in lim and (enforce_defaults or has_finding_limits):
                lim["cpu"] = defaults["limits"]["cpu"]
                local_mod = True
            if "memory" not in lim and (enforce_defaults or has_finding_limits):
                lim["memory"] = defaults["limits"]["memory"]
                local_mod = True

            if local_mod:
                res["requests"] = req
                res["limits"] = lim
                c["resources"] = res
                modified = True
                if context:
                    from yamlr.core.stages.boundaries import MutationScope
                    from yamlr.models import HealAction
                    context.prescribe(HealAction(
                        stage="Shield",
                        action_type="harden",
                        target=f"{kind}/{name}.spec.containers[{container_name}].resources",
                        description=f"Injected default resource limits for container '{container_name}'",
                        rationale="Containers without resource limits can cause cluster-wide instability and OOM kills.",
                        suggestion="Define explicit CPU and Memory requests/limits for all containers.",
                        severity="warning",
                        rule_id="rule/resource-limits",
                        scope=MutationScope.SPEC_RESOURCES
                    ))

        return modified

    def normalize_structure(self, container: Dict[str, Any], context: Optional[HealContext] = None) -> bool:
        """
        Canonicalize container.resources structure by moving misnested cpu/memory into requests.
        
        Why: Standardizes common user errors where resources are specified as flat keys 
             instead of nested under 'requests' or 'limits'.
        """
        if not isinstance(container, dict):
            return False

        res = container.get("resources")
        if res is None:
            return False

        modified = False
        if not isinstance(res, dict):
            if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                res = res[0]
                container["resources"] = res
                modified = True
            else:
                res = {}
                container["resources"] = res
                modified = True

        requests = res.get("requests")
        if not isinstance(requests, dict):
            requests = {}
            res["requests"] = requests
            # We don't mark 'modified' yet unless we actually move something

        if "cpu" in res:
            modified = True
            if context:
                from yamlr.core.stages.boundaries import MutationScope
                from yamlr.models import HealAction
                context.prescribe(HealAction(
                    stage="Shield",
                    action_type="repair",
                    target="resources.cpu",
                    description="Structural Cleanup: Moved misnested 'cpu' into resources.requests",
                    rationale="Kubernetes requires 'cpu' to be nested under requests or limits.",
                    suggestion="Ensure resource requests/limits are properly nested.",
                    rule_id="rule/structural-fix",
                    scope=MutationScope.STRUCTURAL
                ))
        if "memory" in res:
            requests.setdefault("memory", res.pop("memory"))
            modified = True
            if context:
                from yamlr.core.stages.boundaries import MutationScope
                from yamlr.models import HealAction
                context.prescribe(HealAction(
                    stage="Shield",
                    action_type="repair",
                    target="resources.memory",
                    description="Structural Cleanup: Moved misnested 'memory' into resources.requests",
                    rationale="Kubernetes requires 'memory' to be nested under requests or limits.",
                    suggestion="Ensure resource requests/limits are properly nested.",
                    rule_id="rule/structural-fix",
                    scope=MutationScope.STRUCTURAL
                ))

        return modified

