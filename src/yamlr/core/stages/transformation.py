from __future__ import annotations

#!/usr/bin/env python3
"""
Yamlr TRANSFORMATION STAGES - The Scalpels
-----------------------------------
Surgical stages for reconstructing, migrating, and hardening manifests.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-02-15: Reconstruction as a Pipeline Stage**
   - **Context**: Shadow parsing needed to be separated from semantic healing.
   - **Decision**: Create `StageSixReconstruction` to restore ruamel-compatible structure.
   - **Consequence**: 100% comment and formatting preservation guaranteed.

2. **2026-03-23: Safe Migration Guard**
   - **Context**: Deprecated K8s versions require non-destructive API upgrades.
   - **Decision**: Implement `StageSixOneMigration` as a surgical transformation.
   - **Consequence**: Safe API upgrades without impacting non-deprecated fields.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    pass # Heuristic for pro exporter

from yamlr.analyzers.base import AnalysisResult
from yamlr.analyzers.registry import AnalyzerRegistry
from yamlr.core.context import HealContext
from yamlr.core.migrator import MigrationEngine
from yamlr.core.scoring import ScoringEngine
from yamlr.core.stages.base import PipelineStage
from yamlr.parsers.structurer import YamlrStructurer
from yamlr.validators.schema_validator import SchemaValidator

logger = logging.getLogger("yamlr.pipeline.stages.transformation")
__all__ = ['StageFourSemanticAnalysis', 'StageFiveSchemaSelection', 'StageSixReconstruction', 'StageSixOneMigration', 'StageSixFiveContentAnalysis', 'StageEightValidationScoring', 'StageNineSerialization']


class StageFourSemanticAnalysis(PipelineStage):
    """Stage 4: Cross-resource semantic analysis (Metadata level)."""
    def __init__(self, name: str):
        """Initializes the semantic analysis stage.
        
        Why: To prepare the engine for relationship discovery across manifest sets.
        """
        super().__init__(name)

    def run(self, context: HealContext) -> Dict[str, Any]:
        """Executes metadata-level semantic analyzers.
        
        Why: To detect logical mismatches (e.g., port drift) before reconstruction.
        """
        penalty = 0
        try:
            analyzers = [
                a for a in AnalyzerRegistry.get_all_analyzers(catalog=context.catalog)
                if a.analyzer_type == "metadata"
            ]
            scoring = ScoringEngine()
            for analyzer in analyzers:
                try:
                    results = analyzer.analyze(
                        context.identities,
                        kubernetes_version=context.cluster_version,
                        allowed_host_paths=context.allowed_host_paths,
                        trusted_registries=context.trusted_registries
                    )
                    for res in results:
                        context.findings.append(res)
                        res.severity = scoring.get_severity_label(res.severity)
                        penalty += scoring.calculate_penalty(res.rule_id, res.severity)
                except (AttributeError, KeyError, TypeError, ValueError) as analyzer_err:
                    logger.error(f"Analyzer {analyzer.name} failed: {analyzer_err}")
                    # Don't crash the whole pipeline, but log it
                    context.audit_log.append(f"  ⚠️ Analyzer {analyzer.name} failed: {analyzer_err}")
                    
            context.audit_log.append(f"Stage 4: Semantic analysis complete (-{penalty} points)")
            return {"penalty": penalty}
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"Stage 4 failed: {e}")
            return {"penalty": 0, "error": str(e)}

class StageFiveSchemaSelection(PipelineStage):
    """Stage 5: Match resources to Kubernetes OpenAPI schemas."""
    def __init__(self, name: str, find_schema_key_fn: Callable[[str, str], Optional[str]]):
        """Initializes the schema selection stage.
        """
        super().__init__(name)
        self.find_schema_key_fn = find_schema_key_fn

    def run(self, context: HealContext) -> Dict[str, Any]:
        """Matches extracted identities to valid Kubernetes API definitions.
        
        Why: To ensure that reconstruction and healing follow official K8s specifications.
        """
        if not context.identities:
            return {"schema_key": None}
            
        primary = context.identities[0]
        # [Zero-Blindspot] Use the engine's resolved catalog instead of a heavy store
        # The key is expected to be in the catalog already
        schema_key = self.find_schema_key_fn(primary.api_version, primary.kind)
        context.schema_key = schema_key
        
        if schema_key:
            context.audit_log.append(f"Stage 5: Schema matched via {schema_key}")
        else:
            context.audit_log.append("Stage 5: No schema match. Heuristic mode active.")
        return {"schema_key": schema_key}

class StageSixReconstruction(PipelineStage):
    """Stage 6: Reconstruct structured Python objects from Shards."""
    def __init__(self, name: str, structurer: YamlrStructurer):
        """Initializes the reconstruction stage.
        """
        super().__init__(name)
        self.structurer = structurer

    def run(self, context: HealContext) -> Dict[str, Any]:
        """Transforms sharded YAML tokens into high-fidelity Python dictionaries.
        
        Why: Enables logical manipulation and healing of the manifest content.
        """
        try:
            logger.debug(f"Stage 6: Reconstruction running with {len(context.shards)} shards")
            docs = self.structurer.reconstruct(context)
            context.docs = docs
            logger.debug(f"Stage 6: Reconstructed {len(docs)} documents")
            
            typo_count = self._audit_typo_fixes(context)
            dna = self._calculate_dna_receipt(context, docs)
                
            return {"docs": docs, "dna": dna, "typo_count": typo_count}
        except (ValueError, TypeError, AttributeError, KeyError, ImportError) as e:
            logger.error(f"Stage 6 failed: {e}")
            return {"success": False, "error": str(e)}

    def _audit_typo_fixes(self, context: HealContext) -> int:
        """Helper to extract and log typo fixes from shards."""
        typo_count = 0
        for shard in context.shards:
            if hasattr(shard, "intent_tag") and shard.intent_tag and shard.intent_tag.startswith("k8s.typo:"):
                parts = shard.intent_tag.split(":")
                if len(parts) >= 3:
                    context.audit_log.append(f"Fixed typo '{parts[1]}' → '{parts[2]}' (line {shard.line_no})")
                    kbs_kind = context.identities[0].kind if context.identities else "Unknown"
                    kbs_name = context.identities[0].name if context.identities else "unknown"
                    context.findings.append(AnalysisResult(
                        analyzer_name="FuzzyTypoHealer",
                        severity="WARNING",
                        message=f"Auto-fixed structural typo: '{parts[1]}' → '{parts[2]}'",
                        rationale="Yaml files should use the correct K8s schema keys. Relying on auto-healing hides underlying drift.",
                        resource_name=kbs_name,
                        resource_kind=kbs_kind,
                        file_path="unknown",
                        rule_id="yaml/schema-typo",
                        line_number=shard.line_no
                    ))
                typo_count += 1
        return typo_count

    def _calculate_dna_receipt(self, context: HealContext, docs: List[Any]) -> str:
        """Helper to handle DNA calculation for Pro/Free tiers."""
        from yamlr.core.license_manager import LicenseManager
        status, _ = LicenseManager.check_pro_status()
        
        if status.is_usable():
            from yamlr.core.dna_utils import calculate_semantic_dna
            dna = calculate_semantic_dna(docs)
            context.dna_integrity = dna
            context.audit_log.append(f"Stage 6: Reconstructed {len(docs)} document(s) [DNA: {dna[:8]}]")
            return dna
        
        context.audit_log.append(f"Stage 6: Reconstructed {len(docs)} document(s) [DNA: PRO_REQUIRED]")
        return "LOCKED"



class StageSixOneMigration(PipelineStage):
    """Stage 6.1: Automatic migration of deprecated APIs."""
    def __init__(self, name: str, cluster_version: str, enabled: bool = False):
        """Initializes the API migration stage.
        
        Why: To proactively upgrade deprecated manifolds based on target cluster version.
        """
        super().__init__(name)
        self.cluster_version = cluster_version
        self.enabled = enabled

    def run(self, context: HealContext) -> Union[List[Any], Dict[str, Any]]:
        """Executes API migration if enabled for the target cluster version."""
        if not self.cluster_version or not self.enabled:
            context.audit_log.append(f"Stage 6.1: Prophetic Migration skipped (v={self.cluster_version}, enabled={self.enabled})")
            return context.docs

        context.audit_log.append(f"Stage 6.1: Prophetic Migration active (v={self.cluster_version})")

        try:
            migrator = MigrationEngine(target_k8s_version=self.cluster_version)
            migrated_docs, migration_logs = migrator.migrate_all(context.docs)

            from yamlr.core.dna_utils import calculate_semantic_dna
            pre_dna = context.dna_integrity
            post_dna = calculate_semantic_dna(migrated_docs)
            context.dna_integrity = post_dna

            self._process_deprecations(context, migrator)

            if migration_logs:
                context.audit_log.append(f"Stage 6.1: Applied {len(migration_logs)} API migration(s) [DNA: {pre_dna[:8] if pre_dna else 'N/A'} → {post_dna[:8]}]")
                context.audit_log.extend([f"  ✨ {m}" for m in migration_logs])
                context.docs = migrated_docs
                self._sync_identities_with_docs(context, migrated_docs)

            return {"success": True, "modified": len(migration_logs), "docs": migrated_docs}
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.error(f"Migration failed: {e}")
            return {"success": False, "error": str(e), "modified": 0}

    def _process_deprecations(self, context: HealContext, migrator: MigrationEngine):
        """Discovers and logs deprecation findings for all identities."""
        for identity in context.identities:
            dep_info = migrator.checker.check(identity.api_version, identity.kind)
            if dep_info and migrator.checker.is_removed(identity.api_version, identity.kind, self.cluster_version):
                identity.deprecation_info = {
                    "deprecated_api": identity.api_version,
                    "replacement_api": dep_info.replacement_api,
                    "removed_in_version": dep_info.removed_in_version,
                }
                
                context.findings.append(AnalysisResult(
                    analyzer_name="MigrationEngine",
                    severity="WARNING" if dep_info.severity == "WARNING" else "ERROR",
                    message=f"API {identity.api_version} is {dep_info.severity.lower()} in K8s v{self.cluster_version} (Replace with {dep_info.replacement_api})",
                    resource_name=identity.name,
                    resource_kind=identity.kind,
                    file_path="unknown",
                    rule_id="k8s/deprecated-api"
                ))

    def _sync_identities_with_docs(self, context: HealContext, migrated_docs: List[Any]):
        """Ensures identities reflect the upgraded API versions and kinds."""
        for i, doc in enumerate(migrated_docs):
            if i < len(context.identities):
                ident = context.identities[i]
                data = doc.data if hasattr(doc, "data") else doc
                
                new_api = data.get("apiVersion")
                new_kind = data.get("kind")
                
                if new_api and new_api != ident.api_version:
                    ident.api_version = new_api
                if new_kind and new_kind != ident.kind:
                    ident.kind = new_kind

class StageSixFiveContentAnalysis(PipelineStage):
    """Stage 6.5: Run non-metadata (content) analyzers and Shield Shadow Detection."""
    def __init__(self, name: str):
        """Initializes the content analysis stage.
        
        Why: Aggregates content-level detection logic before healers run.
        """
        super().__init__(name)
        try:
            from yamlr.pro.shield import ShieldEngine
            self.shield = ShieldEngine()
        except ImportError:
            self.shield = None

    def run(self, context: HealContext) -> Dict[str, Any]:
        """Executes content-level analysis and shadow risk detection.
        """
        penalty = 0
        try:
            # 1. Standard Content Analyzers
            penalty += self._run_content_analyzers(context)
            # 2. Shield Shadow Risk Detection (Pro)
            if self.shield:
                penalty += self._run_shield_detection(context)
            return {"penalty": penalty}
        except Exception as e:
            logger.error(f"Stage 6.5 failed: {e}")
            return {"penalty": 0}

    def _run_content_analyzers(self, context: HealContext) -> int:
        """Runs registered content-type analyzers."""
        penalty = 0
        analyzers = [a for a in AnalyzerRegistry.get_all_analyzers(catalog=context.catalog) if a.analyzer_type == "content"]
        logger.debug(f"Stage 6.5: Found {len(analyzers)} content analyzers: {[a.name for a in analyzers]}")
        
        # Prepare primitive versions for content analyzers (Stage 6.5)
        doc_primitives = [doc.to_dict() if hasattr(doc, "to_dict") else doc for doc in context.docs]
        
        scoring = ScoringEngine()
        for analyzer in analyzers:
            try:
                results = analyzer.analyze(
                    doc_primitives, 
                    kubernetes_version=context.cluster_version,
                    allowed_host_paths=context.allowed_host_paths,
                    trusted_registries=context.trusted_registries
                )
                for res in results:
                    context.findings.append(res)
                    res.severity = scoring.get_severity_label(res.severity)
                    penalty += scoring.calculate_penalty(res.rule_id, res.severity)
            except Exception as err:
                logger.error(f"Analyzer {analyzer.name} failed: {err}")
                context.audit_log.append(f"  ⚠️ Analyzer {analyzer.name} failed: {err}")
        return penalty

    def _run_shield_detection(self, context: HealContext) -> int:
        """Executes Shield shadow risk detection with graph awareness."""
        penalty = 0
        from yamlr.core.resource_graph import ResourceGraph
        if not context.resource_graph:
            context.resource_graph = ResourceGraph()
            context.resource_graph.build(context.identities)
        
        scoring = ScoringEngine()
        for doc_obj in context.docs:
            shadow_findings = self.shield.detect_shadow_risks(doc_obj, graph=context.resource_graph)
            if shadow_findings:
                for sf in shadow_findings:
                    context.findings.append(sf)
                    penalty += scoring.calculate_penalty(sf.rule_id, sf.severity)
        return penalty

class StageEightValidationScoring(PipelineStage):
    """Stage 8: Final validation and scoring."""
    def __init__(self, name: str, validator: SchemaValidator):
        """Initializes the validation and scoring stage.
        """
        super().__init__(name)
        self.validator = validator

    def run(self, context: HealContext) -> Dict[str, Any]:
        """Validates healed documents against target schemas and calculates health score.
        
        Why: To ensure that all automated repairs result in valid, deployable manifests.
        """
        # [AUDIT-DEBT-01] Use context version for validation
        if context.cluster_version and context.cluster_version != self.validator.version:
            # [PHASE-11] Re-bind to the correct versioned catalog
            # [PHASE-11] Re-bind to the correct versioned catalog via in-memory cache
            from yamlr.core.catalog_manager import CatalogManager
            cm = CatalogManager()
            catalog = cm.get_catalog_data(context.cluster_version)
            if catalog:
                self.validator = SchemaValidator(catalog, context.cluster_version)

        context.audit_log.append(f"Stage 8: Schema Validation (K8s v{self.validator.version})")
        errors = []
        context.doc_findings = {} # Reset for this run
        
        for i, doc in enumerate(context.docs):
            # Convert to primitives for clean error messages
            data = doc.to_dict() if hasattr(doc, "to_dict") else doc
            
            # [PERF] Fast Sample Mode: If doc has massive arrays, skip deep validation
            is_massive = any(isinstance(v, list) and len(v) > 1000 for v in data.values())
            doc_errors = self.validator.validate_full_document(
                data, 
                deep_array_check=not is_massive,
                strict_mode=context.config.strict_mode
            )
            errors.extend(doc_errors)
            context.doc_findings[i] = doc_errors
            
            # Convert to AnalysisResult for audit/reporting
            kind = doc.get("kind", "Unknown")
            name = doc.get("metadata", {}).get("name", "unnamed")
            
            for finding in doc_errors:
                # Ensure findings are correctly localized
                finding.resource_name = name
                finding.resource_kind = kind
                finding.file_path = context.file_path or "unknown"
                context.findings.append(finding)

        # Scoring Logic
        schema_penalty = min(50, len(errors) * 5)
        
        if errors:
            context.audit_log.append(f"  ❌ Schema Validation Failed ({len(errors)} errors)")
        else:
            context.audit_log.append("  ✅ Manifest matches Kubernetes schema")

        return {"penalty": schema_penalty, "errors": errors}

class StageNineSerialization(PipelineStage):
    """Stage 9: Final YAML generation."""
    def __init__(self, name: str, structurer: YamlrStructurer, exporter: Optional[Any] = None, compact: bool = False):
        """Initializes the serialization stage.
        
        Why: To transform Python objects back into comment-preserved YAML strings.
        """
        super().__init__(name)
        self.structurer = structurer
        self.exporter = exporter
        self.compact = compact

    def run(self, context: HealContext) -> Dict[str, str]:
        """Serializes healed documents to the final YAML output.
        
        Why: To provide the user with the final, repaired manifest file.
        """
        # [PRO-12-08] Sovereign Export: If Pro exporter is available, use it for 
        # schema-aware sorting and high-fidelity aesthetics.
        if self.exporter:
            healed_text = self.exporter.sovereign_export(context.docs, context, compact=self.compact)
            context.audit_log.append("Stage 9: Final YAML serialization successful (Sovereign Mode)")
        else:
            healed_text = self.structurer.serialize(
                context.docs, 
                compact=self.compact,
                custom_priority=context.config.custom_sort_order
            )
            context.audit_log.append("Stage 9: Final YAML serialization successful (Legacy Mode)")
        
        context.raw_text = healed_text # For downstream stages (Vacuum)
        return {"content": healed_text}
