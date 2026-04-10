from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from yamlr.core.k8s_utils import extract_containers
from yamlr.analyzers.rules import Rules

if TYPE_CHECKING:
    from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.image_tag")
__all__ = ["ImageTagHealer"]


class ImageTagHealer:
    """
    [Best Practice Healer]
    Ensures all containers use specific image tags instead of ':latest' or no tag.
    """

    DEFAULT_TAG = "stable"  # Industrial default for missing tags

    def heal_doc(self, doc: Dict[str, Any], fix_latest: bool = False, context: Optional[HealContext] = None) -> bool:
        """
        Detects and optionally fixes :latest tags in the document.
        Returns: True if changes were made.
        """
        modified = False

        # Use cached containers if context is available
        all_containers = context.container_context if context else extract_containers(doc)

        # Determine if we have findings that require a fix
        has_finding = False
        if context:
            from yamlr.analyzers.rules import Rules

            # Any image-tag finding in the context for this doc
            # (Note: Analyzer reports 'any' latest in the manifest)
            has_finding = any(f.rule_id == Rules.IMAGE_TAG_CHECK for f in context.findings)

        should_fix = fix_latest or has_finding

        if not should_fix:
            return False

        for _idx, c in enumerate(all_containers):
            if not hasattr(c, "get"):
                continue

            image = c.get("image")
            if not image or not isinstance(image, str):
                continue

            # [Security] Registry Pinning (Blue Team Hardening)
            # Why: Enforces image source validation to prevent supply-chain attacks.
            if context and context.config:
                import fnmatch

                from yamlr.core.exceptions import YamlrSecurityError

                # Extract registry
                registry = "docker.io"  # Default if no slash
                if "/" in image:
                    # e.g. gcr.io/my-proj/my-img -> gcr.io
                    parts = image.split("/")
                    if "." in parts[0] or ":" in parts[0]:
                        registry = parts[0]

                allowed = context.config.allowed_registries
                if not any(fnmatch.fnmatch(registry, pattern) for pattern in allowed):
                    err_msg = f"Untrusted Image Registry Detected: '{registry}' (Image: {image}). Only {allowed} are allowed. Use --unrestricted or update .yamlr.yaml to bypass."
                    logger.critical(err_msg)
                    raise YamlrSecurityError(err_msg)

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
                if should_fix:
                    # Fix: Append default tag if missing, or replace latest
                    base = image.split(":")[0] if ":" in image else image
                    # [PRO] Pin to a stable version instead of a placeholder if possible
                    target_tag = self.DEFAULT_TAG
                    if target_tag == "v0.0.1":
                        target_tag = "stable"  # Industrial default

                    new_image = f"{base}:{target_tag}"
                    c["image"] = new_image
                    modified = True
                    if context:
                        from yamlr.core.stages.boundaries import MutationScope
                        from yamlr.models import HealAction

                        context.prescribe(
                            HealAction(
                                stage="Shield",
                                action_type="harden",
                                target=f"containers[{c.get('name', 'unknown')}].image",
                                description=f"Pinned image tag: {image} -> {new_image}",
                                rationale="Using :latest or implicit latest tags is non-deterministic and risky in production.",
                                suggestion=f"Always use specific version tags or immutable digests (e.g. {new_image}).",
                                severity="warning",
                                rule_id="rule/no-latest-tag",
                                scope=MutationScope.SPEC_IMAGE,
                            )
                        )
                    logger.info(f"Pinned image tag: {image} -> {new_image}")

        return modified
