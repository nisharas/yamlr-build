#!/usr/bin/env python3
"""
Stage 6.1: Security Safety Interlock
------------------------------------
Prevents unauthorized mutations to high-risk manifest fields.
Why: Enforces the 'Safety-First' trust pillar by blocking privileged 
     container escalations unless explicitly overridden by the user.
"""

import logging
from typing import Any

from yamlr.core.context import HealContext
from yamlr.core.exceptions import YamlrSecurityError
from yamlr.core.stages.base import PipelineStage

logger = logging.getLogger("yamlr.stages.interlock")

class StageSecurityInterlock(PipelineStage):
    """
    Blocks healing of manifests containing high-risk security anti-patterns.
    """

    def __init__(self, name: str):
        super().__init__(name)

    def run(self, context: HealContext):
        """Scans documents for privileged roots and blocks if found."""
        if not context.config or context.config.unrestricted:
            return {"success": True, "skipped": True}

        unsafe_found = []
        for doc in context.docs:
            data = doc.data if hasattr(doc, "data") else doc
            if self._is_unsafe(data):
                unsafe_found.append(f"{data.get('kind')}/{data.get('metadata', {}).get('name')}")

        if unsafe_found:
            msg = f"Safety Interlock Triggered! High-risk manifest(s) detected: {', '.join(unsafe_found)}. " \
                  "Use --unrestricted to bypass this safety guard."
            logger.error(msg)
            raise YamlrSecurityError(msg)

        return {"success": True}

    def _is_unsafe(self, data: Any) -> bool:
        """Heuristic check for privileged or host-level access."""
        if not isinstance(data, dict): return False
        
        # 1. privileged: true
        spec = data.get("spec", {})
        if not isinstance(spec, dict): return False
        
        containers = spec.get("containers") or []
        init_containers = spec.get("initContainers") or []
        
        for container in list(containers) + list(init_containers):
            sc = container.get("securityContext", {})
            if sc.get("privileged") is True: return True
            if sc.get("allowPrivilegeEscalation") is True: return True

        # 2. hostPath: / (Root)
        for vol in spec.get("volumes", []):
            hp = vol.get("hostPath", {})
            if hp and hp.get("path") in ("/", "/etc", "/var/run/docker.sock"):
                return True

        return False
