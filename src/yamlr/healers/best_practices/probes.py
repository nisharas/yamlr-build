from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger("yamlr.healers.probes")

class ProbeHealer:
    """
    [Best Practice Healer]
    Ensures all containers have liveness and readiness probes defined.
    Mapped to: yamlr heal --enforce-probes
    """
    
    DEFAULT_PORT = 8080
    
    def heal_doc(self, doc: Dict[str, Any], enforce_probes: bool = False) -> bool:
        """
        Detects and optionally fixes missing probes.
        Returns True if changes were made.
        """
        if not enforce_probes:
            return False

        modified = False
        kind = (doc or {}).get("kind") or ""
        spec = (doc or {}).get("spec") or {}

        # Usually only Deployments/StatefulSets/DaemonSets/Pods need probes
        if kind.lower() not in ["deployment", "statefulset", "daemonset", "pod", "job", "cronjob"]:
            return False

        if kind.lower() == "pod":
            pod_spec = spec
        elif kind.lower() == "cronjob":
             # JobTemplate -> Spec -> Template -> Spec
             job_tmpl = spec.get("jobTemplate") or {}
             job_spec = job_tmpl.get("spec") or {}
             tmpl = job_spec.get("template") or {}
             pod_spec = tmpl.get("spec") or {}
        else:
            tmpl = spec.get("template") or {}
            pod_spec = tmpl.get("spec") or {}

        containers = pod_spec.get("containers") or []
        for c in containers:
            if not isinstance(c, dict):
                continue

            changed = self._ensure_probes(c)
            if changed:
                modified = True

        return modified

    def _ensure_probes(self, container: Dict[str, Any]) -> bool:
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

        # 3. Check Liveness
        if "livenessProbe" not in container:
            container["livenessProbe"] = default_probe.copy()
            modified = True
            logger.info(f"Injected default livenessProbe ({protocol}) for container {container.get('name', 'unknown')}")

        # 4. Check Readiness
        if "readinessProbe" not in container:
            container["readinessProbe"] = default_probe.copy()
            modified = True
            logger.info(f"Injected default readinessProbe ({protocol}) for container {container.get('name', 'unknown')}")

        return modified
