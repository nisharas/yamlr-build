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

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from yamlr.models import FORCED_ARRAY_FIELDS, SAFE_OBJECT_FIELDS
from yamlr.parsers.coercer import TypeCoercer

if TYPE_CHECKING:
    pass

logger = logging.getLogger("yamlr.parsers.schema_healer")

__all__ = ['SchemaHealer']


class SchemaHealer:
    """
    Provides schema-aware signals and repairs during reconstruction.
    """

    def __init__(self, catalog: Dict[str, Any], validator: Any):
        """Initializes the schema healer with a catalog and validator.
        
        Why: To provide schema-aware intelligence for structural and semantic repairs.
        """
        self.catalog = catalog
        self.validator = validator
        self.coercer = TypeCoercer()
        self.definition_key = None

    def apply_typo_fix(self, shard: Shard) -> str:
        """Applies fuzzy typo correction to a shard's key based on schema or intent tags.
        
        Why: To resolve 'drifted' keys (e.g. 'relicas' -> 'replicas') during reconstruction.
        """
        # 1. Check if Scanner already identified a typo via intent_tag
        if hasattr(shard, "intent_tag") and shard.intent_tag and shard.intent_tag.startswith("k8s.typo:"):
            parts = shard.intent_tag.split(":")
            if len(parts) >= 3:
                return parts[2]

        if not shard.key:
            return ""
        
        # Guard: Skip short keys to prevent identity collisions
        if len(shard.key) < 4:
            return shard.key

        # 2. Schema-aware fuzzy matching fallback
        if self.validator:
            suggestion = self.validator.fuzzy_match(shard.key)
            if suggestion:
                # [Hardening] Double-check metadata context to prevent accidental Kind/Name renames
                if shard.key in {"kind", "apiVersion", "name", "namespace"}:
                     return shard.key
                logger.debug(f"SchemaHealer: Typo Corrected '{shard.key}' -> '{suggestion}'")
                return suggestion
                
        return shard.key

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
            
        # Hardened Overrides for Forensic Integrity
        if key in ("containers", "initContainers", "volumes", "volumeMounts", "imagePullSecrets"):
             return True
             
        eff_def = self.get_effective_definition(dot_path)
        
        if not self.validator or not eff_def or not self.validator.catalog:
            # Fallback heuristics for common K8s fields
            return key in FORCED_ARRAY_FIELDS
            
        full_path = f"{dot_path}.{key}" if dot_path else key
        return self.validator.is_array_type(eff_def, full_path)

    def resolve_tri_state_ambiguity(self, stack: List[Tuple], shard_key: str) -> bool:
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
        # Use YamlrNode API if available
        is_node = hasattr(current_container, "is_map")
        if (is_node and current_container.is_map and len(current_container) > 0) or \
           (not is_node and isinstance(current_container, dict) and len(current_container) > 0):
            
            # YamlrNode implements .keys()
            last_key = list(current_container.keys())[-1]
            prev_sibling_def = self.validator.get_field_definition(eff_def, current_path, last_key)

            if prev_sibling_def:
                prev_props = (prev_sibling_def.get("properties") or {})
                if shard_key in prev_props:
                    return False # Tell physicist NOT to keep as sibling
        
        # [FIX] If we have a validator, and we haven't found a reason to keep it,
        # we should pop. This prevents 'volumes' from being swallowed by containers.
        if self.validator:
            return False

        return True

    def is_valid_sibling(self, dot_path: str, shard_key: str) -> bool:
        """Checks if a key is a valid sibling in the current schema context."""
        if not self.validator or not shard_key:
            return True
        eff_def = self.get_effective_definition(dot_path)
        if not eff_def:
            return True
        res = self.validator.has_field(eff_def, dot_path, shard_key)
        logger.debug("SchemaHealer is_valid_sibling(path=%s, key=%s) -> %s", dot_path, shard_key, res)
        return res

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
            return key in SAFE_OBJECT_FIELDS

        full_path = f"{dot_path}.{key}" if dot_path else key
        if self.validator.is_object_type(eff_def, full_path):
            return True
            
        # Fallback: If strict check fails (e.g., misplaced key), check if it's a known object key
        return key in SAFE_OBJECT_FIELDS

    def clean_value(self, val: Any, dot_path: str, shard_key: Optional[str], is_flow: bool = False) -> Any:
        """Applies type coercion and cleaning to a value."""
        if val is None:
            if shard_key and self.should_be_object(shard_key, dot_path):
                logger.debug(f"Coercing None -> {{}} for {dot_path}.{shard_key}")
                return {}
            return None

        val = self._apply_epistemic_casting(val, dot_path, shard_key)

        field_schema = self.get_field_schema(dot_path, shard_key) if shard_key else None
        if field_schema and self.coercer:
            val = self.coercer.coerce(val, field_schema)
            
        if is_flow:
            val = self._handle_flow_style_value(val)
            
        return val

    def _apply_epistemic_casting(self, val: Any, dot_path: str, shard_key: Optional[str]) -> Any:
        """[HEAL-6.2] Casts scalars to arrays for known sequence fields."""
        if shard_key and self.should_be_array(shard_key, dot_path) and not isinstance(val, list):
            if not hasattr(val, "is_seq") or not val.is_seq:
                try:
                    from yamlr.pro.surgery import ProSurgeon
                    logger.info(f"Epistemic Repair: Cast {shard_key} to list at {dot_path}")
                    return ProSurgeon.cast_to_array(val, dot_path, shard_key)
                except ImportError:
                    # Fallback for Free version: simple wrapping
                    logger.debug(f"Free-mode Fallback: Wrapping {shard_key} in list at {dot_path}")
                    if shard_key in {"imagePullSecrets"}:
                        return [{"name": val}]
                    return [val]
        return val

    def _handle_flow_style_value(self, val: Any) -> Any:
        """De-serializes flow-style YAML values for reconstruction."""
        if isinstance(val, str):
            from yamlr.core.utils import get_hardened_yaml
            try:
                parser = get_hardened_yaml(typ="safe")
                parsed_node = parser.load(val)
                if parsed_node.is_map or parsed_node.is_seq:
                    return parsed_node
            except Exception:
                pass
        return val


