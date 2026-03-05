#!/usr/bin/env python3
"""
Yamlr SCHEMA HEALER
-------------------
Handles schema-driven intelligence during YAML reconstruction:
- OpenAPI-aware array detection
- Tri-state ambiguity resolution
- Type coercion
- Fuzzy typo correction (Tier 0)

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from yamlr.parsers.coercer import TypeCoercer
from ruamel.yaml.comments import CommentedMap, CommentedSeq

logger = logging.getLogger("yamlr.parsers.schema_healer")

T_MAP = CommentedMap
T_SEQ = CommentedSeq

class SchemaHealer:
    """
    Provides schema-aware signals and repairs during reconstruction.
    """

    def __init__(self, catalog: Dict[str, Any], validator: Any):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.catalog = catalog
        self.validator = validator
        self.coercer = TypeCoercer()
        self.definition_key = None

    def set_resource_context(self, api_version: str, kind: str):
        """Sets the current resource context for schema lookups."""
        if self.validator:
            self.definition_key = self.validator.get_resource_definition(api_version, kind)
        else:
            self.definition_key = None

    def get_effective_definition(self, dot_path: str) -> Optional[str]:
        """Returns the effective schema definition for a given path."""
        cat_def = self.catalog.get(dot_path, {}).get("_definition") if self.catalog else None
        return cat_def or self.definition_key

    def should_be_array(self, key: str, dot_path: str) -> bool:
        """Determines if a field should be a list based on schema."""
        if key == "resources":
            return False
            
        eff_def = self.get_effective_definition(dot_path)
        
        if not self.validator or not eff_def or not self.validator.schema:
            # Fallback heuristics for common K8s fields
            if key in {"roleRef", "metadata"}:
                return False
            if key in {
                "containers", "initContainers", "volumes", "subjects", "ports",
                "rules", "env", "envFrom", "imagePullSecrets", "finalizers",
                "ownerReferences", "hostAliases", "topologySpreadConstraints",
            }:
                return True
            return False
            
        full_path = f"{dot_path}.{key}" if dot_path else key
        return self.validator.is_array_type(eff_def, full_path)

    def resolve_tri_state_ambiguity(self, stack: List[Tuple], shard_key: str, shard_indent: int) -> bool:
        """
        Resolves whether a shard at the same indent as its parent belongs to the parent
        or a sibling (Ambiguity Resolution).
        """
        if not self.validator or not shard_key:
            return True # Conservative default: keep sibling

        _, current_container, _, current_path, _ = stack[-1]
        eff_def = self.get_effective_definition(current_path)
        
        if not eff_def:
            return True

        # Check State 1: Is it a valid sibling?
        if self.validator.has_field(eff_def, current_path, shard_key):
            return True

        # Check State 2: Does it belong to the previous sibling as a child?
        if isinstance(current_container, T_MAP) and len(current_container) > 0:
            last_key = list(current_container.keys())[-1]
            prev_sibling_def = self.validator.get_field_definition(eff_def, current_path, last_key)

            if prev_sibling_def:
                prev_props = prev_sibling_def.get("properties", {})
                if shard_key in prev_props:
                    # It belongs to the previous sibling!
                    # Logic for pushing onto physicist stack is handled by structurer
                    return False # Tell physicist NOT to keep as sibling

        return True

    def is_valid_sibling(self, dot_path: str, shard_key: str) -> bool:
        """Checks if a key is a valid sibling in the current schema context."""
        if not self.validator or not shard_key:
            return True
        eff_def = self.get_effective_definition(dot_path)
        if not eff_def:
            return True
        return self.validator.has_field(eff_def, dot_path, shard_key)

    def get_field_schema(self, dot_path: str, key: str) -> Optional[dict]:
        """Returns the schema definition for a specific field."""
        if not self.validator:
            return None
        eff_def = self.get_effective_definition(dot_path)
        if not eff_def:
            return None
        return self.validator.get_field_definition(eff_def, dot_path, key)

    def should_be_object(self, key: str, dot_path: str) -> bool:
        """Determines if a field should be an object (Map) based on schema."""
        eff_def = self.get_effective_definition(dot_path)
        
        if not self.validator or not eff_def or not self.validator.schema:
            # Fallback heuristics
            if key in {"metadata", "spec", "selector", "labels", "annotations", "resources", "template", "data", "stringData", "status"}:
                return True
            return False

        full_path = f"{dot_path}.{key}" if dot_path else key
        if self.validator.is_object_type(eff_def, full_path):
            return True
            
        # Fallback: If strict check fails (e.g., misplaced key), check if it's a known object key
        if key in {"metadata", "spec", "selector", "labels", "annotations", "resources", "template", "data", "stringData", "status"}:
            return True
            
        return False



    def clean_value(self, val: Any, parent_key: Optional[str], dot_path: str, shard_key: Optional[str], is_flow: bool = False) -> Any:
        """
        Applies type coercion and cleaning to a value.
        """
        if val is None:
            # Schema-Aware Coercion: Convert None to {} for required objects
            if shard_key and self.should_be_object(shard_key, dot_path):
                logger.debug(f"Coercing None -> {{}} for {dot_path}.{shard_key}")
                return T_MAP()
            return None

        # [HEAL-6.2] Epistemic Casting (ENTERPRISE GATE)
        if shard_key and self.should_be_array(shard_key, dot_path) and not isinstance(val, list):
            from yamlr.core.license_manager import LicenseManager
            status, _ = LicenseManager.check_pro_status()
            
            if status.is_usable():
                from yamlr.pro.surgery import ProSurgeon
                val = ProSurgeon.cast_to_array(val, dot_path, shard_key)
            else:
                logger.debug(f"Free Tier: Skipping Epistemic Repair for Map-as-List trauma at {dot_path}.{shard_key}. Pro license required.")

        # Schema-driven coercion
        field_schema = None
        if shard_key:
            field_schema = self.get_field_schema(dot_path, shard_key)
            
        if field_schema and self.coercer:
            val = self.coercer.coerce(val, field_schema)
            
        # Handle flow-style (deserialization for reconstruction)
        if is_flow and isinstance(val, str):
            import yaml
            try:
                parsed = yaml.safe_load(val)
                if isinstance(parsed, (dict, list)):
                    if isinstance(parsed, dict):
                        val = T_MAP(parsed)
                        val.fa.set_flow_style()
                    else:
                        val = T_SEQ(parsed)
                        val.fa.set_flow_style()
            except Exception:
                pass
            
        return val

    def apply_typo_fix(self, shard: Any) -> str:
        """Extracts and returns a corrected key if a typo tag is present."""
        if hasattr(shard, "intent_tag") and shard.intent_tag and shard.intent_tag.startswith("k8s.typo:"):
            parts = shard.intent_tag.split(":")
            if len(parts) >= 3:
                return parts[2]
        return shard.key
