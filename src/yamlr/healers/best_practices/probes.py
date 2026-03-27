from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from yamlr.core.k8s_utils import extract_containers

if TYPE_CHECKING:
    from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.probes")
__all__ = ['ProbeHealer']


class ProbeHealer:
    """
    [Best Practice Healer]
    Ensures all containers have liveness and readiness probes defined.
    Mapped to: yamlr heal --enforce-probes
    """
    
    DEFAULT_PORT = 8080
    
    def heal_doc(
        self, 
        doc: Dict[str, Any], 
        enforce_probes: bool = False,
        context: Optional[HealContext] = None
    ) -> bool:
        """
        Detects and optionally fixes missing probes.
        Returns: True if changes were made.
        """
        has_finding_liveness = False
        has_finding_readiness = False
        
        if context:
            from yamlr.analyzers.rules import Rules
            has_finding_liveness = any(f.rule_id == Rules.MISSING_LIVENESS for f in context.findings)
            has_finding_readiness = any(f.rule_id == Rules.MISSING_READINESS for f in context.findings)

        should_fix = enforce_probes or has_finding_liveness or has_finding_readiness

        if not should_fix:
            return False

        modified = False
        # Use cached containers if context is available
        containers = context.container_context if context else extract_containers(doc)
        
        for c in containers:
            if not isinstance(c, dict):
                continue

            changed = self._ensure_probes(c, enforce_probes, has_finding_liveness, has_finding_readiness, context)
            if changed:
                modified = True

        return modified

    def _ensure_probes(
        self, 
        container: Dict[str, Any], 
        enforce_all: bool, 
        liveness_finding: bool, 
        readiness_finding: bool,
        context: Optional[HealContext] = None
    ) -> bool:
        """Injects default probes if missing."""
        modified = False
        
        # 1. Determine port and protocol
        port = self.DEFAULT_PORT
        protocol = "http" # Default to http if we find web ports
        
        ports = container.get("ports") or []
        if isinstance(ports, list) and len(ports) > 0:
            first_port = ports[0]
            if isinstance(first_port, dict):
                port_val = first_port.get("containerPort")
                if port_val:
                    port = port_val
                    # If port is common web port, use http
                    if port in [80, 8080, 3000, 5000, 8000]:
                        protocol = "http"
                    else:
                        protocol = "tcp"
        else:
            # If no ports defined, default to TCP for safety
            protocol = "tcp"

        # 2. Build probe structure
        if protocol == "http":
            handler = {
                "httpGet": {
                    "path": "/healthz",
                    "port": port
                }
            }
        else:
            handler = {
                "tcpSocket": {
                    "port": port
                }
            }

        default_probe = {
            **handler,
            "initialDelaySeconds": 5,
            "periodSeconds": 10,
            "timeoutSeconds": 1,
            "successThreshold": 1,
            "failureThreshold": 3
        }

        if "livenessProbe" not in container and (enforce_all or liveness_finding):
            container["livenessProbe"] = default_probe.copy()
            modified = True
            if context:
                from yamlr.core.stages.boundaries import MutationScope
                from yamlr.models import HealAction
                context.prescribe(HealAction(
                    stage="Shield",
                    action_type="harden",
                    target=f"containers[{container.get('name', 'unknown')}].livenessProbe",
                    description=f"Injected default livenessProbe ({protocol})",
                    rationale="Liveness probes ensure that the container is restarted if it enters an unhealthy state.",
                    suggestion="Define liveness probes for all production containers.",
                    severity="warning",
                    rule_id="rule/missing-liveness",
                    scope=MutationScope.SPEC_PROBES
                ))
            logger.info(f"Injected default livenessProbe ({protocol}) for container {container.get('name', 'unknown')}")

        if "readinessProbe" not in container and (enforce_all or readiness_finding):
            container["readinessProbe"] = default_probe.copy()
            modified = True
            if context:
                from yamlr.core.stages.boundaries import MutationScope
                from yamlr.models import HealAction
                context.prescribe(HealAction(
                    stage="Shield",
                    action_type="harden",
                    target=f"containers[{container.get('name', 'unknown')}].readinessProbe",
                    description=f"Injected default readinessProbe ({protocol})",
                    rationale="Readiness probes ensure that the container only receives traffic when it is ready to handle it.",
                    suggestion="Define readiness probes for all production containers.",
                    severity="warning",
                    rule_id="rule/missing-readiness",
                    scope=MutationScope.SPEC_PROBES
                ))
            logger.info(f"Injected default readinessProbe ({protocol}) for container {container.get('name', 'unknown')}")

        return modified
