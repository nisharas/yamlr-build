from typing import Any, Dict, List, Optional
import logging
from yamlr.models import WORKLOAD_KINDS

logger = logging.getLogger("yamlr.core.k8s_utils")

def find_pod_spec(doc: Any, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Safely navigates a manifest to find the embedded PodSpec.
    
    Why: Shared primitive for security auditing and container extraction.
         Prevents logic duplication across the engine.
    """
    # [HARDENING] Support RuamelNode-wrapped objects or raw dicts
    if hasattr(doc, "_node"):
        doc = doc._node
    elif not isinstance(doc, dict) and hasattr(doc, "data"):
        doc = doc.data

    # Use 'get' instead of isinstance(doc, dict) to be safe with CommentedMap
    if not hasattr(doc, "get"):
        return None

    kind = kind or doc.get("kind", "")
    if not kind:
        return None
    
    kind_lower = kind.lower()
    spec = doc.get("spec")
    
    # Unwrap spec too
    if hasattr(spec, "_node"):
        spec = spec._node
    
    if not spec or not hasattr(spec, "get"):
        return None
    
    # 1. Pod itself
    if kind_lower == "pod":
        with open("d:\\yamlr\\k8s_debug.log", "a") as f:
            keys = list(spec.keys()) if hasattr(spec, "keys") else "NOT_A_MAP"
            f.write(f"DEBUG: find_pod_spec Pod spec_keys={keys}\n")
        logger.debug("find_pod_spec Pod result=%s", spec is not None)
        return spec

    # 2. CronJob (nested .spec.jobTemplate.spec.template.spec)
    if kind_lower == "cronjob":
        jt = spec.get("jobTemplate", {})
        if hasattr(jt, "_node"): jt = jt._node
        
        template = jt.get("spec", {}).get("template", {}) if hasattr(jt, "get") else {}
        if hasattr(template, "_node"): template = template._node
        
        res = template.get("spec") if hasattr(template, "get") else None
        if hasattr(res, "_node"): res = res._node
        return res
    
    # 3. Standard workloads (nested .spec.template.spec)
    if kind_lower in ["deployment", "replicaset", "statefulset", "daemonset", "job", "replicationcontroller"]:
        template = spec.get("template", {})
        if not template:
            logger.debug("find_pod_spec %s has NO template in spec", kind)
            return None
            
        if hasattr(template, "_node"): template = template._node
        
        res = template.get("spec") if hasattr(template, "get") else None
        if hasattr(res, "_node"): res = res._node
        
        return res
    
    # Generic check
    template = spec.get("template", {})
    if hasattr(template, "_node"): template = template._node
    res = template.get("spec") if hasattr(template, "get") else None
    if res:
        if hasattr(res, "_node"): res = res._node
        return res
        
    return None

def extract_containers(doc: Any, kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extracts all containers (main and init) from a Kubernetes resource.
    
    Why: Centralizes traversal logic to prevent fragmentation and duplication
         across Analyzers and Healers. Supports all standard workload types.
    
    Args:
        doc: Raw Kubernetes manifest dictionary or YamlrNode.
        
    Returns:
        List of container dictionary objects.
    """
    if hasattr(doc, "_node"):
        doc = doc._node
    elif not isinstance(doc, dict) and hasattr(doc, "data"):
        doc = doc.data

    if not hasattr(doc, "get"):
        return []

    kind = kind or doc.get("kind", "")
    kind_lower = str(kind).lower()
    
    # Optimization: These known kinds never have embedded PodSpecs
    if kind_lower in ["configmap", "secret", "service", "ingress", "persistentvolume", "persistentvolumeclaim", "namespace", "networkpolicy"]:
        return []

    pod_spec = find_pod_spec(doc, kind)

    # pod_spec might be a RuamelNode or a dict
    if hasattr(pod_spec, "_node"):
        pod_spec = pod_spec._node

    if pod_spec is None or not hasattr(pod_spec, "get"):
        if kind_lower in WORKLOAD_KINDS or kind_lower == "replicaset":
             logger.debug("extract_containers FAILED to find pod_spec for workload %s", kind)
        return []

    containers = pod_spec.get("containers", [])
    logger.debug("extract_containers found %d containers for %s", len(containers or []), kind)
    with open("d:\\yamlr\\k8s_debug.log", "a") as f:
        f.write(f"DEBUG: extract_containers found {type(containers)} len={len(containers) if hasattr(containers, '__len__') else 'N/A'}\n")
        if hasattr(containers, "__iter__"):
            for i, c in enumerate(containers):
                 keys = list(c.keys()) if hasattr(c, "keys") else "N/A"
                 f.write(f"DEBUG: Container {i} keys={keys}\n")
    
    init_containers = pod_spec.get("initContainers", [])

    results = []
    if isinstance(containers, list):
        results.extend([c for c in containers if hasattr(c, "get")])
    if isinstance(init_containers, list):
        results.extend([c for c in init_containers if hasattr(c, "get")])

    return results
