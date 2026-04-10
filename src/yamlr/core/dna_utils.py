from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Union

__all__ = ["calculate_semantic_dna", "verify_dna"]


def _to_primitives(obj: Any) -> Any:
    """Recursively converts objects to JSON-serializable primitives.

    Why: To handle RuamelNodes and other complex structures that may leak
         into the document tree during Pro-mode reconstruction.
    """
    if isinstance(obj, dict):
        # Ensure stable traversal for DNA hashing [PHASE-19]
        try:
            items = sorted(obj.items(), key=lambda x: str(x[0]))
        except (TypeError, AttributeError):
            items = obj.items()
        return {str(k): _to_primitives(v) for k, v in items}
    elif isinstance(obj, (list, tuple, set)):
        return [_to_primitives(v) for v in obj]
    elif hasattr(obj, "to_dict"):
        return _to_primitives(obj.to_dict())
    elif hasattr(obj, "__dict__"):
        # This handles RuamelNode which wraps the underlying rt-dict
        try:
            return _to_primitives(dict(obj))
        except (TypeError, ValueError):
            return str(obj)
    return obj


def calculate_semantic_dna(docs: Union[List[Dict[str, Any]], str]) -> str:
    """Generates a SHA-256 hash of the data content.

    Why: Provides a format-invariant semantic signature of the manifest.
    """
    if isinstance(docs, str):
        # Handle raw text input by parsing it into semantic structures [PHASE-19-SYNC]
        from yamlr.core.parser.ruamel_adapter import RuamelAdapter

        try:
            adapter = RuamelAdapter()
            # use load_all to handle multi-doc manifests
            parsed = list(adapter.load_all(docs))
            docs = parsed
        except Exception:
            # Fallback to raw string hash if parsing fails (Safety-First)
            return hashlib.sha256(docs.encode("utf-8")).hexdigest()

    # Cleanse documents to ensure 100% JSON compatibility [PRO-12-09]
    primitives = [_to_primitives(d) for d in docs]
    stable_json = json.dumps(primitives, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def verify_dna(docs: Union[List[Dict[str, Any]], str], expected_hash: str) -> bool:
    """Verifies that the semantic DNA matches the expected hash.

    Why: Centralized integrity verification for zero-loss intent proof.
    """
    return calculate_semantic_dna(docs) == expected_hash


class DNAValidator:
    """
    Orchestrates Semantic DNA verification across the engine.

    Why: To provide a 'Single DNA Gate' that can abort operations
         if unintended semantic drift is detected.
    """

    @staticmethod
    def verify_or_abort(content: str, expected_hash: Optional[str] = None):
        """
        Verifies content DNA and raises an exception if verification fails.
        """
        if not expected_hash:
            return  # Skip if no baseline for comparison

        current_hash = calculate_semantic_dna(content)
        if current_hash != expected_hash:
            from yamlr.core.exceptions import YamlrSecurityError

            raise YamlrSecurityError(
                f"🛡️ DNA CORRUPTION DETECTED: Semantic signature mismatch.\n"
                f"Expected: {expected_hash[:12]}...\n"
                f"Actual:   {current_hash[:12]}...\n"
                "ABORTING WRITE to protect manifest integrity."
            )
