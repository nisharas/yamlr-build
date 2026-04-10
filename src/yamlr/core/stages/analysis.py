"""
Yamlr Analysis Stage
--------------------
What: Executes all registered semantic and schema analyzers.
Why: To detect architectural and security violations in reconstructed models.
Where: Executed as Stage 2 of the Yamlr Engine Pipeline.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
logger = logging.getLogger("yamlr.core.stages.analysis")
from yamlr.core.stages.base import PipelineStage, StageResult
from yamlr.analyzers.registry import AnalyzerRegistry

class AnalysisStage(PipelineStage):
    """
    Analysis Stage (Semantic Scan).
    
    Why: To decouple 'Finding Generation' from 'Remediation' (Healing).
         This ensures a clean dependency graph.
    """

    def __init__(self, catalog: Optional[Dict[str, Any]] = None):
        super().__init__(name="Analysis")
        self.catalog = catalog or {}

    def execute(self, state: PipelineState, engine: Optional[Any] = None) -> StageResult:
        """
        Executes semantic analysis logic.
        """
        from yamlr.parsers.scanner import YamlrScanner
        
        scanner = YamlrScanner(catalog=self.catalog)
        
        try:
            # Stage 2: Identity Analysis and Intent Tagging
            # Why: Populates state.identities for metadata-level analyzers.
            identities = scanner.scan_shards(state.shards)
            state.identities = identities
            
            # Stage 3: Semantic Analysis (The Heart of Yamlr)
            # Why: Replaces 'Ghost Logic' with a live analyzer loop. 
            #      Ensures findings (vulnerabilities, best practices) are available for healers.
            if state.documents:
                from yamlr.analyzers.registry import AnalyzerRegistry
                # [Hardening] Ensure defaults are registered in the current process memory
                AnalyzerRegistry.register_defaults()
                
                analyzers = AnalyzerRegistry.get_all_analyzers(catalog=self.catalog)
                
                findings = []
                for analyzer in analyzers:
                    try:
                        # [Hardening] Support both Metadata and Content-level analysis
                        analyzer_type = getattr(analyzer, "analyzer_type", "content")
                        if analyzer_type in ("metadata", "batch"):
                            doc_findings = analyzer.analyze(state.identities, context=state.context)
                        else:
                            # [V3-PARITY] Pass the full document list for cross-resource analysis
                            doc_findings = analyzer.analyze(state.documents, context=state.context)

                        if doc_findings:
                            if isinstance(doc_findings, list):
                                findings.extend(doc_findings)
                            else:
                                findings.append(doc_findings)
                    except Exception as ae:
                        import traceback
                        logger.error(f"Analyzer {getattr(analyzer, 'name', 'unknown')} failed: {ae}\n{traceback.format_exc()}")

                state.findings = findings
            
            return StageResult(
                success=True,
                metadata={
                    "identities_found": len(identities),
                    "findings_total": len(state.findings)
                }
            )
        except Exception as e:
            logger.error(f"AnalysisStage critical failure: {e}")
            return StageResult(
                success=False,
                errors=[str(e)]
            )
