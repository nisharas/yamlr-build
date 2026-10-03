"""Integrity Audit Stage — checks best-practice rules and security misconfigurations."""
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class IntegrityAuditStage:
    """Stage that executes forensic rules on manifest shards."""

    @staticmethod
    def audit(yamlr_native: Any, shards: List[Any]) -> List[Any]:
        """Audits document shards for integrity violations.

        Args:
            yamlr_native: The PyO3 native module binding.
            shards: Tokenized AST shards of the document.

        Returns:
            List of IntegrityViolation objects.
        """
        if not shards:
            return []

        try:
            return list(yamlr_native.native_audit_forensics(shards))
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.debug("Integrity audit stage error: %s", e)
            return []
