"""
Yamlr Patch Generator - Plan 1B (Strategic Bridge)
--------------------------------------------------
What: Computes a surgical delta between original and healed manifests.
Why: To support GitOps workflows (Helm/Kustomize) without mutating source templates.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from yamlr.core.utils import get_hardened_yaml

logger = logging.getLogger("yamlr.utils.patch_generator")

class PatchGenerator:
    """
    Utility to generate Kubernetes Strategic Merge Patches.
    """

    @staticmethod
    def generate_and_append(patch_file: Path, original_text: str, healed_text: str):
        """
        Computes patches for all resources in healed_text that differ from original_text.
        """
        parser = get_hardened_yaml()
        orig_docs = list(parser.load_all(original_text))
        heal_docs = list(parser.load_all(healed_text))

        patches = []
        for i, heal_doc in enumerate(heal_docs):
            if i >= len(orig_docs):
                # New resource created by Yamlr (e.g. stubbing)
                patches.append(heal_doc)
                continue

            orig_doc = orig_docs[i]
            if PatchGenerator._is_different(orig_doc, heal_doc):
                patch = PatchGenerator._compute_surgical_patch(orig_doc, heal_doc)
                if patch:
                    patches.append(patch)

        if not patches:
            return

        # [Phase 20] Forensic Journal ACID 1.0: Atomic append via portalocker
        # Why: Prevents corruption when multiple workers attempt to append patches simultaneously.
        import portalocker
        
        mode = "a" if patch_file.exists() else "w"
        try:
            with open(patch_file, mode, encoding="utf-8") as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                if mode == "a":
                    f.write("---\n")
                
                # [STRATEGY] We write a header comment to help users identify the source
                f.write(f"# Yamlr Applied Remediation (Deterministic Patch)\n")
                parser.dump_all(patches, f)
                # Lock is released when file closes (context manager)
        except Exception as e:
            logger.error(f"Failed to write patch journal atomically: {e}")

    @staticmethod
    def _is_different(orig: Any, heal: Any) -> bool:
        """Determines if two resource states differ semantically."""
        # Simple string comparison of dumped YAML is reliable enough for detection
        parser = get_hardened_yaml(typ="safe")
        return parser.dump(orig) != parser.dump(heal)

    @staticmethod
    def _compute_surgical_patch(orig: Any, heal: Any) -> Dict[str, Any]:
        """
        Generates a Strategic Merge Patch.
        
        Why: We preserve the identity (apiVersion, kind, metadata.name) 
             and include only the changed fields.
        """
        if not isinstance(orig, dict) or not isinstance(heal, dict):
            return heal

        # 1. Start with the Identity (Required for Strategic Merge)
        patch = {
            "apiVersion": heal.get("apiVersion"),
            "kind": heal.get("kind"),
            "metadata": {
                "name": heal.get("metadata", {}).get("name"),
                "namespace": heal.get("metadata", {}).get("namespace")
            }
        }
        # Clean up null namespace
        if not patch["metadata"]["namespace"]:
            del patch["metadata"]["namespace"]

        # 2. Compute Recursive Delta for the 'spec' or other non-identity fields
        delta = PatchGenerator._dict_diff(orig, heal)
        
        # We don't want to include identity fields in the delta as they are already in the patch root
        for key in ["apiVersion", "kind", "metadata"]:
            if key in delta:
                if key == "metadata" and isinstance(delta[key], dict):
                    # Only keep metadata fields that aren't name/namespace (e.g. labels)
                    meta_delta = {k: v for k, v in delta[key].items() if k not in ["name", "namespace"]}
                    if meta_delta:
                        patch["metadata"].update(meta_delta)
                    else:
                        # If metadata only had name/ns, and they didn't change, we still keep the outer metadata
                        # but check if we should remove it if no other changes. actually K8s needs name.
                        pass
                del delta[key]

        patch.update(delta)
        return patch

    @staticmethod
    def _dict_diff(orig: Dict[str, Any], heal: Dict[str, Any]) -> Dict[str, Any]:
        """Recursive dictionary diffing."""
        diff = {}
        for k, v in heal.items():
            if k not in orig:
                diff[k] = v
            elif isinstance(v, dict) and isinstance(orig[k], dict):
                sub_diff = PatchGenerator._dict_diff(orig[k], v)
                if sub_diff:
                    diff[k] = sub_diff
            elif v != orig[k]:
                diff[k] = v
        return diff
