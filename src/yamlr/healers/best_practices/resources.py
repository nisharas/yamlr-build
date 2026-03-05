from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger("yamlr.healers.resources")

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

    def heal_doc(self, doc: Dict[str, Any], structurer: Any = None, enforce_defaults: bool = False) -> bool:
        """
        Injects resource limits into the document in-place.
        Args:
            doc: The manifest dictionary.
            structurer: Optional structurer for normalization.
            enforce_defaults: If True, injects default values for missing requests/limits.
        Returns:
            True if changes were made.
        """
        modified = False
        kind = (doc or {}).get("kind") or ""
        spec = (doc or {}).get("spec") or {}

        if kind.lower() == "pod":
            pod_spec = spec
        else:
            tmpl = (spec.get("template") or {})
            pod_spec = (tmpl.get("spec") or {})

        containers = pod_spec.get("containers") or []
        init_containers = pod_spec.get("initContainers") or []
        
        all_containers = [("containers", containers), ("initContainers", init_containers)]

        for key, container_list in all_containers:
            for idx, c in enumerate(container_list):
                if not isinstance(c, dict):
                    continue

                # 1) Fix bad nesting (ports/resources/probes under envFrom items)
                cleaned = self._normalize_container_spec(c)

                # 2) Normalize resources structure (one mapping, not list)
                if structurer:
                    if "resources" in cleaned or enforce_defaults:
                        structurer.normalize_resources(cleaned)

                res = cleaned.get("resources") or {}
                req = res.get("requests") or {}
                lim = res.get("limits") or {}

                # 3) Apply Smart Defaults (Pro Logic)
                local_mod = False
                
                if enforce_defaults:
                    context = self._detect_context(cleaned.get("name", ""), cleaned.get("image", ""))
                    defaults = self.CONTEXT_DEFAULTS.get(context, self.CONTEXT_DEFAULTS["app"])
                    
                    if "cpu" not in req:
                        req["cpu"] = defaults["requests"]["cpu"]
                        local_mod = True
                    if "memory" not in req:
                        req["memory"] = defaults["requests"]["memory"]
                        local_mod = True
                        
                    if "cpu" not in lim:
                        lim["cpu"] = defaults["limits"]["cpu"]
                        local_mod = True
                    if "memory" not in lim:
                        lim["memory"] = defaults["limits"]["memory"]
                        local_mod = True

                if local_mod or cleaned != c:
                    res["requests"] = req
                    res["limits"] = lim
                    cleaned["resources"] = res
                    
                    # Final safeguard: if resources is empty and wasn't there, kill it
                    if not req and not lim and "resources" not in c:
                         del cleaned["resources"]

                    container_list[idx] = cleaned
                    modified = True

        if modified:
             if kind.lower() == "pod":
                 doc["spec"] = pod_spec
             else:
                 doc["spec"]["template"]["spec"] = pod_spec
             
        return modified

    def _normalize_container_spec(self, container: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix common structural corruption in Container specs.
        """
        if not isinstance(container, dict):
            return container

        cleaned = dict(container)  # shallow copy

        env_from = cleaned.get("envFrom")
        if isinstance(env_from, list):
            for item in env_from:
                if not isinstance(item, dict):
                    continue

                for key in ["ports", "readinessProbe", "livenessProbe", "resources"]:
                    if key in item and key not in cleaned:
                        cleaned[key] = item.pop(key)

        return cleaned
