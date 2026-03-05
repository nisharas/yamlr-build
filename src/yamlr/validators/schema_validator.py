"""
Yamlr Schema Validator - Pure Validator Implementation
------------------------------------------------------
Validates Kubernetes manifests against OpenAPI schemas.
Infrastructure concerns (fetching/caching) moved to SchemaStore.
"""

import logging
from typing import Optional, Dict, Any, List
from jsonschema import validate, ValidationError, RefResolver

from yamlr.analyzers.base import AnalysisResult
from yamlr.parsers.schema_store import SchemaStore

logger = logging.getLogger("yamlr.schema_validator")

class SchemaValidator:
    """
    Validates Kubernetes API versions against OpenAPI schemas.
    """
    
    # Common stable API versions for core resources
    KNOWN_STABLE_VERSIONS = {
        "ConfigMap": "v1", "Secret": "v1", "Service": "v1", "Pod": "v1",
        "Namespace": "v1", "ServiceAccount": "v1", "PersistentVolume": "v1",
        "PersistentVolumeClaim": "v1", "Deployment": "apps/v1",
        "StatefulSet": "apps/v1", "DaemonSet": "apps/v1", "ReplicaSet": "apps/v1",
        "Job": "batch/v1", "CronJob": "batch/v1", "Ingress": "networking.k8s.io/v1",
        "NetworkPolicy": "networking.k8s.io/v1",
    }
    
    def __init__(self, k8s_version: str = "1.31"):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.store = SchemaStore(k8s_version)

    @property
    def version(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.store.version

    @property
    def schema(self) -> Optional[Dict[str, Any]]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.store.schema

    @property
    def is_loading(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.store.is_loading

    def load_schema(self, background: bool = False) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.store.load(background)

    def get_resource_definition(self, api_version: str, kind: str) -> Optional[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.schema:
            if self.is_loading: return None
            if not self.load_schema(): return None
        
        definitions = self.schema.get("definitions", {})
        group, version = api_version.split("/", 1) if "/" in api_version else ("core", api_version)
        
        for key in [f"io.k8s.api.{group}.{version}.{kind}", f"io.k8s.api.{group}.{kind}", f"io.k8s.{kind}"]:
            if key in definitions: return key
        return None

    def is_array_type(self, definition_key: str, path: str) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.schema or not definition_key: return False
        definitions = self.schema.get("definitions", {})
        current_def = definitions.get(definition_key)
        if not current_def: return False
            
        for i, part in enumerate(path.split('.')):
            prop = current_def.get("properties", {}).get(part)
            if not prop and current_def.get("$ref"):
                current_def = definitions.get(current_def["$ref"].split('/')[-1])
                if not current_def: return False
                prop = current_def.get("properties", {}).get(part)
            
            if not prop: return False
            if i == len(path.split('.')) - 1: return prop.get("type") == "array"
            
            next_ref = prop.get("items", {}).get("$ref") if prop.get("type") == "array" else prop.get("$ref")
            if next_ref:
                current_def = definitions.get(next_ref.split('/')[-1])
                if not current_def: return False
            else: current_def = prop
        return False

    def is_object_type(self, definition_key: str, path: str) -> bool:
        """Determines if a field path resolves to an object type."""
        if not self.schema or not definition_key: return False
        definitions = self.schema.get("definitions", {})
        current_def = definitions.get(definition_key)
        if not current_def: return False
            
        for i, part in enumerate(path.split('.')):
            prop = current_def.get("properties", {}).get(part)
            if not prop and current_def.get("$ref"):
                current_def = definitions.get(current_def["$ref"].split('/')[-1])
                if not current_def: return False
                prop = current_def.get("properties", {}).get(part)
            
            if not prop: return False
            if i == len(path.split('.')) - 1:
                return prop.get("type") == "object" or "properties" in prop or "$ref" in prop
            
            next_ref = prop.get("items", {}).get("$ref") if prop.get("type") == "array" else prop.get("$ref")
            if next_ref:
                current_def = definitions.get(next_ref.split('/')[-1])
                if not current_def: return False
            else: current_def = prop
        return False

    def has_field(self, definition_key: str, path: str, field_name: str) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.schema or not definition_key: return False
        definitions = self.schema.get("definitions", {})
        current_def = definitions.get(definition_key)
        if not current_def: return False
            
        if path:
            for part in path.split('.'):
                prop = current_def.get("properties", {}).get(part)
                if not prop and current_def.get("$ref"):
                    current_def = definitions.get(current_def["$ref"].split('/')[-1])
                    if not current_def: return False
                    prop = current_def.get("properties", {}).get(part)
                if not prop: return False
                
                next_ref = prop.get("items", {}).get("$ref") if prop.get("type") == "array" else prop.get("$ref")
                if next_ref:
                    current_def = definitions.get(next_ref.split('/')[-1])
                    if not current_def: return False
                else: current_def = prop

        if "$ref" in current_def:
             current_def = definitions.get(current_def["$ref"].split('/')[-1], current_def)
        return field_name in current_def.get("properties", {})

    def get_field_definition(self, definition_key: str, path: str, field_name: str) -> Optional[dict]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.schema or not definition_key: return None
        definitions = self.schema.get("definitions", {})
        current_def = definitions.get(definition_key)
        if not current_def: return None
            
        if path:
            for part in path.split('.'):
                prop = current_def.get("properties", {}).get(part)
                if not prop and current_def.get("$ref"):
                    current_def = definitions.get(current_def["$ref"].split('/')[-1])
                    if not current_def: return None
                    prop = current_def.get("properties", {}).get(part)
                if not prop: return None
                
                next_ref = prop.get("items", {}).get("$ref") if prop.get("type") == "array" else prop.get("$ref")
                if next_ref:
                    current_def = definitions.get(next_ref.split('/')[-1])
                    if not current_def: return None
                else: current_def = prop

        if "$ref" in current_def:
             current_def = definitions.get(current_def["$ref"].split('/')[-1], current_def)

        field_def = current_def.get("properties", {}).get(field_name) or current_def.get("additionalProperties")
        if not field_def: return None
            
        ref = field_def.get("$ref") or (field_def.get("items", {}).get("$ref") if field_def.get("type") == "array" else None)
        return definitions.get(ref.split('/')[-1]) if ref else field_def

    def validate_api_version(self, api_version: str, kind: str) -> Optional[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.schema and not self.load_schema(): return self._heuristic_check(api_version, kind)
        if self.get_resource_definition(api_version, kind): return None
        return self._create_invalid_api_error(api_version, kind)
    
    def _heuristic_check(self, api_version: str, kind: str) -> Optional[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if kind not in self.KNOWN_STABLE_VERSIONS: return None
        correct = self.KNOWN_STABLE_VERSIONS[kind]
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
            suggestion=f"Verify version",
            rule_id="schema/nonstandard-api-version"
        ) if api_version != correct else None
    
    def _create_invalid_api_error(self, api_version: str, kind: str) -> AnalysisResult:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        suggested = self.KNOWN_STABLE_VERSIONS.get(kind)
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

    def validate_full_document(self, doc: Dict[str, Any]) -> List[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.schema:
            if self.is_loading: return []
            if not self.load_schema(): return ["Schema unavailable"]
            
        api_version, kind = doc.get("apiVersion"), doc.get("kind")
        if not api_version or not kind: return ["Missing apiVersion or kind"]
            
        def_key = self.get_resource_definition(api_version, kind)
        if not def_key: return [f"Unknown resource: {kind} ({api_version})"]
            
        try:
            validate(instance=doc, schema=self.schema["definitions"][def_key], resolver=RefResolver.from_schema(self.schema))
            return []
        except ValidationError as e:
            return [f"[{'.'.join(str(p) for p in e.path)}] {e.message}" if e.path else e.message]
        except Exception as e:
            return [f"System error: {str(e)}"]

    def clear_cache(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.store.clear_cache()
