#!/usr/bin/env python3
"""
Yamlr TRANSFORMATION STAGES - Stages 4-9
---------------------------------------
Implements the analysis, reconstruction, healing, and serialization phases.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from yamlr.core.stages.base import PipelineStage
from yamlr.core.context import HealContext
from yamlr.analyzers.registry import AnalyzerRegistry
from yamlr.core.scoring import ScoringEngine
from yamlr.parsers.structurer import YamlrStructurer
from yamlr.analyzers.base import AnalysisResult

logger = logging.getLogger("yamlr.pipeline.stages.transformation")

class StageFourSemanticAnalysis(PipelineStage):
    """Stage 4: Cross-resource semantic analysis (Metadata level)."""
    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 4: Semantic Analysis")

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        penalty = 0
        try:
            analyzers = [
                a for a in AnalyzerRegistry.get_all_analyzers()
                if a.analyzer_type == "metadata"
            ]
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
                        res.severity = ScoringEngine.get_severity_label(res.severity)
                        penalty += ScoringEngine.calculate_penalty(res.rule_id, res.severity)
                except Exception as analyzer_err:
                    logger.error(f"Analyzer {analyzer.name} failed: {analyzer_err}")
                    # Don't crash the whole pipeline, but log it
                    context.audit_log.append(f"  ⚠️ Analyzer {analyzer.name} failed: {analyzer_err}")
                    
            context.audit_log.append(f"Stage 4: Semantic analysis complete (-{penalty} points)")
            return {"penalty": penalty}
        except Exception as e:
            logger.error(f"Stage 4 failed: {e}")
            return {"penalty": 0, "error": str(e)}

class StageFiveSchemaSelection(PipelineStage):
    """Stage 5: Match resources to Kubernetes OpenAPI schemas."""
    def __init__(self, find_schema_key_fn: Any):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 5: Schema Selection")
        self.find_schema_key_fn = find_schema_key_fn

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not context.identities:
            return {"schema_key": None}
            
        primary = context.identities[0]
        schema_key = self.find_schema_key_fn(primary.kind, primary.api_version)
        context.schema_key = schema_key
        
        if schema_key:
            context.audit_log.append(f"Stage 5: Schema matched via {schema_key}")
        else:
            context.audit_log.append("Stage 5: No schema match. Heuristic mode active.")
        return {"schema_key": schema_key}

class StageSixReconstruction(PipelineStage):
    """Stage 6: Reconstruct structured Python objects from Shards."""
    def __init__(self, structurer: YamlrStructurer):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 6: Reconstruction")
        self.structurer = structurer

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        try:
            docs = self.structurer.reconstruct(context)
            context.docs = docs
            
            # Audit Typo Fixes (Legacy behavior)
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
            
            
            # [PRO GATE] DNA calculation is purely enterprise
            from yamlr.core.license_manager import LicenseManager
            status, _ = LicenseManager.check_pro_status()
            
            if status.is_usable():
                from yamlr.pro.shield import calculate_semantic_dna
                dna = calculate_semantic_dna(docs)
                context.audit_log.append(f"Stage 6: Reconstructed {len(docs)} document(s) [DNA: {dna[:8]}]")
            else:
                dna = "LOCKED"
                context.audit_log.append(f"Stage 6: Reconstructed {len(docs)} document(s) [DNA: PRO_REQUIRED]")
                
            return {"docs": docs, "dna": dna, "typo_count": typo_count}
        except Exception as e:
            logger.error(f"Stage 6 failed: {e}")
            return {"success": False, "error": str(e)}

from yamlr.core.migrator import MigrationEngine
from yamlr.validators.schema_validator import SchemaValidator
from yamlr.analyzers.base import AnalysisResult
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.pipeline.stages.transformation")

class StageSixOneMigration(PipelineStage):
    """Stage 6.1: Automatic migration of deprecated APIs."""
    def __init__(self, cluster_version: str, enabled: bool = False):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 6.1: Prophetic Migration")
        self.cluster_version = cluster_version
        self.enabled = enabled

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.cluster_version or not self.enabled:
            context.audit_log.append(f"Stage 6.1: Prophetic Migration skipped (v={self.cluster_version}, enabled={self.enabled})")
            return context.docs

        context.audit_log.append(f"Stage 6.1: Prophetic Migration active (v={self.cluster_version})")

        try:
            migrator = MigrationEngine(target_k8s_version=self.cluster_version)
            migrated_docs, migration_logs = migrator.migrate_all(context.docs)

            # Update identities with deprecation info & Add Findings
            for identity in context.identities:
                dep_info = migrator.checker.check(identity.api_version, identity.kind)
                if dep_info and migrator.checker.is_removed(identity.api_version, identity.kind, self.cluster_version):
                    identity.deprecation_info = {
                        "deprecated_api": identity.api_version,
                        "replacement_api": dep_info.replacement_api,
                        "removed_in_version": dep_info.removed_in_version,
                    }
                    
                    # Add to Findings
                    finding = AnalysisResult(
                        analyzer_name="MigrationEngine",
                        severity="WARNING" if dep_info.severity == "WARNING" else "ERROR",
                        message=f"API {identity.api_version} is {dep_info.severity.lower()} in K8s v{self.cluster_version} (Replace with {dep_info.replacement_api})",
                        resource_name=identity.name,
                        resource_kind=identity.kind,
                        file_path="unknown", # Will be filled by higher level
                        rule_id="k8s/deprecated-api"
                    )
                    context.findings.append(finding)

            if migration_logs:
                context.audit_log.append(f"Stage 6.1: Applied {len(migration_logs)} API migration(s)")
                context.audit_log.extend([f"  ✨ {m}" for m in migration_logs])
                context.docs = migrated_docs
            return {"success": True, "modified": len(migration_logs), "docs": migrated_docs}
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {"success": False, "error": str(e), "modified": 0}

class StageSixFiveContentAnalysis(PipelineStage):
    """Stage 6.5: Run non-metadata (content) analyzers."""
    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 6.5: Content Analysis")

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        penalty = 0
        try:
            analyzers = [
                a for a in AnalyzerRegistry.get_all_analyzers()
                if a.analyzer_type == "content"
            ]
            for analyzer in analyzers:
                try:
                    results = analyzer.analyze(
                        context.docs, 
                        kubernetes_version=context.cluster_version,
                        allowed_host_paths=context.allowed_host_paths,
                        trusted_registries=context.trusted_registries
                    )
                    for res in results:
                        context.findings.append(res)
                        res.severity = ScoringEngine.get_severity_label(res.severity)
                        penalty += ScoringEngine.calculate_penalty(res.rule_id, res.severity)
                except Exception as analyzer_err:
                    logger.error(f"Analyzer {analyzer.name} failed: {analyzer_err}")
                    context.audit_log.append(f"  ⚠️ Analyzer {analyzer.name} failed: {analyzer_err}")
                    
            return {"penalty": penalty}
        except Exception as e:
            logger.error(f"Stage 6.5 failed: {e}")
            return {"penalty": 0}

class StageEightValidationScoring(PipelineStage):
    """Stage 8: Final validation and scoring."""
    def __init__(self, validator: SchemaValidator):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 8: Validation")
        self.validator = validator

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        # [AUDIT-DEBT-01] Use context version for validation
        if context.cluster_version and context.cluster_version != self.validator.version:
            self.validator = SchemaValidator(context.cluster_version)

        context.audit_log.append(f"Stage 8: Schema Validation (K8s v{self.validator.version})")
        errors = []
        for doc in context.docs:
            doc_errors = self.validator.validate_full_document(doc)
            errors.extend(doc_errors)
            
            # Convert to AnalysisResult for audit/reporting
            kind = doc.get("kind", "Unknown")
            name = doc.get("metadata", {}).get("name", "unnamed")
            
            for err_msg in doc_errors:
                finding = AnalysisResult(
                    analyzer_name="SchemaValidator",
                    severity="ERROR",
                    message=err_msg,
                    resource_name=name,
                    resource_kind=kind,
                    file_path=context.audit_log[0].split(": ")[-1] if ":" in context.audit_log[0] else "unknown", # Heuristic for file path
                    rule_id="schema/validation-error"
                )
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
    def __init__(self, structurer: YamlrStructurer, compact: bool = False):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 9: Serialization")
        self.structurer = structurer
        self.compact = compact

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        healed_text = self.structurer.serialize(context.docs, compact=self.compact)
        context.audit_log.append("Stage 9: Final YAML serialization successful")
        return {"content": healed_text}
