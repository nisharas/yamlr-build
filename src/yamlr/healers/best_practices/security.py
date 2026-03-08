from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger("yamlr.healers.security")

class SecurityContextHealer:
    """
    [Best Practice Healer]
    Enforces security hardening by ensuring containers run as non-root.
    Mapped to: yamlr heal --harden
    """
    
    DEFAULT_USER = 1000
    
    def heal_doc(self, doc: Dict[str, Any], harden: bool = False) -> bool:
        """
        Detects and optionally fixes insecure security contexts.
        Returns True if changes were made.
        """
        if not harden:
            return False

        modified = False
        kind = (doc or {}).get("kind") or ""
        spec = (doc or {}).get("spec") or {}

        if kind.lower() == "pod":
            pod_spec = spec
        else:
            tmpl = (spec.get("template") or {})
            pod_spec = (tmpl.get("spec") or {})

        # 1. Pod Level SecurityContext and Host Namespaces
        if pod_spec.get("hostNetwork") is True:
            pod_spec["hostNetwork"] = False
            modified = True
            logger.info("Hardened hostNetwork to false")

        if pod_spec.get("hostIPC") is True:
            pod_spec["hostIPC"] = False
            modified = True
            logger.info("Hardened hostIPC to false")

        if pod_spec.get("hostPID") is True:
            pod_spec["hostPID"] = False
            modified = True
            logger.info("Hardened hostPID to false")

        # Hardening Volumes: Remove hostPath, enforce emptyDir for safety
        volumes = pod_spec.get("volumes")
        if isinstance(volumes, list):
            for vol in volumes:
                if isinstance(vol, dict) and "hostPath" in vol:
                    del vol["hostPath"]
                    vol["emptyDir"] = {}
                    modified = True
                    logger.info(f"Hardened unsafe hostPath to emptyDir for volume {vol.get('name', 'unknown')}")

        pod_sc = pod_spec.get("securityContext")
        if pod_sc is None or not isinstance(pod_sc, dict):
            # We don't necessarily MUST have a pod-level SC if containers have them,
            # but for hardening, we'll ensure it exists or containers have them.
            pass
        
        # 2. Container Level SecurityContext
        containers = pod_spec.get("containers") or []
        init_containers = pod_spec.get("initContainers") or []
        
        all_containers = containers + init_containers
        
        for c in all_containers:
            if not isinstance(c, dict):
                continue

            changed = self._harden_container(c)
            if changed:
                modified = True

        return modified

    def _harden_container(self, container: Dict[str, Any]) -> bool:
        """Applies hardening to a single container."""
        modified = False
        sc = container.get("securityContext")
        
        if sc is None:
            # Inject full securityContext
            sc = {
                "runAsNonRoot": True,
                "runAsUser": self.DEFAULT_USER,
                "allowPrivilegeEscalation": False,
                "readOnlyRootFilesystem": True,
                "privileged": False,
                "capabilities": {
                    "drop": ["ALL"]
                }
            }
            container["securityContext"] = sc
            modified = True
            logger.info(f"Injected full security hardening for container {container.get('name', 'unknown')}")
        elif isinstance(sc, dict):
            # Check individual fields
            checks = [
                ("runAsNonRoot", True),
                ("allowPrivilegeEscalation", False),
                ("readOnlyRootFilesystem", True),
                ("privileged", False)
            ]
            
            for field, target in checks:
                if sc.get(field) != target:
                    sc[field] = target
                    modified = True
                    logger.info(f"Hardened {field} for container {container.get('name', 'unknown')}")
            
            if "runAsUser" not in sc:
                sc["runAsUser"] = self.DEFAULT_USER
                modified = True
                
            # Capabilities dropping
            caps = sc.get("capabilities") or {}
            if not isinstance(caps, dict):
                caps = {}
            
            drop = caps.get("drop") or []
            if "ALL" not in drop:
                if isinstance(drop, list):
                    drop.append("ALL")
                else:
                    drop = ["ALL"]
                caps["drop"] = drop
                sc["capabilities"] = caps
                modified = True
                logger.info(f"Ensured capabilities drop ALL for container {container.get('name', 'unknown')}")

        return modified
