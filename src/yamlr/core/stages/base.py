"""
Yamlr Pipeline Stage - Base Interface
------------------------------------
What: Defines the contract for all logic layers (Physicist, Healer, Judge).
Why: To enforce strict tiered execution and zero-side-effect logic.
Where: Inherited by all stages in yamlr.core.stages.*
"""

from __future__ import annotations

"""
Yamlr SAFEGUARD & RISK - Operational Stability Guardrails
--------------------------------------------------------
Implements Stage 5.5 Safeguard and Breaking Change Detection.

Why: To ensure that Yamlr remains a 'Zero-Failure Trust Pillar'. 
     The ResourceGuard prevents OOM crashes during massive 100k manifest 
     scaling passes, while the breaking-detector prevents accidental 
     downtime from automatic reconciliation.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from pydantic import BaseModel, Field

class StageResult(BaseModel):
    """Immutable state handover between pipeline stages."""
    success: bool
    findings: List[Any] = []
    metadata: Dict[str, Any] = {}
    next_action: Optional[str] = None
    errors: List[str] = []

class PipelineState(BaseModel):
    """
    Mutable state table for a single manifest pipeline session.
    
    Why: To provide a type-safe, deterministic container for 
         shards, identities, and documents as they flow through stages.
    """
    content: str
    shards: List[Any] = Field(default_factory=list)
    identities: List[Any] = Field(default_factory=list)
    documents: List[Any] = Field(default_factory=list)
    findings: List[Any] = Field(default_factory=list)
    context: Any  # HealContext

    class Config:
        arbitrary_types_allowed = True

class PipelineStage(ABC):
    """
    Abstract Base Class for all Yamlr Pipeline Stages.
    
    Why: To provide a unified contract for the YamlrEngine to execute 
         disparate logic (Normalization, Analysis, Healing) in a 
         deterministic sequence.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def execute(self, state: PipelineState, engine: Optional[Any] = None) -> StageResult:
        """
        Executes the stage logic on the provided state.
        
        Args:
            state: The current 'PipelineState' containing manifest shards, 
                   identities, and documents.
                   
        Returns:
            A StageResult containing the outcome and any new findings.
        """
        pass

    def __repr__(self) -> str:
        return f"<Stage:{self.name}>"
