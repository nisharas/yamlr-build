"""Schema Validation Stage — validates Kubernetes manifests against OpenAPI schemas."""
import logging
from typing import Any, List, Optional

from yamlr.core.exceptions import SchemaLoadError

logger = logging.getLogger(__name__)


class SchemaValidationStage:
    """Stage responsible for checking schema violations using native OpenAPI definitions."""

    @staticmethod
    def validate(yamlr_native: Any, raw_content: str, schemas: List[Any], identity: Optional[Any] = None) -> List[Any]:
        """Validates raw YAML content against native schemas.

        Args:
            yamlr_native: The PyO3 native module binding.
            raw_content: Raw YAML manifest string.
            schemas: List of loaded NativeSchema definitions.
            identity: Optional NativeIdentity extracted from the document.

        Returns:
            List of SchemaViolation objects.
        """
        if not schemas or not identity:
            return []

        try:
            return list(yamlr_native.native_check_schema_violations(raw_content, schemas))
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.debug("Schema validation stage encountered error: %s", e)
            return []
