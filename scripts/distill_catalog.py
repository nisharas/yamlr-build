#!/usr/bin/env python3
"""
Yamlr Catalog Distiller
-----------------------
Automates the conversion of raw Kubernetes OpenAPI (swagger.json) into
Yamlr's hyper-efficient "Distilled DNA" catalog format.

Why: To ensure Yamlr can support new K8s versions with sub-megabyte
     distribution footprints and sub-50ms load times.
"""

import argparse
import json
import logging
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("distiller")


class CatalogDistiller:
    """Distills raw OpenAPI schemas into efficient DNA maps."""

    def __init__(self, version: str):
        self.version = version.lstrip("v")
        self.raw_schema: Dict[str, Any] = {}
        self.distilled: Dict[str, Any] = {}
        self._ref_cache: Dict[str, str] = {}

    def fetch_raw_schema(self) -> bool:
        """Downloads the official swagger.json for the target version."""
        url = (
            f"https://raw.githubusercontent.com/kubernetes/kubernetes/"
            f"release-{self.version}/api/openapi-spec/swagger.json"
        )
        logger.info(f"Fetching raw OpenAPI schema for v{self.version}...")
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch schema: HTTP {response.status}")
                    return False
                self.raw_schema = json.loads(response.read())
                return True
        except Exception as e:
            logger.error(f"Network error: {e}")
            return False

    def distill(self) -> Dict[str, Any]:
        """Orchestrates the distillation process."""
        if not self.raw_schema:
            return {}

        definitions = self.raw_schema.get("definitions", {})

        # 1. Map all K8s internal keys to simpler names (e.g. io.k8s.api.core.v1.Pod -> Pod)
        self._build_ref_map(definitions)

        # 2. Process each major Kind
        # We focus on the core resources first
        for key, schema in definitions.items():
            if not self._is_k8s_resource(key):
                continue

            kind = key.split(".")[-1]
            if kind in self.distilled:
                # Resolve conflicts? Usually just use the first stable one or merge.
                continue

            self.distilled[kind] = self._process_node(schema)

        return self.distilled

    def _build_ref_map(self, definitions: Dict[str, Any]):
        """Maps long OpenAPI keys to simple Kind names."""
        for key in definitions:
            parts = key.split(".")
            kind = parts[-1]
            # [Hardening] Capture core types from apimachinery (IntOrString, Quantity, etc) and API resources
            if ("pkg" in key or "util" in key) and not any(x in key for x in ["intstr", "apis", "api"]):
                continue
            self._ref_cache[f"#/definitions/{key}"] = kind

    def _is_k8s_resource(self, key: str) -> bool:
        """Heuristic to identify a K8s object vs an internal utility struct."""
        # Capture Standard APIs, Extensions (CRDs), and Core Machinery types
        return (key.startswith("io.k8s.api.") or "apiextensions" in key or "apimachinery" in key) and not any(
            x in key for x in ["proto"]
        )

    def _process_node(self, node: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Recursively distills a schema node."""
        if depth > 12:  # Safety limit for circular refs
            return {"type": "object", "incomplete": True}

        # Case 1: Reference
        if "$ref" in node:
            ref = node["$ref"]
            return {"ref": self._ref_cache.get(ref, ref.split("/")[-1])}

        # Case 2: Array
        if node.get("type") == "array":
            items = node.get("items", {})
            return {
                "type": "array",
                "item_type": items.get("type", "object"),
                "fields": self._process_node(items, depth + 1).get("fields"),
            }

        # Case 3: Object with properties
        if node.get("type") == "object" or "properties" in node:
            distilled_node = {"type": "object", "fields": {}}
            props = node.get("properties", {})
            for name, detail in props.items():
                # Strip metadata we don't need for basic structure matching
                distilled_node["fields"][name] = self._process_node(detail, depth + 1)
            return distilled_node

        # Case 4: Multi-type (oneOf/anyOf) for types like IntOrString
        for key in ["oneOf", "anyOf"]:
            if key in node:
                return {"type": "multi", "options": [self._process_node(opt, depth + 1) for opt in node[key]]}

        # Case 5: Primitive
        return {"type": node.get("type", "string")}

    def save(self, output_path: Path):
        """Persists the distilled catalog to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # [ROUND-10] Strategic Stamping: Include distiller version for forensic auditability
        self.distilled["metadata"] = self.distilled.get("metadata", {})
        self.distilled["metadata"]["distiller_version"] = "1.6.0"
        self.distilled["metadata"]["distilled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.get_gmtime())

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(self.distilled, f, indent=2, sort_keys=True)
        logger.info(f"Successfully saved distilled catalog to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Yamlr Catalog Distiller")
    parser.add_argument("--version", default="1.31", help="K8s version (e.g. 1.31)")
    parser.add_argument("--output", help="Output path (default: k8s_v{ver}_distilled.json)")
    args = parser.parse_args()

    distiller = CatalogDistiller(args.version)
    if distiller.fetch_raw_schema():
        distiller.distill()
        output = Path(args.output) if args.output else Path(f"k8s_v{args.version}_distilled.json")
        distiller.save(output)


if __name__ == "__main__":
    main()
