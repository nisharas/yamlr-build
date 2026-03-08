"""
Schema Analyzer - Validates API versions against K8s OpenAPI schemas
--------------------------------------------------------------------
Integrates SchemaValidator into the Yamlr pipeline.
"""

import logging
from typing import List

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.validators.schema_validator import SchemaValidator

logger = logging.getLogger("yamlr.analyzers.schema")


class SchemaAnalyzer(BaseAnalyzer):
    """
    Analyzes manifests for invalid API versions.
    
    Uses SchemaValidator to check if apiVersion + kind combinations exist
    in the target Kubernetes version.
    """
    
    def __init__(self, k8s_version: str = "1.31"):
        """
        Initialize schema analyzer.
        
        Args:
            k8s_version: Target Kubernetes version (e.g., "1.31")
        """
        super().__init__()
        self.validator = SchemaValidator(k8s_version)
    
    @property
    def name(self) -> str:
        """Return analyzer name."""
        return "SchemaAnalyzer"
    
    @property
    def analyzer_type(self) -> str:
        """Return analyzer type - operates on manifest content."""
        return "content"
    
    def analyze(self, resources: List[dict], **kwargs) -> List[AnalysisResult]:
        """
        Analyze manifests for invalid API versions.
        
        Args:
            resources: List of parsed YAML manifests
            **kwargs: Additional context (kubernetes_version, etc.)
            
        Returns:
            List of AnalysisResult objects (empty if all valid)
        """
        results = []
        
        # Respect kubernetes_version if passed in kwargs
        target_version = kwargs.get("kubernetes_version")
        if target_version:
            # We don't want to recreate SchemaValidator every time if not needed.
            # But the validator is lightweight enough for now.
            # Safer: check if it's the same version.
            if target_version != self.validator.version:
                self.validator = SchemaValidator(target_version)

        for resource in resources:
            # Extract apiVersion and kind
            api_version = resource.get("apiVersion")
            kind = resource.get("kind")
            
            if not api_version or not kind:
                # Missing apiVersion or kind - will be caught by other analyzers
                continue
            
            # Validate API version
            error = self.validator.validate_api_version(api_version, kind)
            if error:
                # Update resource context in the error
                error.resource_name = resource.get("metadata", {}).get("name", "<unknown>")
                error.resource_kind = kind
                logger.debug(f"Invalid API version: {api_version} for {kind}")
                results.append(error)
        
        return results
