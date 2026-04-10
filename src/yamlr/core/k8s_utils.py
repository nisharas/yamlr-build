import logging
from typing import Any, Dict, List, Optional

from yamlr.models import WORKLOAD_KINDS

logger = logging.getLogger("yamlr.core.k8s_utils")
from yamlr.core.forensics import ForensicLogger


def find_pod_spec(doc: Any) -> Optional[Any]:
    """Navigates a manifest to find the embedded PodSpec.
    
    Why: PodSpecs are located at different paths depending on Kind 
         (Pod vs Deployment vs Job).
    """
    if not hasattr(doc, "get"):
        return None

    kind = doc.get("kind", "Unknown")
    kind_lower = (kind or "unknown").lower()
    spec = doc.get("spec")

    if not spec or not hasattr(spec, "get"):
        return None

    # 1. Pod itself
    if kind_lower == "pod":
        return spec

    # 2. CronJob (nested .spec.jobTemplate.spec.template.spec)
    if kind_lower == "cronjob":
        jt = spec.get("jobTemplate", {})
        template = jt.get("spec", {}).get("template", {}) if hasattr(jt, "get") else {}
        return template.get("spec") if hasattr(template, "get") else None

    # 3. Workloads (Deployment, StatefulSet, DaemonSet, Job) 
    #    (nested .spec.template.spec)
    template = spec.get("template", {})
    if hasattr(template, "get"):
        return template.get("spec")

    return None

def extract_containers(doc: Any, kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extracts container lists from any supported K8s workload.
    
    Why: To provide healers with a direct, flattened list of container dicts 
         without worrying about the manifest hierarchy.
    """
    if not hasattr(doc, "get"):
        return []

    kind = kind or doc.get("kind", "")
    pod_spec = find_pod_spec(doc)

    if not pod_spec or not hasattr(pod_spec, "get"):
        return []

    containers = pod_spec.get("containers", [])
    init_containers = pod_spec.get("initContainers", [])

    results = []
    if isinstance(containers, list):
        results.extend([c for c in containers if hasattr(c, "get")])
    if isinstance(init_containers, list):
        results.extend([c for c in init_containers if hasattr(c, "get")])

    return results
