"""
Yamlr CATALOG PIPELINE
----------------------
Automates the retrieval and distillation of Kubernetes OpenAPI schemas.
This ensures Yamlr stays compatible with the latest K8s releases without 
manual updates.

Usage:
  python scripts/catalog_pipeline.py --version 1.31
"""

import json
import argparse
import urllib.request
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("catalog-pipeline")

# Core resources that Yamlr focuses on for validation and healing
CORE_RESOURCES = [
    "Namespace", "ServiceAccount", "Pod", "PodTemplateSpec", "PodSpec", 
    "PodSecurityContext", "ContainerSecurityContext", "Probe", "Deployment", 
    "StatefulSet", "DaemonSet", "JobSpec", "Job", "JobTemplateSpec", "CronJob", 
    "Service", "Ingress", "ConfigMap", "Secret", "ReplicaSet", 
    "PersistentVolume", "PersistentVolumeClaim"
]

# Mapping of distilled names to their full OpenAPI definition paths (heuristics)
NAME_MAP_REVERSE = {
    "Pod": "io.k8s.api.core.v1.Pod",
    "PodSpec": "io.k8s.api.core.v1.PodSpec",
    "Deployment": "io.k8s.api.apps.v1.Deployment",
    "Service": "io.k8s.api.core.v1.Service",
    "ConfigMap": "io.k8s.api.core.v1.ConfigMap",
    "Secret": "io.k8s.api.core.v1.Secret",
    "Namespace": "io.k8s.api.core.v1.Namespace",
    "ServiceAccount": "io.k8s.api.core.v1.ServiceAccount",
    "PodTemplateSpec": "io.k8s.api.core.v1.PodTemplateSpec",
    "PodSecurityContext": "io.k8s.api.core.v1.PodSecurityContext",
    "ContainerSecurityContext": "io.k8s.api.core.v1.ContainerSecurityContext",
    "Probe": "io.k8s.api.core.v1.Probe",
    "StatefulSet": "io.k8s.api.apps.v1.StatefulSet",
    "DaemonSet": "io.k8s.api.apps.v1.DaemonSet",
    "Job": "io.k8s.api.batch.v1.Job",
    "JobSpec": "io.k8s.api.batch.v1.JobSpec",
    "JobTemplateSpec": "io.k8s.api.batch.v1.JobTemplateSpec",
    "CronJob": "io.k8s.api.batch.v1.CronJob",
    "Ingress": "io.k8s.api.networking.k8s.io.v1.Ingress",
    "ReplicaSet": "io.k8s.api.apps.v1.ReplicaSet",
    "PersistentVolume": "io.k8s.api.core.v1.PersistentVolume",
    "PersistentVolumeClaim": "io.k8s.api.core.v1.PersistentVolumeClaim",
}

# Sub-components that we want to flatten into parent fields rather than keeping as refs
FLATTEN_COMPONENTS = [
    "io.k8s.api.core.v1.Container",
    "io.k8s.api.core.v1.Volume",
    "io.k8s.api.core.v1.ContainerPort",
    "io.k8s.api.core.v1.EnvVar",
    "io.k8s.api.core.v1.ResourceRequirements",
    "io.k8s.api.core.v1.HTTPGetAction",
    "io.k8s.api.core.v1.TCPSocketAction",
    "io.k8s.api.core.v1.ExecAction",
    "io.k8s.api.core.v1.ResourceList",
    "io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta"
]

class CatalogDistiller:
    def __init__(self, openapi_data: Dict[str, Any]):
        self.definitions = openapi_data.get("definitions", {})
        # Inverse NAME_MAP for easy lookup
        self.full_to_short = {v: k for k, v in NAME_MAP_REVERSE.items()}
        self.distilled = {}

    def distill(self, resource_names: List[str]):
        """Main entry point to distill specific resources."""
        for name in resource_names:
            full_name = NAME_MAP_REVERSE.get(name)
            if full_name and full_name in self.definitions:
                self.distilled[name] = self._process_definition(full_name, depth=0)
            else:
                logger.debug(f"Resource {name} not found in OpenAPI definitions (full name: {full_name})")

        return self.distilled

    def _process_definition(self, def_full_name: str, depth: int) -> Dict[str, Any]:
        """Process a definition into distilled format."""
        if depth > 5: # Safety break for deep recursions
            return {"type": "object"}

        definition = self.definitions.get(def_full_name, {})
        result = {"fields": {}}
        
        properties = definition.get("properties", {})
        for prop_name, prop_data in properties.items():
            result["fields"][prop_name] = self._process_property(prop_data, depth + 1)
            
        return result

    def _process_property(self, prop_data: Dict[str, Any], depth: int) -> Dict[str, Any]:
        """Convert an OpenAPI property to Yamlr format."""
        
        # Handle References
        if "$ref" in prop_data:
            ref_path = prop_data["$ref"]
            ref_full_name = ref_path.split("/")[-1]
            
            # If it's a top-level distilled resource, use its ref name
            if ref_full_name in self.full_to_short:
                return {"ref": self.full_to_short[ref_full_name]}
            
            # If it's a component we want to FLATTEN, recursively process it
            if ref_full_name in FLATTEN_COMPONENTS or depth < 3:
                expanded = self._process_definition(ref_full_name, depth)
                return {"type": "object", "fields": expanded.get("fields", {})}

            return {"type": "object"}

        # Handle Arrays
        if prop_data.get("type") == "array":
            items = prop_data.get("items", {})
            res = {"type": "array"}
            
            # Recurse into item type
            item_distilled = self._process_property(items, depth)
            
            if "ref" in item_distilled:
                res["item_type"] = "object"
                # If we have the definition for the ref, try to include fields for validation
                ref_path = items.get("$ref")
                if ref_path:
                    ref_name = ref_path.split("/")[-1]
                    expanded = self._process_definition(ref_name, depth)
                    res["fields"] = expanded.get("fields", {})
            elif "fields" in item_distilled:
                res["item_type"] = "object"
                res["fields"] = item_distilled["fields"]
            elif "type" in item_distilled:
                res["item_type"] = item_distilled["type"]
            else:
                res["item_type"] = "object"
                
            return res

        # Handle Simple Types
        openapi_type = prop_data.get("type")
        if openapi_type == "string":
            return {"type": "string"}
        if openapi_type == "integer":
            return {"type": "integer"}
        if openapi_type == "boolean":
            return {"type": "boolean"}
        if openapi_type == "number":
            return {"type": "number"}
        
        # Special K8s int-or-string
        if "x-kubernetes-int-or-string" in prop_data:
            return {"type": "int_or_string"}

        return {"type": "object"}

def get_openapi_url(version: str) -> str:
    # v1.31 -> v1.31.0
    tag = f"v{version.lstrip('v')}"
    if tag.count('.') == 1:
        tag += ".0"
    return f"https://raw.githubusercontent.com/kubernetes/kubernetes/{tag}/api/openapi-spec/swagger.json"

def main():
    parser = argparse.ArgumentParser(description="Distill K8s OpenAPI to Yamlr Catalog")
    parser.add_argument("--version", required=True, help="K8s version (e.g., 1.31)")
    parser.add_argument("--output", help="Output path")
    args = parser.parse_args()

    url = get_openapi_url(args.version)
    logger.info(f"Downloading OpenAPI spec for {args.version} from {url}...")
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Failed to download or parse OpenAPI spec: {e}")
        sys.exit(1)

    distiller = CatalogDistiller(data)
    distilled_data = distiller.distill(CORE_RESOURCES)

    output_path = args.output or f"k8s_v{args.version.lstrip('v')}_distilled.json"
    with open(output_path, "w") as f:
        json.dump(distilled_data, f, indent=2)

    logger.info(f"Successfully distilled catalog to {output_path}")

if __name__ == "__main__":
    main()
