from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("yamlr.parsers.coercer")
__all__ = ["TypeCoercer"]


class TypeCoercer:
    """
    Schema-aware type coercion engine.
    Auto-fixes common type mismatches using Kubernetes OpenAPI definitions.
    """

    def coerce(self, value: Any, schema_def: Optional[Dict[str, Any]]) -> Any:
        """
        Coerce a value to the type expected by the schema.

        Args:
            value: The value to coerce.
            schema_def: The JSON schema definition for the field.

        Returns:
            The coerced value if possible, otherwise the original value.
        """
        if value is None or schema_def is None:
            return value

        # Clean value if it's a string (proactively strip redundant quotes)
        v = value
        if isinstance(value, str):
            v = value.strip().strip("'\"")

        # 1. Skip if field can be multiple types (int-or-string)
        if "x-kubernetes-int-or-string" in schema_def:
            return v

        # [HEAL-6.5] Enum Typo Correction (e.g., 'Alway' -> 'Always')
        enum_list = schema_def.get("enum")
        if enum_list and isinstance(v, str):
            v_lower = v.lower().strip()
            # Exact match first
            for e in enum_list:
                if str(e).lower() == v_lower:
                    v = e
                    break
            else:
                # Fuzzy match if no exact match (Tier 0 Forensic)
                if len(v) > 2:
                    from difflib import get_close_matches

                    # [PHASE 20 OMEGA FIX] Case-insensitive fuzzy matching for enums
                    matches = get_close_matches(v_lower, [str(e).lower() for e in enum_list], n=1, cutoff=0.7)
                    if matches:
                        # Map back to original case from the enum definition
                        for e in enum_list:
                            if str(e).lower() == matches[0]:
                                logger.debug(f"Coercer: Enum Typo Corrected '{v}' -> '{e}'")
                                v = e
                                break

        expected_type = schema_def.get("type")
        if not expected_type:
            return v

        # 2. Coerce to integer
        if expected_type == "integer":
            if v == "":
                return None
            try:
                if isinstance(v, str):
                    # Handle float/scientific strings first (e.g., "1.0", "1e3")
                    if "." in v or "e" in v.lower():
                        return int(float(v))
                    # Handle base-aware integers (0x, 0o)
                    return int(v, 0)
                return int(v) if isinstance(v, (float, bool)) else v
            except (ValueError, TypeError):
                return v

        # 3. Coerce to boolean
        if expected_type == "boolean":
            if v == "":
                return None
            if isinstance(v, str):
                v_lower = v.lower()
                if v_lower in ("true", "yes", "on"):
                    return True
                if v_lower in ("false", "no", "off"):
                    return False
            elif isinstance(v, (int, float)):
                return bool(v)
            return v

        # 4. Coerce to number (float)
        if expected_type == "number":
            if v == "":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return v

        # 5. Coerce to string (Crucial for labels/data/env)
        if expected_type == "string":
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, (int, float)):
                return str(v)
            return v

        return v
