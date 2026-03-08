"""
Security validation logic for Yamlr Engine.

Why: To protect against directory traversal and unsafe hostPath mounts in Kubernetes manifests.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger("yamlr.engine.security")

def validate_absolute_paths(docs: List[Dict[str, Any]], allowed_host_paths: List[str]) -> List[str]:
    """
    Scans document for hostPath absolute paths and verifies against whitelist.
    
    Why: To prevent attackers from mounting arbitrary sensitive host paths (like /etc/shadow)
    into containers via malformed manifests.
    """
    errors = []

    def check_node(node, path_context=""):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if isinstance(node, dict):
            # Specific check for hostPath in volumes
            if "hostPath" in node and isinstance(node["hostPath"], dict):
                hp = node["hostPath"].get("path")
                if hp:
                    import os
                    # [Fix] Resolve and normalize path to prevent traversal bypass
                    # Since we don't have the "host" root, abspath is the best local proxy 
                    # for normalization of '..' relative segments.
                    normalized_path = os.path.abspath(hp)
                    
                    # Check if it starts with any allowed path
                    if not any(
                        normalized_path.startswith(allowed)
                        for allowed in allowed_host_paths
                    ):
                        errors.append(
                            f"Unsafe hostPath at {path_context}/hostPath: {hp} (Normalized: {normalized_path})"
                        )

            for k, v in node.items():
                check_node(v, f"{path_context}/{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_node(item, f"{path_context}[{i}]")

    for i, doc in enumerate(docs):
        check_node(doc, f"doc[{i}]")

    return errors
