"""
Yamlr Schema Validator - Pure Validator Implementation
------------------------------------------------------
Validates Kubernetes manifests against OpenAPI schemas.
Infrastructure concerns (fetching/caching) moved to SchemaStore.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from yamlr.core.validation.schema import SchemaValidator

logger = logging.getLogger("yamlr.schema_validator")
__all__ = ["SchemaValidator"]

# No separate class here, to ensure 100% logic parity and avoid duplication.
# The pro/reconciliation/engine.py module now acts as a redirect to the
# sovereign validator in core.
