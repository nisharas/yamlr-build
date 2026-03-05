#!/usr/bin/env python3
"""
Scanner IDENTITY Mixin
----------------------
Identity convergence, sovereign alignment, filtering, and collision logic.

Why: Extracted from scanner.py to enforce the <500 line modularity rule.
This mixin provides all identity management methods that YamlrScanner inherits.

Architecture: Mixin pattern — shares state via `self` with the main class.
All methods are private (_prefixed) and called only by YamlrScanner internals.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-17
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.scanner")


class IdentityMixin:
    """
    Identity convergence and filtering methods for YamlrScanner.

    Responsibilities:
    - Document flushing and state transitions
    - Sovereignty Convergence Algorithm (anchor drift correction)
    - Identity collision detection and logging
    - OSS identity filtering (strict K8s compliance)
    - Pro identity filtering (intelligent inference)
    """

    # =========================================================================
    # INTERNAL LOGIC: IDENTITY MANAGEMENT & CONVERGENCE
    # =========================================================================

    def _flush_current_identity(self) -> None:
        """
        Finalizer for the current YAML document.
        Runs the Sovereign Alignment algorithm before flushing to the result set.

        This stage handles "Transition Physics": closing the current metadata
        context and preparing the volatile state for the next document in a
        multi-doc stream. High-fidelity reset of all trackers is performed here.
        """
        # [PHASE 3: IDENTITY CONVERGENCE]
        # Use the Archeologist algorithm to align identity markers across depths.
        self._finalize_identity_alignment()

        # Only store if we found at least a hint of identity.
        if self._current_identity.kind or self._current_identity.api_version:
            self._current_identity.doc_index = self._doc_index
            self.identities.append(self._current_identity)

        # Volatile Reset: Prepare for the next potential manifest.
        self._current_identity = ManifestIdentity()
        self._path_stack = []
        self._in_global_metadata = False
        self._doc_index += 1

        # Flush sovereignty candidates for the next potential document.
        for k in self._sovereign_candidates:
            self._sovereign_candidates[k] = []

    # =========================================================================
    # SOVEREIGNTY CONVERGENCE ALGORITHM
    # =========================================================================
    """
    The Sovereignty Convergence Algorithm (SCA) handles the "Anchor Drift"
    scenario common in copy-pasted Kubernetes manifests.

    When a developer pastes a 'Service' manifest into a 'Deployment'
    but accidentally indents the 'kind' and 'apiVersion' fields, most
    tools fail to recognize the document root.

    SCA Heuristics:
    - Candidate Collection: Every instance of Kind/API is recorded with depth.
    - Shallowest Selection: The scanner identifies the highest unique
      occurrence as the "Grand Sovereign".
    - Identity Promotion: Drifted anchors are promoted to the root
      identity object, enabling Stage 4 (Structurer) to apply the
      correct schema even if the file is structurally malformed.
    """

    def _finalize_identity_alignment(self) -> None:
        """
        [THE IDENTITY ARCHEOLOGIST]
        Implements the Sovereignty Convergence Algorithm for Anchor keys.

        Corrects Anchor Drift:
        If 'kind' or 'apiVersion' are accidentally indented, normal scanners
        lose identity context. The Archeologist tracks every instance and
        promotes the "shallowest" unique candidates to the root identity.

        Forensic Strategy:
        By analyzing the positional physics of identity markers, we can
        handle malformed YAML where identity markers are accidentally nested.
        This is a high-confidence recovery heuristic that prevents total
        resource rejection in Stage 3.
        """
        for key in ["kind", "apiVersion"]:
            instances = self._sovereign_candidates.get(key, [])
            if not instances:
                continue

            # Identity Convergence: Find the "shallowest" Anchor.
            key_min_indent = min(i[0] for i in instances)
            candidates = [i for i in instances if i[0] == key_min_indent]

            if len(candidates) == 1:
                # Promotion Path: Unique high-confidence anchor.
                val = candidates[0][1]
                was_drifted = (key_min_indent > 0)

                if key == "kind":
                    self._current_identity.kind = val
                else:
                    self._current_identity.api_version = val

                if was_drifted:
                    # Forensic Log: Promoter narrative for the audit trail.
                    msg = f"Doc {self._doc_index}: Promoted drifted '{key}: {val}' (indent {key_min_indent}) to root identity."
                    logger.info(msg)
                    self.scan_logs.append(msg)
                    self._current_identity.was_repaired = True

            elif len(candidates) > 1:
                # Collision Path: Ambiguous markers found at the same depth.
                self._log_identity_collision(key, key_min_indent)

    def _log_identity_collision(self, key: str, depth: int) -> None:
        """
        Logs a detailed identity collision error for the audit trail.

        Rationale:
        Multiple markers at the same depth indicate a fundamental structural
        ambiguity. We force a null identity to guarantee that the user
        performs a manual UAT review of the manifest. This prevents
        accidental application of the wrong resource type to the cluster.
        """
        msg = f"Doc {self._doc_index}: IDENTITY_COLLISION! Multiple '{key}' markers at indent {depth}."
        logger.error(msg)
        self.scan_logs.append(msg)

        # Invalidate the identity to force manual audit.
        if key == "kind":
            self._current_identity.kind = None
        else:
            self._current_identity.api_version = None

    def _filter_identities_oss(self) -> List[ManifestIdentity]:
        """
        OSS Identity Filter: Strict K8s Compliance checks.

        Standard Rules:
        Both Kind AND apiVersion must be present. This is a non-negotiable
        requirement for standard OSS validation.

        Diagnostic Narrative:
        Provides verbose hints to help the user resolve identity missingness.
        Each branch is expanded with example fixes to ensure the user can
        recover their manifest without needing Pro features immediately.

        Returns:
            List[ManifestIdentity]: Validated resources.
        """
        valid_ids = []
        skipped_count = 0

        for idnt in self.identities:
            if idnt.kind and idnt.api_version:
                valid_ids.append(idnt)
            else:
                skipped_count += 1

                # High-Fidelity Forensic Messaging for OSS users.
                if not idnt.kind and not idnt.api_version:
                    logger.error(f"Doc {idnt.doc_index}: Fragmented-Identity! Missing BOTH kind/apiVersion. Skipping.")
                elif not idnt.kind:
                    logger.error(
                        f"Doc {idnt.doc_index}: Missing 'kind' field (apiVersion: {idnt.api_version}). "
                        f"Hint: Add 'kind: <Resource>' at root level. (Example: 'kind: Pod')"
                    )
                    logger.info("Compliance Check: Resource type must be explicitly declared for serialization.")
                else:
                    logger.error(
                        f"Doc {idnt.doc_index}: Missing 'apiVersion' field (kind: {idnt.kind}). "
                        f"Hint: Add 'apiVersion: <version>' at root. (Example: 'apiVersion: v1')"
                    )
                    logger.info(f"Pro-Mode Hint: {self.pro_brand} can auto-infer this using the schema catalog.")
                    logger.info("Standardization: Always specify API versions to avoid runtime ambiguity.")

        if skipped_count > 0:
            logger.warning(f"OSS mode: Skipped {skipped_count} documents. Upgrade to {self.pro_brand} for repair logic.")

        return valid_ids

    def _filter_identities_pro(self) -> List[ManifestIdentity]:
        """
        Pro Identity Filter: Intelligent Inference heuristics.

        Heuristic Capabilities:
        Auto-completes apiVersion from Kind using the internal catalog search space.
        This is particularly useful for ancient manifests where the API
        versioning has drifted from current production standards.

        Audit Trail:
        Each repair is recorded in the ManifestIdentity object, ensuring that
        the later Stages (Structurer/Shield) are aware that identity was
        inferred rather than explicitly stated.
        """
        valid_ids = []
        for idnt in self.identities:
            if idnt.kind and idnt.api_version:
                valid_ids.append(idnt)
                continue
            if idnt.kind and not idnt.api_version:
                inferred = self.api_inferrer.infer_version(idnt.kind)
                if inferred:
                    logger.warning(f"Doc {idnt.doc_index}: Auto-inferred apiVersion '{inferred}' for '{idnt.kind}'.")
                    idnt.api_version = inferred
                    idnt.was_repaired = True
                    valid_ids.append(idnt)
                    continue
                else:
                    logger.error(f"Doc {idnt.doc_index}: Cannot infer apiVersion for unknown kind '{idnt.kind}'.")

            # Final Fallback: Reject totally unidentified fragments.
            logger.error(f"Doc {idnt.doc_index}: Unidentified resource fragment. Skipping.")
        return valid_ids
