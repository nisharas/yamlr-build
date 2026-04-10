"""
Yamlr Schema Validator (Legacy Redirect)
---------------------------------------
Consolidated logic moved to core/validation/schema.py.

Why: To eliminate code duplication and ensure null-safety across all
     validation surfaces. This file remains as a legacy entrypoint.
"""

from __future__ import annotations

from yamlr.core.validation.schema import SchemaValidator

__all__ = ["SchemaValidator"]
