from typing import List, Dict, Any, Tuple, Optional
import logging
import re

logger = logging.getLogger("yamlr.healers.image_tag")

class ImageTagHealer:
    """
    [Best Practice Healer]
    Ensures all containers use specific image tags instead of ':latest' or no tag.
    """
    
    DEFAULT_TAG = "v0.0.1" # Placeholder for missing tags
    
    def heal_doc(self, doc: Dict[str, Any], fix_latest: bool = False) -> bool:
        """
        Detects and optionally fixes :latest tags in the document.
        Returns True if changes were made.
        """
        modified = False
        kind = (doc or {}).get("kind") or ""
        spec = (doc or {}).get("spec") or {}

        if kind.lower() == "pod":
            pod_spec = spec
        else:
            tmpl = (spec.get("template") or {})
            pod_spec = (tmpl.get("spec") or {})

        containers = pod_spec.get("containers") or []
        init_containers = pod_spec.get("initContainers") or []
        
        all_containers = containers + init_containers
        
        for idx, c in enumerate(all_containers):
            if not isinstance(c, dict):
                continue

            image = c.get("image")
            if not image or not isinstance(image, str):
                continue

            # Detection Logic
            # Patterns:
            # 1. repo/image@sha256:digest (Digest - Best)
            # 2. repo/image:tag (Tag - OK)
            # 3. repo/image (Implicit Latest - Bad)
            
            has_digest = "@sha256:" in image
            has_tag = ":" in image and not has_digest
            
            is_latest = False
            if has_tag:
                tag = image.split(":")[-1]
                if tag.lower() == "latest":
                    is_latest = True
            elif not has_digest:
                # Implicit latest
                is_latest = True

            if is_latest:
                if fix_latest:
                    # Fix: Append default tag if missing, or replace latest
                    base = image.split(":")[0] if ":" in image else image
                    # [PRO] Pin to a stable version instead of a placeholder if possible
                    target_tag = self.DEFAULT_TAG
                    if target_tag == "v0.0.1":
                        target_tag = "stable" # Industrial default
                    
                    new_image = f"{base}:{target_tag}"
                    c["image"] = new_image
                    modified = True
                    logger.info(f"Pinned image tag: {image} -> {new_image}")

        return modified
