"""Dynamic CustomResourceDefinition (CRD) schema distillation engine.

Parses external Kubernetes CRD manifests (e.g. Cert-Manager, Istio, Prometheus,
Argo Rollouts) and compiles their OpenAPI v3 schemas into distilled JSON definitions
for local caching and zero-latency validation.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA_DIR = ".yamlr/schemas"


class CRDDistiller:
    """Compiles and manages custom Kubernetes CRD schemas."""

    def __init__(self, schema_dir: Optional[str] = None):
        self.schema_dir = Path(schema_dir or os.getenv("YAMLR_SCHEMA_DIR", DEFAULT_SCHEMA_DIR)).resolve()

    def _ensure_dir(self):
        """Ensures the schema storage directory exists."""
        self.schema_dir.mkdir(parents=True, exist_ok=True)

    def distill_file(self, crd_path: str) -> List[Dict[str, Any]]:
        """Parses a CRD manifest and compiles all version schemas.

        Args:
            crd_path: Path to single or multi-document CRD YAML file.

        Returns:
            List of compiled schema dictionaries.
        """
        self._ensure_dir()
        file_path = Path(crd_path)
        if not file_path.exists():
            raise FileNotFoundError(f"CRD manifest not found: {crd_path}")

        compiled = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            try:
                docs = list(yaml.safe_load_all(f))
            except Exception as e:
                logger.error("Failed to parse YAML in '%s': %s", crd_path, e)
                return []

        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if doc.get("kind") != "CustomResourceDefinition":
                continue

            schemas = self._extract_crd_schemas(doc)
            for s in schemas:
                out_name = f"{s['kind'].lower()}_{s['version']}.json"
                out_path = self.schema_dir / out_name
                with open(out_path, "w", encoding="utf-8") as out_f:
                    json.dump(s, out_f, indent=2)
                compiled.append(s)

        return compiled

    def distill_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """Recursively parses all YAML files in a directory and compiles CRDs.

        Args:
            dir_path: Path to directory containing CRD manifests.

        Returns:
            List of all compiled schema dictionaries.
        """
        all_compiled = []
        root = Path(dir_path)
        if not root.is_dir():
            return self.distill_file(dir_path)

        for p in root.rglob("*.yaml"):
            all_compiled.extend(self.distill_file(str(p)))
        for p in root.rglob("*.yml"):
            all_compiled.extend(self.distill_file(str(p)))
        return all_compiled

    def _extract_crd_schemas(self, crd: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts OpenAPI v3 schema definitions for each CRD version.

        Supports both v1 and v1beta1 CRD specifications, with structural
        fallback inference for legacy or unvalidated CRDs.
        """
        spec = crd.get("spec", {})
        group = spec.get("group", "")
        names = spec.get("names", {})
        kind = names.get("kind", "CustomResource")

        results = []
        versions = spec.get("versions", [])

        # v1beta1 backward compatibility: spec.version (singular string)
        if not versions and "version" in spec and isinstance(spec["version"], str):
            versions = [{"name": spec["version"]}]

        # Global validation schema (common in v1beta1)
        global_schema = spec.get("validation", {}).get("openAPIV3Schema")

        for v_info in versions:
            if not isinstance(v_info, dict):
                continue
            version_name = v_info.get("name", "v1")
            api_version = f"{group}/{version_name}" if group else version_name

            schema_obj = v_info.get("schema", {}).get("openAPIV3Schema")
            if not schema_obj and isinstance(global_schema, dict):
                schema_obj = global_schema

            # Structural fallback if no schema is provided
            if not schema_obj or not isinstance(schema_obj, dict):
                schema_obj = {
                    "type": "object",
                    "properties": {
                        "apiVersion": {"type": "string", "description": "API Version"},
                        "kind": {"type": "string", "description": "Resource Kind"},
                        "metadata": {"type": "object", "description": "Standard object metadata"},
                        "spec": {"type": "object", "description": "Specification of the desired state"},
                        "status": {"type": "object", "description": "Observed status of the resource"}
                    }
                }

            properties = schema_obj.get("properties", {})
            required_fields = set(schema_obj.get("required", []))

            fields = {}
            for prop_name, prop_def in properties.items():
                if isinstance(prop_def, dict):
                    prop_type = prop_def.get("type", "string")
                    desc = prop_def.get("description", "")
                    fields[prop_name] = {
                        "type": prop_type,
                        "required": prop_name in required_fields,
                        "description": desc
                    }
                else:
                    fields[prop_name] = {"type": "string", "required": False, "description": ""}

            results.append({
                "kind": kind,
                "apiVersion": api_version,
                "group": group,
                "version": version_name,
                "fields": fields
            })

        return results

    def list_schemas(self) -> List[Dict[str, Any]]:
        """Lists all distilled CRD schemas currently cached on disk."""
        if not self.schema_dir.exists():
            return []

        cached = []
        for p in self.schema_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cached.append({
                        "file": p.name,
                        "kind": data.get("kind", "Unknown"),
                        "apiVersion": data.get("apiVersion", "Unknown"),
                        "fields_count": len(data.get("fields", {}))
                    })
            except Exception:
                pass
        return sorted(cached, key=lambda x: x["kind"])

    def clean_schemas(self) -> int:
        """Removes all cached CRD schemas from the storage directory."""
        if not self.schema_dir.exists():
            return 0

        count = 0
        for p in self.schema_dir.glob("*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        return count
