#!/usr/bin/env python3
"""
Yamlr SCANNER - The Identity Archeologist
-----------------------------------------
Mines identity markers from Yamlr Shards to extract the "Manifest DNA".
Strictly isolates global metadata from nested template metadata.

Architecture:
Uses an indentation stack to navigate the YAML hierarchy without a full parser.
This allows Stage 3 to identify the resource Kind/API before the Structurer
even begins building the tree.

CNCF Standards Compliance:
- Vendor Neutral: Focuses on standard K8s Resource model.
- Robust: Block-safe and multi-document aware.
- Non-Destructive: Reads shards without modifying them.
- Interoperable: Aligns with cloud-native schema standards (OpenAPI, JSONSchema).

Phase 3 Enhancements:
- Future-proof multi-schema architecture (K8s, OpenAPI, CRDs, plugins)
- Integrated with enhanced Lexer metadata (prepare_for_scanner)
- Schema-aware intent tagging with catalog integration
- Repair context correlation for audit trails
- Enhanced confidence scoring integration

OSS Patch:
- Enhanced Intent Tagging: Now tags structural K8s keys (spec, data, containers)
  to ensure the Confidence Engine accurately recognizes valid manifests.
- Multi-document isolation: Ensures clean state resets between '---' shards.

Sovereignty Alignment:
Implements the "Sovereign Key" pattern: identifying shallowest candidates
for kind/apiVersion and promoting drifted anchors to the root identity.
This is critical for handling malformed YAML where identity markers
are accidentally indented.

Modularity:
Decomposed into focused mixins (scanner_identity, scanner_heuristics,
scanner_forensics) per the <500 line modularity rule. This file serves
as the coordinator, retaining __init__, scan_shards, and state management.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-17
Version: 1.2.1 (Modular Decomposition)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from yamlr.core.deprecations import DeprecationChecker
from yamlr.models import ManifestIdentity, Shard
from yamlr.parsers.api_inference import APIVersionInferrer
from yamlr.parsers.scanner_forensics import ForensicsMixin
from yamlr.parsers.scanner_heuristics import HeuristicsMixin
from yamlr.parsers.scanner_identity import IdentityMixin
from yamlr.parsers.schema_manager import SchemaManager

logger = logging.getLogger("yamlr.scanner")


# =============================================================================
# THE IDENTITY ARCHEOLOGIST
# =============================================================================
__all__ = ["YamlrScanner"]


class YamlrScanner(IdentityMixin, HeuristicsMixin, ForensicsMixin):
    """
    Analyzes Shards to identify Kubernetes resources and tag semantic intent.

    Logic and Heuristics:
    1. Path Tracking: Uses an indentation stack (Indentation Physics) to ensure
       'metadata.name' is only captured at the document root, not inside
       a Pod template.
    2. Document Awareness: Correctly handles multi-document (---) boundaries
       by performing a full state flush and identity alignment.
    3. Intent Mapping: Tags shards with semantic labels (e.g., k8s.spec)
       to assist the Pipeline's downstream confidence scoring engine.
    4. Schema Integration: Supports a multi-catalog architecture for K8s core,
       OpenAPI v3, CRDs, and user-provided schema plugins.
    5. Sovereign Alignment: Employs a post-scan convergence algorithm to promote
       drifted 'Sovereign Keys' (kind/apiVersion) to the root identity.

    This class serves as Stage 3 of the Yamlr Pipeline. It is responsible for
    the "Identity Convergence" phase where raw shards gain semantic meaning.

    Mixins:
    - IdentityMixin: Sovereignty convergence, filtering, collision logic
    - HeuristicsMixin: Intent tagging, path tracking, metadata extraction
    - ForensicsMixin: Audit logging, deprecation checks, Pro detection
    """

    # =========================================================================
    # ARCHITECTURAL NARRATIVE: INDENTATION PHYSICS
    # =========================================================================
    """
    The "Indentation Physics" engine is the heart of the Identity Archeologist.

    Traditional YAML parsers build a full document object model (DOM) before
    allowing inspection. Yamlr's Scanner performs "In-Flight Identification"
    by tracking the relative indentation of keys as they stream through the
    Lexer.

    Core Principles:
    1. Zero-Trust Indentation: We do not assume the YAML is well-formed.
    2. Vertical Scope Tracking: The path_stack tracks the logical lineage
       of the current shard.
    3. Contextual Isolation: We use the lineage to distinguish between
       global metadata and nested template metadata.

    This approach allows Yamlr to identify the resource type even in
    partially corrupted files where a full parser would throw an
    IndentationError. It is the "Forensic Glue" of Stage 3.
    """

    def __init__(
        self,
        catalog: Optional[Dict[Any, Any]] = None,
        schema_type: str = "kubernetes",
        app_name: str = "Yamlr",
        pro_brand: str = "Yamlr Enterprise (Pro)",
        **schema_sources,
    ):
        """
        Initializes the scanner with schema catalog(s) and branding.

        Future-Proof Multi-Catalog Support:
        The scanner accepts multiple catalog sources to support hybrid schema
        environments (K8s + OpenAPI + CRDs). This enables Yamlr to expand beyond
        Kubernetes into general cloud-native manifests without breaking logic.

        Args:
            catalog: Primary schema catalog (K8s core + CRDs)
            schema_type: Schema format type ("kubernetes", "openapi", "mixed")
            app_name: Branding for CLI and log messages (default: "Yamlr")
            pro_brand: Specific branding for Enterprise features (default: "Yamlr Enterprise (Pro)")
            **schema_sources: Additional schema catalogs for future expansion
                - openapi_catalog: OpenAPI 3.0 schema definitions
                - crd_catalog: Custom Resource Definition catalog
                - plugin_catalogs: User-provided schema plugins (list)
        """
        # Primary branding and configuration tokens
        self.catalog = catalog or {}
        self.schema_type = schema_type
        self.app_name = app_name.capitalize()
        self.pro_brand = pro_brand

        # Future expansion: Multi-catalog registration for hybrid parsing
        self.openapi_catalog = schema_sources.get("openapi_catalog", {})
        self.crd_catalog = schema_sources.get("crd_catalog", {})
        self.plugin_catalogs = schema_sources.get("plugin_catalogs", [])

        # Result store: Accumulates identities found in a single file stream.
        self.identities: List[ManifestIdentity] = []

        # Current Document State (Volatile, reset on doc boundaries)
        self._current_identity = ManifestIdentity()
        self._path_stack: List[Tuple[int, str]] = []
        self._in_global_metadata = False
        self._in_freeform_block = False
        self._doc_index = 0
        self.deep_array_check = True

        # Lexer Metadata Integration (Phase 3 Context)
        self._lexer_context: Optional[Dict[str, Any]] = None

        # Build unified structure keys from all registered catalogs.
        self.schema_manager = SchemaManager(
            catalog=self.catalog,
            openapi_catalog=self.openapi_catalog,
            crd_catalog=self.crd_catalog,
            plugin_catalogs=self.plugin_catalogs,
        )
        self._known_structure_keys = self.schema_manager.get_structure_keys()

        # Detailed Schema Initialization Audit for forensic debugging.
        self._log_schema_initialization_verbose()

        # Core Dependencies for API lifecycle and inference.
        self.deprecation_checker = DeprecationChecker()
        self.api_inferrer = APIVersionInferrer(
            catalog=self.catalog, crd_catalog=self.crd_catalog, plugin_catalogs=self.plugin_catalogs
        )

        # Pro Mode Detection
        self.pro_mode = schema_sources.get("pro_mode", self._detect_pro_mode())

        if self.pro_mode:
            logger.debug(f"Scanner initialized in PRO mode (intelligent repair enabled via {self.pro_brand})")
        else:
            logger.debug("Scanner initialized in Free Version (strict validation)")

        # Sovereignty Candidates: Tracks potentially 'root' keys that suffered drift.
        self._sovereign_candidates: Dict[str, List[Tuple[int, str, int]]] = {
            "kind": [],
            "apiVersion": [],
            "metadata": [],
            "spec": [],
        }

        # Forensic Log Store
        self.scan_logs: List[str] = []

    # =========================================================================
    # PHASE 3: LEXER METADATA INTEGRATION
    # =========================================================================

    def set_lexer_context(self, lexer_metadata: Dict[str, Any]) -> None:
        """
        Receives metadata from the enhanced Lexer for context-aware scanning.

        Args:
            lexer_metadata: Output from lexer.prepare_for_scanner()
                - indent_context: Dictionary of nesting structures
                - repair_stats: Summary of fixes performed (counts)
                - structure_hints: Global patterns found (lists vs maps)
        """
        self._lexer_context = lexer_metadata

        # Telemetry Log: Receive Lexer stats to align extraction confidence.
        if lexer_metadata.get("repair_stats"):
            total_fixes = sum(lexer_metadata["repair_stats"].values())
            if total_fixes > 0:
                logger.debug(f"Scanner received telematic lexer context: {total_fixes} structural repairs performed.")

        # Telemetry Log: Document structure hints for forensic audit.
        if lexer_metadata.get("structure_hints"):
            hints = lexer_metadata["structure_hints"]
            logger.debug(
                f"Structure hints received: {hints.get('document_count', 0)} documents, "
                f"max depth={hints.get('max_nesting_depth', 0)}, "
                f"array_heavy={hints.get('has_lists', False)}"
            )

    # =========================================================================
    def fast_scan(self, raw_yaml: str) -> List[ManifestIdentity]:
        """
        Ultra-fast identity extraction bypassing the Shard loop.
        Uses the native Rust implementation if available, with a Python
        safety check for identity collisions.
        """
        if self._has_identity_collision(raw_yaml):
            logger.debug(
                "Identity collision detected in raw YAML. Falling back to Python scanner for diagnostic precision."
            )
            return self.scan_shards(self._get_shards_fallback(raw_yaml))

        try:
            try:
                from yamlr_native import fast_scan
            except ImportError:
                from yamlr.native import fast_scan
            raw_results = fast_scan(raw_yaml)

            identities = []
            for res in raw_results:
                identities.append(
                    ManifestIdentity(
                        kind=res.get("kind"),
                        api_version=res.get("api_version"),
                        name=res.get("name"),
                        namespace=res.get("namespace"),
                        was_repaired=False,  # Fast scan is discovery-only
                    )
                )
            return identities
        except (ImportError, Exception) as e:
            logger.debug(f"Native fast_scan failed or unavailable: {e}. Falling back to Python.")
            return self.scan_shards(self._get_shards_fallback(raw_yaml))

    def _has_identity_collision(self, raw_yaml: str) -> bool:
        """
        Lightweight check for multiple root-level 'kind' or 'apiVersion' keys.
        Supports multi-document manifests with low memory overhead.
        """
        import re

        # Single-pass regex for document boundaries and identity markers at indent 0
        pattern = re.compile(r"(?m)^(?:---$|kind\s*:|apiVersion\s*:)")

        has_kind = False
        has_api = False

        for match in pattern.finditer(raw_yaml):
            marker = match.group(0).strip()

            if marker == "---":
                # Reset for next document
                has_kind = False
                has_api = False
            elif marker.startswith("kind"):
                if has_kind:
                    return True
                has_kind = True
            elif marker.startswith("apiVersion"):
                if has_api:
                    return True
                has_api = True

        return False

    def _get_shards_fallback(self, raw_yaml: str) -> List[Shard]:
        from yamlr.parsers.lexer import YamlrLexer

        lexer = YamlrLexer()
        return lexer.shard(raw_yaml)

    # PUBLIC API: SHARD SCANNING (STAGE 3)
    # =========================================================================

    def scan_shards(self, shards: List[Shard], mode: str = "infer") -> List[ManifestIdentity]:
        """
        [Stage 3] The Main Entry Point for Identity Archeology.
        """
        self._reset_state()
        min_indent = 999

        for shard in shards:
            if shard.is_doc_boundary:
                self._flush_doc_state()
                min_indent = 999
                continue

            if shard.is_block:
                continue

            if shard.key and shard.indent < min_indent:
                min_indent = shard.indent

            self._update_path_context(shard)

            if not shard.key:
                continue

            key = shard.key.strip()
            val = self._clean_id(shard.value)

            # Healer Tier 0: Typo Correction
            key = self._check_and_fix_typo(shard, key)

            self._tag_intent(shard, key)
            self._extract_cross_resource_metadata(shard, key, val)

            # Sovereignty Tracking
            if key in self._sovereign_candidates:
                self._sovereign_candidates[key].append((shard.indent, val, shard.line_no))

            # Identity Extraction logic
            is_root = shard.indent == min_indent
            self._process_identity_marker(shard, key, val, is_root)

        self._flush_current_identity()
        return self._finalize_scan(mode)

    def _flush_doc_state(self) -> None:
        """Resets state for a new document boundary."""
        self._flush_current_identity()
        # Reset doc-specific markers if needed (implemented in IdentityMixin/HeuristicsMixin)

    def _check_and_fix_typo(self, shard: Shard, key: str) -> str:
        """Applies fuzzy typo correction to K8s keys."""
        # [ROUND-10] Defensive: Skip fuzzy matching for very short keys to prevent accidental identity collisions (e.g. 'app' -> 'kind')
        if len(key) < 4:
            return key

        if key not in self._known_structure_keys and not self._in_freeform_block:
            suggestion = self.schema_manager.fuzzy_match(key, kind=self._current_identity.kind)
            if suggestion:
                shard.intent_tag = f"k8s.typo:{key}:{suggestion}"
                logger.debug("Stage 3 Typo Corrected: '%s' → '%s' (line %d)", key, suggestion, shard.line_no)
                return suggestion
        return key

    def _process_identity_marker(self, shard: Shard, key: str, val: str, is_root: bool) -> None:
        """Identifies core K8s identity markers (kind, version, name)."""
        if is_root:
            if key == "kind":
                self._current_identity.kind = val
            elif key == "apiVersion":
                self._current_identity.api_version = val
            elif key == "name" and not self._current_identity.name:
                self._current_identity.name = val

        if self._in_global_metadata and not shard.is_list_item:
            if key == "name" and not self._current_identity.name:
                logger.debug(
                    f"[SCANNER] Setting name to '{val}' for {self._current_identity.kind} (Line {shard.line_no})"
                )
                self._current_identity.name = val

    def _finalize_scan(self, mode: str) -> List[ManifestIdentity]:
        """Applies license-based filtering and audits."""
        if mode == "strict":
            valid_ids = self._filter_identities_oss()
        elif self.pro_mode:
            valid_ids = self._filter_identities_pro()
        else:
            valid_ids = self._filter_identities_oss()

        self._log_scan_summary_verbose(valid_ids)
        self._audit_deprecations(valid_ids)
        return valid_ids

    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================

    def _reset_state(self) -> None:
        """Resets the "Archeology Table" for a fresh file scan session."""
        self.identities = []
        self._current_identity = ManifestIdentity()
        self._path_stack = []
        self._in_global_metadata = False
        self._in_freeform_block = False
        self._doc_index = 0
        self._lexer_context = None
        self.scan_logs = []
        for k in self._sovereign_candidates:
            self._sovereign_candidates[k] = []
