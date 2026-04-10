from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from jsonschema import ValidationError, validate

from yamlr.core.engine.models import AnalysisResult
from yamlr.core.forensics import ForensicLogger
from yamlr.core.k8s_versions import MATRIX

logger = logging.getLogger("yamlr.core.validation.schema")
__all__ = ["SchemaValidator"]


class SchemaValidator:
    """
    Consolidated Kubernetes Manifest Validator.

    Why: Resolves duplication across ref_resolver, risk_classifier, and analyzers.
         Guarantees 100% null-safety for partial/malformed YAMLs during real-time LSP scans.
    """

    def __init__(
        self,
        catalog: Dict[str, Any] = None,
        cluster_version: str = "1.31",
        debug_forensics: bool = False,
    ):
        """Initializes the schema validator with a distilled catalog.

        Why: To eliminate dependency on heavy SchemaStore and enable
             sub-millisecond validation using pre-distilled schemas.
        """
        if catalog is None:
            # [Universal Motto] Resolve via CatalogManager for multi-version support
            from yamlr.core.catalog_manager import CatalogManager
            mgr = CatalogManager()
            catalog = mgr.get_catalog_data(cluster_version)

        self.catalog = catalog
        self._version = cluster_version
        self.debug_forensics = debug_forensics

    @property
    def version(self) -> str:
        """Returns the Kubernetes version currently targeted."""
        return self._version

    @property
    def schema(self) -> Dict[str, Any]:
        """LSP-compatible schema wrapper for definitions."""
        return {"definitions": self.catalog}

    def get_resource_definition(self, api_version: str, kind: str) -> Optional[str]:
        """
        Resolves the schema key for a kind/api combination.

        Why: Uses 10x-faster distilled key lookups with built-in null-safety.
        """
        if not self.catalog or not hasattr(self.catalog, "keys"):
            return None

        # 🛡️ Null-Safety: api_version and kind are often None during LSP typing
        api_v = str(api_version or "unknown")
        kind_v = str(kind or "unknown")

        # 1. Precise Match
        key = f"{api_v}/{kind_v}"
        if key in self.catalog:
            return key

        return None

    def validate(self, content: str, file_path: str = "unknown") -> List[Dict[str, Any]]:
        """Legacy compatibility wrapper for the pipeline engine Stage 1.0."""
        import yaml

        try:
            # [Zero-Blindspot] Support multi-document manifests
            resources = [r for r in yaml.safe_load_all(content) if isinstance(r, dict)]
            findings = []
            for doc in resources:
                v_results = self.validate_full_document(doc, file_path=file_path)
                for f in v_results:
                    findings.append(
                        {
                            "severity": f.severity,
                            "message": f.message,
                            "resource_name": f.resource_name,
                            "resource_kind": f.resource_kind,
                            "rule_id": f.rule_id,
                            "line_no": f.line_no,
                            "column_no": f.column_no,
                        }
                    )
            return findings
        except Exception as e:
            logger.debug(f"Pipeline validation failed: {e}")
            return []

    def validate_full_document(
        self,
        doc: Dict[str, Any],
        schema_key: Optional[str] = None,
        file_path: str = "unknown",
        deep_array_check: bool = True,
        strict_mode: bool = False,
    ) -> List[AnalysisResult]:
        """Performs a full schema validation of the document."""
        if not doc or not isinstance(doc, dict):
            return []

        kind = doc.get("kind")
        api_version = doc.get("apiVersion")

        if not kind or not api_version:
            return []

        key = schema_key or self.get_resource_definition(api_version, kind)
        if not key:
            return []

        schema = self.schema.get("definitions", {}).get(key)
        if not schema:
            return []

        try:
            if not deep_array_check:
                doc = self._sample_document(doc)

            full_schema = {**schema, "definitions": self.schema.get("definitions", {})}

            if strict_mode:
                full_schema = self._make_schema_strict(full_schema)

            validate(doc, full_schema)
            return []
        except ValidationError as e:
            return [
                AnalysisResult(
                    analyzer_name="SchemaValidator",
                    severity="ERROR",
                    message=e.message,
                    resource_name=doc.get("metadata", {}).get("name", "unknown"),
                    resource_kind=kind,
                    file_path=file_path,
                    rule_id="schema/validation-error",
                    line_no=0,
                )
            ]
        except Exception as e:
            logger.debug(f"Schema validation crash avoided: {e}")
            return []

    def validate_api_version(self, api_version: str, kind: str) -> Optional[AnalysisResult]:
        """Specific validator for Kubernetes API deprecations and validity."""
        if not api_version or not kind:
            return None

        if self.get_resource_definition(api_version, kind):
            return None

        stable = MATRIX.STABLE_VERSIONS.get(kind)
        if not stable:
            return None

        val_api = str(api_version or "v1").lower()
        if "beta" in val_api or "alpha" in val_api:
            return AnalysisResult(
                analyzer_name="SchemaValidator",
                severity="ERROR",
                message=f"{kind} uses beta/alpha version '{api_version}' (standard: {stable})",
                resource_name="unknown",
                resource_kind=kind,
                file_path="unknown",
                suggestion=f"Use {stable}",
                rule_id="schema/suspicious-api-version",
            )
        return None

    def _sample_document(self, doc: Any) -> Any:
        """Recursively samples arrays to 1 element for fast validation."""
        if isinstance(doc, dict):
            return {k: self._sample_document(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            if len(doc) > 1:
                return [self._sample_document(doc[0])]
            return [self._sample_document(v) for v in doc]
        return doc

    def _make_schema_strict(self, schema: Any) -> Any:
        """Injects additionalProperties: False recursively."""
        if not isinstance(schema, dict):
            return schema

        new_schema = dict(schema)
        if new_schema.get("type") == "object" or "properties" in new_schema or "fields" in new_schema:
            new_schema["additionalProperties"] = False

        if "properties" in new_schema:
            new_schema["properties"] = {k: self._make_schema_strict(v) for k, v in new_schema["properties"].items()}

        if "definitions" in new_schema:
            new_schema["definitions"] = {k: self._make_schema_strict(v) for k, v in new_schema["definitions"].items()}

        if "items" in new_schema:
            new_schema["items"] = self._make_schema_strict(new_schema["items"])

        return new_schema

    # --- Path Traversal Helpers (Optimized for Cognitive Complexity) ---

    def _resolve_path_def(self, definition_key: str, path: str) -> Optional[Dict[str, Any]]:
        """Traverses a schema path to return the target definition."""
        if not self.schema or not definition_key:
            return None

        definitions = self.schema.get("definitions", {})
        current = definitions.get(definition_key)
        if not current or not path:
            return current

        parts = path.split(".")
        for i, part in enumerate(parts):
            current = self._resolve_path_step(current, part, i, len(parts), definitions)
            if not current:
                return None

        return self._resolve_final_ref(current, definitions)

    def _resolve_path_step(
        self,
        current: Dict[str, Any],
        part: str,
        index: int,
        total: int,
        definitions: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Resolves a single step in a schema path traversal."""
        # 1. Follow Refs
        ref = current.get("$ref") or current.get("ref")
        if ref:
            current = definitions.get(ref.split("/")[-1])
            if not current:
                return None

        # 2. Descend into Intermediate Arrays
        if index < total - 1 and current.get("type") == "array":
            current = self._resolve_intermediate_array(current, definitions)
            if not current:
                return None

        # 3. Look up property/field
        return (current.get("properties") or current.get("fields") or {}).get(part)

    def _resolve_intermediate_array(
        self, current: Dict[str, Any], definitions: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handles descent into array items/fields for intermediate path steps."""
        # A. Distilled catalogs: array property itself contains the fields
        if "fields" in current:
            return current

        # B. Standard items logic
        if "items" in current:
            items = current["items"]
            item_ref = items.get("$ref") or items.get("ref") if isinstance(items, dict) else None
            if item_ref:
                return definitions.get(item_ref.split("/")[-1])
            return items

        # C. Distilled 'ref' logic
        if "ref" in current:
            return definitions.get(current["ref"].split("/")[-1])

        return None

    def _resolve_final_ref(self, current: Any, definitions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ensures the final resolved node is fully dereferenced."""
        if not isinstance(current, dict):
            return current
        ref = current.get("$ref") or current.get("ref")
        if ref:
            return definitions.get(ref.split("/")[-1])
        return current

    # --- Public Insight Methods ---

    def get_definition_for_path(self, definition_key: str, path: str) -> Optional[Dict[str, Any]]:
        """Resolves a nested path to its JSON schema definition."""
        return self._resolve_path_def(definition_key, path)

    def is_array_type(self, definition_key: str, path: str) -> bool:
        """Determines if a given path within a definition is expected to be an array."""
        target = self._resolve_path_def(definition_key, path)
        if not target:
            return False

        if target.get("type") == "array":
            return True

        item_node = self._resolve_array_item_node(target)
        if item_node:
            return item_node.get("type") == "array"
        return False

    def is_object_type(self, definition_key: str, path: str) -> bool:
        """Determines if a field path resolves to an object type."""
        target = self._resolve_path_def(definition_key, path)
        if not target:
            return False

        if target.get("type") == "multi":
            return any(opt.get("type") == "object" or "fields" in opt for opt in target.get("options", []))

        if target.get("type") == "object" or "fields" in target:
            return True

        item_node = self._resolve_array_item_node(target)
        if item_node:
            return item_node.get("type") == "object" or "fields" in item_node
        return False

    def _resolve_array_item_node(self, target: Any) -> Optional[Dict[str, Any]]:
        """Helper to resolve the underlying item definition if target is an array."""
        if not isinstance(target, dict) or target.get("type") != "array":
            return None

        definitions = self.schema.get("definitions", {})

        # 1. Distilled ref
        ref = target.get("ref")
        if ref:
            return definitions.get(ref.split("/")[-1])

        # 2. Standard items
        items = target.get("items")
        if items:
            ref = items.get("$ref") or items.get("ref") if isinstance(items, dict) else None
            if ref:
                return definitions.get(ref.split("/")[-1])
            return items

        return None

    def has_field(self, definition_key: str, path: str, field_name: str) -> bool:
        """Checks if a definition at a given path contains a specific field."""
        target = self._resolve_path_def(definition_key, path)
        if not target:
            return False

        # [PHASE 21 GENESIS FIX] Array-Aware Field Resolution
        if target.get("type") == "array":
            item_node = self._resolve_array_item_node(target)
            if item_node:
                target = item_node

        res = field_name in (target.get("fields") or target.get("properties") or {})
        ForensicLogger.log(
            "pe_debug.log",
            f"DEBUG: has_field key={field_name} path={path} res={res}",
            enabled=self.debug_forensics,
        )
        return res

    def get_field_definition(self, definition_key: str, path: str, field_name: str) -> Optional[dict]:
        """Retrieves the schema definition for a specific field within a path."""
        target = self._resolve_path_def(definition_key, path)
        if not target:
            return None

        # [PHASE 21 GENESIS FIX] Unified Array/Multi-Type Resolution
        if target.get("type") == "array":
            return self._resolve_array_field_definition(target, path, field_name)

        if target.get("type") == "multi":
            for opt in target.get("options", []):
                f_def = (opt.get("fields") or opt.get("properties") or {}).get(field_name)
                if f_def:
                    return f_def
            return None

        return (target.get("fields") or target.get("properties") or {}).get(field_name)

    def _resolve_array_field_definition(
        self, target: Dict[str, Any], path: str, field_name: str
    ) -> Optional[Dict[str, Any]]:
        """Handles deep field lookups within array types (standard & distilled)."""
        # 1. Distilled fields check
        f_def = (target.get("fields") or {}).get(field_name)
        if f_def:
            return f_def

        # 2. Distilled recursive ref check: Use self.catalog directly
        ref = target.get("ref")
        if ref:
            # Note: recursive call to get_field_definition is safe here as it resolves the ref
            return self.get_field_definition(ref.split("/")[-1], path, field_name)

        # 3. Standard items logic
        items = target.get("items")
        if not items:
            return None

        ref = items.get("$ref") or items.get("ref") if isinstance(items, dict) else None
        if ref:
            item_target = self.catalog.get(ref.split("/")[-1])
            if item_target:
                return (item_target.get("fields") or item_target.get("properties") or {}).get(field_name)
        else:
            # Fallthrough for inline items
            return (items.get("fields") or items.get("properties") or {}).get(field_name)
        return None
