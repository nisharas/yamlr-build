"""
Yamlr Schema Validator - Pure Validator Implementation
------------------------------------------------------
Validates Kubernetes manifests against OpenAPI schemas.
Infrastructure concerns (fetching/caching) moved to SchemaStore.
"""

from __future__ import annotations
import logging
from typing import Optional, Dict, Any, List
from jsonschema import validate, ValidationError

from yamlr.analyzers.base import AnalysisResult
from yamlr.core.k8s_versions import MATRIX

logger = logging.getLogger("yamlr.schema_validator")
__all__ = ['SchemaValidator']


class SchemaValidator:
    """
    Validates Kubernetes API versions against OpenAPI schemas.
    """
    
    # KNOWN_STABLE_VERSIONS moved to SchemaStore
    
    def __init__(self, catalog: Dict[str, Any] = None, k8s_version: str = "1.31"):
        """Initializes the schema validator with a distilled catalog.
        
        Why: To eliminate dependency on heavy SchemaStore and enable 
             sub-millisecond validation using pre-distilled schemas.
        """
        if catalog is None:
            # Fallback for testing/legacy calls
            from yamlr.core.utils import resolve_bundled_asset
            catalog_path = resolve_bundled_asset("catalog/k8s_v1_distilled.json")
            import json
            with open(catalog_path, "r") as f:
                catalog = json.load(f)
        
        self.catalog = catalog
        self._version = k8s_version

    @property
    def version(self) -> str:
        """Returns the Kubernetes version currently being used for validation."""
        return self._version

    @property
    def schema(self) -> Dict[str, Any]:
        """Returns a compatibility wrapper for the catalog acting as a schema."""
        return {"definitions": self.catalog}

    @property
    def is_loading(self) -> bool:
        """Distilled catalogs are always loaded synchronously."""
        return False

    def load_schema(self, background: bool = False) -> bool:
        """Distilled catalogs are pre-loaded during pipeline initialization."""
        return True

    def get_resource_definition(self, api_version: str, kind: str) -> Optional[str]:
        """Resolves the key for a specific resource type in the distilled catalog.
        
        Why: Distilled catalogs use 'api/kind' keys for 10x faster lookups.
        """
        # [Zero-Blindspot] Support both legacy GVK paths and streamlined catalog keys
        # [ROUND-10] Defensive: ensure catalog is valid before iteration
        if not self.catalog or not hasattr(self.catalog, "keys"):
            return None
            
        for k in list(self.catalog.keys()):
            if str(k).split("/")[-1].lower() == kind.lower():
                return k
        return None

    def _resolve_path_def(self, definition_key: str, path: str) -> Optional[Dict[str, Any]]:
        """Traverses a schema path to return the target definition."""
        if not self.schema or not definition_key:
            return None
        
        definitions = self.schema.get("definitions", {})
        current = definitions.get(definition_key)
        if not current or not path:
            return current

        parts = path.split('.')
        for i, part in enumerate(parts):
            # Follow refs and descend into items only for intermediate steps
            ref = current.get("$ref") or current.get("ref")
            if ref:
                current = definitions.get(ref.split('/')[-1])
                if not current: return None
            
            # If we are at an intermediate step and it's an array, descend into items/fields
            if i < len(parts) - 1 and current.get("type") == "array":
                # For distilled catalogs, the array property itself might contain the fields
                # if the item type is object.
                if "fields" in current:
                    pass # Stay on current, it has the fields we need for the next part
                elif "items" in current:
                    items = current["items"]
                    item_ref = items.get("$ref") or items.get("ref") if isinstance(items, dict) else None
                    if item_ref:
                        current = definitions.get(item_ref.split('/')[-1])
                    else:
                        current = items
                elif "ref" in current: # Some distilled versions use 'ref'
                    current = definitions.get(current["ref"].split('/')[-1])
                
                if not current: return None

            # Look up property/field
            current = (current.get("properties") or current.get("fields") or {}).get(part)
            if not current:
                return None
                
        res = self._resolve_final_ref(current, definitions)
        return res

    def _resolve_final_ref(self, current: Any, definitions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ensures the final resolved node is fully dereferenced."""
        if not isinstance(current, dict):
            return current
        ref = current.get("$ref") or current.get("ref")
        if ref:
            return definitions.get(ref.split('/')[-1])
        return current

    def is_array_type(self, definition_key: str, path: str) -> bool:
        """Determines if a given path within a definition is expected to be an array."""
        target = self._resolve_path_def(definition_key, path)
        if not target: return False
        return target.get("type") == "array"

    def is_object_type(self, definition_key: str, path: str) -> bool:
        """Determines if a field path resolves to an object type."""
        target = self._resolve_path_def(definition_key, path)
        if not target: return False
        if target.get("type") == "multi":
             return any(opt.get("type") == "object" or "fields" in opt for opt in target.get("options", []))
        return target.get("type") == "object" or "fields" in target

    def has_field(self, definition_key: str, path: str, field_name: str) -> bool:
        """Checks if a definition at a given path contains a specific field."""
        target = self._resolve_path_def(definition_key, path)
        if not target: return False
        
        # If the target is an array, we are likely looking for a field in its items
        if target.get("type") == "array":
            # Support distilled fields in the array property itself
            if field_name in (target.get("fields") or {}):
                with open("d:\\yamlr\\pe_debug.log", "a") as f:
                    f.write(f"DEBUG: has_field key={field_name} path={path} res=True (distilled array fields)\n")
                return True
            # Support standard items wrapper
            definitions = self.schema.get("definitions", {})
            items = target.get("items")
            if items:
                ref = items.get("$ref") or items.get("ref") if isinstance(items, dict) else None
                if ref:
                    target = definitions.get(ref.split('/')[-1])
                else:
                    target = items
                if not target: return False
        
        is_f = field_name in (target.get("fields") or target.get("properties") or {})
        with open("d:\\yamlr\\pe_debug.log", "a") as f:
            f.write(f"DEBUG: has_field key={field_name} path={path} res={is_f}\n")
        return is_f

    def get_field_definition(self, definition_key: str, path: str, field_name: str) -> Optional[dict]:
        """Retrieves the schema definition for a specific field within a path."""
        target = self._resolve_path_def(definition_key, path)
        if not target: return None
        
        # If the target is an array, we are likely looking for a field in its items
        if target.get("type") == "array":
            # Support distilled fields in the array property itself
            f_def = (target.get("fields") or {}).get(field_name)
            if f_def:
                return f_def
            # Support standard items wrapper
            definitions = self.schema.get("definitions", {})
            items = target.get("items")
            if items:
                ref = items.get("$ref") or items.get("ref") if isinstance(items, dict) else None
                if ref:
                    target = definitions.get(ref.split('/')[-1])
                else:
                    target = items
                if not target: return None

        if target.get("type") == "multi":
             for opt in target.get("options", []):
                  f_def = (opt.get("fields") or opt.get("properties") or {}).get(field_name)
                  if f_def: return f_def
             return None

        return (target.get("fields") or target.get("properties") or {}).get(field_name)

    def get_definition_for_path(self, definition_key: str, path: str) -> Optional[Dict[str, Any]]:
        """Resolves a nested path to its JSON schema definition."""
        return self._resolve_path_def(definition_key, path)

    def validate_api_version(self, api_version: str, kind: str) -> Optional[AnalysisResult]:
        """Validates the apiVersion for a specific resource kind.
        
        Why: To catch deprecated or invalid API versions early in the pipeline.
        """
        if not self.schema and not self.load_schema(): return self._heuristic_check(api_version, kind)
        if self.get_resource_definition(api_version, kind): return None
        return self._create_invalid_api_error(api_version, kind)
    
    def _heuristic_check(self, api_version: str, kind: str) -> Optional[AnalysisResult]:
        """Performs a best-effort API version check when the schema is unavailable.
        
        Why: To provide fallback safety even in offline or air-gapped environments.
        """
        # [Legacy-Parity] Use MATRIX as the authority for stable versions
        if kind not in MATRIX.STABLE_VERSIONS: return None
        correct = MATRIX.STABLE_VERSIONS[kind]
        if "beta" in api_version.lower() or "alpha" in api_version.lower():
            return AnalysisResult(
                analyzer_name="SchemaValidator",
                severity="ERROR",
                message=f"{kind} uses beta/alpha version '{api_version}' (standard: {correct})",
                resource_name="unknown",
                resource_kind=kind,
                file_path="unknown",
                suggestion=f"Use {correct}",
                rule_id="schema/suspicious-api-version"
            )
        return AnalysisResult(
            analyzer_name="SchemaValidator",
            severity="WARNING",
            message=f"{kind} uses non-standard version '{api_version}' (expected {correct})",
            resource_name="unknown",
            resource_kind=kind,
            file_path="unknown",
            suggestion="Verify version",
            rule_id="schema/nonstandard-api-version"
        ) if api_version != correct else None
    
    def _create_invalid_api_error(self, api_version: str, kind: str) -> AnalysisResult:
        """Factory method for creating structured API version validation errors.
        
        Why: To ensure consistent error reporting across the engine.
        """
        suggested = MATRIX.STABLE_VERSIONS.get(kind)
        suggestion = f"Change to {suggested}" if suggested else f"Check valid versions for {kind}"
        return AnalysisResult(
            analyzer_name="SchemaValidator",
            severity="ERROR",
            message=f"{kind} does not support apiVersion '{api_version}'",
            resource_name="unknown",
            resource_kind=kind,
            file_path="unknown",
            suggestion=suggestion,
            rule_id="schema/invalid-api-version"
        )

    def _get_schema_for_doc(self, doc: Dict[str, Any], schema_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the specific schema for a given document."""
        if not self.schema:
            self.load_schema()
        
        kind = doc.get("kind")
        api_version = doc.get("apiVersion")
        if not kind or not api_version:
            return None
            
        key = schema_key or self.get_resource_definition(api_version, kind)
        if not key:
            return None
            
        return self.schema.get("definitions", {}).get(key)

    def validate_full_document(
        self, 
        doc: Dict[str, Any], 
        schema_key: Optional[str] = None,
        deep_array_check: bool = True,
        strict_mode: bool = False
    ) -> List[AnalysisResult]:
        """
        Validates the entire document against its schema.
        
        Why: Central entry point for full schema validation. 
             Supports sampling (deep_array_check=False) for Pro performance.
        """
        if not doc:
            return []

        schema = self._get_schema_for_doc(doc, schema_key)
        if not schema:
            return []

        # [Phase 8] Validation Sampling for Operational Efficiency
        if not deep_array_check:
             doc = self._sample_document(doc)

        return self.validate_instance(doc, schema, strict_mode=strict_mode)


    def validate_instance(self, doc: Dict[str, Any], schema: Dict[str, Any], strict_mode: bool = False) -> List[AnalysisResult]:
        """Performs JSON schema validation with full definition context."""
        try:
            # [Audit v17] Strict Mode: Hard-fail on unknown fields
            if strict_mode:
                 import copy
                 # Deepcopy the ENTIRE schema context (root + definitions) to avoid cache contamination
                 full_schema = copy.deepcopy({
                     **schema,
                     "definitions": self.schema.get("definitions", {})
                 })
                 # Recursively inject additionalProperties: False
                 full_schema = self._make_schema_strict(full_schema)
            else:
                 # Normal Mode: Use shared definitions to save memory/time
                 full_schema = {
                     **schema,
                     "definitions": self.schema.get("definitions", {})
                 }

            validate(doc, full_schema)
            return []
        except ValidationError as e:
            return [AnalysisResult(
                analyzer_name="SchemaValidator",
                severity="ERROR",
                message=e.message,
                resource_name=doc.get("metadata", {}).get("name", "unknown"),
                resource_kind=doc.get("kind", "unknown"),
                file_path="unknown",
                rule_id="schema/validation-error"
            )]





    def _make_schema_strict(self, schema: Any) -> Any:
        """
        Recursively injects additionalProperties: False into objects.
        
        Why: Kubernetes schemas use many $refs. Top-level strictness isn't enough.
        """
        if not isinstance(schema, dict):
            return schema
            
        new_schema = dict(schema)
        if new_schema.get("type") == "object" or "properties" in new_schema or "fields" in new_schema:
            new_schema["additionalProperties"] = False
            
        # Recurse into properties
        if "properties" in new_schema:
            new_props = {}
            for k, v in new_schema["properties"].items():
                new_props[k] = self._make_schema_strict(v)
            new_schema["properties"] = new_props
            
        # Recurse into definitions (the most important part for K8s)
        if "definitions" in new_schema:
            new_defs = {}
            for k, v in new_schema["definitions"].items():
                new_defs[k] = self._make_schema_strict(v)
            new_schema["definitions"] = new_defs
            
        # Recurse into items (for arrays)
        if "items" in new_schema:
            new_schema["items"] = self._make_schema_strict(new_schema["items"])
            
        return new_schema

    def _sample_document(self, doc: Any) -> Any:
        """Recursively samples arrays to 1 element for fast validation."""
        if isinstance(doc, dict):
            return {k: self._sample_document(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            if len(doc) > 1:
                return [self._sample_document(doc[0])]
            return [self._sample_document(v) for v in doc]
        return doc


    def clear_cache(self):
        """No-op: CatalogManager handles cache lifecycle."""
        pass

    def fuzzy_match(self, key: str) -> Optional[str]:
        """
        Stub for fuzzy matching.
        
        Why: Prevents AttributeError in SchemaHealer during reconstruction.
             In Pro versions, this is delegated to the SchemaManager.
        """
        return None
