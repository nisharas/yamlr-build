#!/usr/bin/env python3
import enum
import time
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class HealStatus(str, enum.Enum):
    """
    Standardized execution status for a single manifest file.

    Why: To provide a deterministic lifecycle for the VS Code status bar.
    """

    INITIALIZED = "initialized"
    SCANNING = "scanning"
    HEALED = "healed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNCHANGED = "unchanged"
    IGNORED = "ignored"
    QUOTA_EXCEEDED = "quota_exceeded"


class HealAction(BaseModel):
    """
    Represents a single remediation step taken by the engine.
    
    Why: To provide a forensic audit trail of all changes made to a manifest.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    stage: str
    action_type: str  # 'repair', 'harden', 'optimize'
    target: str      # e.g., 'spec.template.spec.containers[0].image'
    description: str
    rationale: Optional[str] = None
    suggestion: Optional[str] = None
    severity: str = "info"
    rule_id: Optional[str] = None
    scope: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AnalysisResult(BaseModel):
    """
    Represents a single finding (error/warning/info) from the engine.

    Why: Shared contract across CLI, LSP, and Healers.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    analyzer_name: str
    severity: str
    message: str
    resource_name: str = "unknown"
    resource_kind: str = "unknown"
    file_path: str
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None
    line_no: Optional[int] = None
    column_no: Optional[int] = None
    rationale: Optional[str] = None
    impact_description: Optional[str] = None
    risk_level: Optional[str] = None
    external_url: Optional[str] = None
    fix_available: bool = False
    fix_id: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class HealFileResult(BaseModel):
    """
    The final atomic result for a single-file processing pass.

    Why: Unified result structure for VS Code LSP and CLI.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    file_path: str
    success: bool
    status: Union[HealStatus, str]
    full_path: Optional[str] = None
    kind: Optional[str] = None
    error: Optional[str] = None
    remediation_command: Optional[str] = None
    findings: List[Union[AnalysisResult, HealAction]] = Field(default_factory=list)
    logic_logs: List[str] = Field(default_factory=list)
    dna_integrity_score: float = 100.0
    trust_score: float = 100.0
    dna_hash: Optional[str] = None
    original_content: Optional[str] = None
    healed_content: Optional[str] = None
    raw_content: Optional[str] = None  # Alias for backward compat
    written: bool = False
    backup_created: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    processing_stats: Dict[str, Any] = Field(default_factory=dict)
    identities: List[Any] = Field(default_factory=list)
    cluster_version: Optional[str] = None
    processing_time_seconds: float = 0.0
    
    # Truth-in-Healing Metrics
    phy_status: str = "100%"
    kbs_status: str = "100%"
    sem_status: str = "100%"
    reconciled_count: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-style access for UI layer compatibility."""
        return getattr(self, key, default)

    def calculate_integrity_score(self) -> float:
        """Stub for DNA scoring logic."""
        return self.dna_integrity_score


class HealResult(BaseModel):
    """
    Summarized results for a single file or document suite.
    
    Why: To provide a unified result for the UI and CLI layers.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    status: HealStatus
    content: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    dna_integrity_score: float = 0.0
    identities: List[Any] = Field(default_factory=list)
    findings: List[Union[AnalysisResult, HealAction]] = Field(default_factory=list)
    stats: Any = None
    error_message: Optional[str] = None
    pro_features_triggered: bool = False
    reconciled_count: int = 0
    trust_score: float = 100.0
    safety_verdict: str = "N/A"
    safety_messages: List[str] = Field(default_factory=list)
    dna_hash: Optional[str] = None
    phy_status: str = "100%"
    kbs_status: str = "100%"
    sem_status: str = "100%"


class PipelineStats(BaseModel):
    """
    Cumulative telemetry for a processing pass.
    """
    model_config = ConfigDict(extra="ignore")
    lexer_repairs: int = 0
    lexer_typos: int = 0
    migrator_changes: int = 0
    validation_errors: int = 0
    semantic_repairs: int = 0
    security_hardens: int = 0
    shards_parsed: int = 0
    docs_count: int = 0


class PipelineCapabilities(BaseModel):
    """
    Feature flags for the engine.
    """
    model_config = ConfigDict(extra="ignore")
    native_acceleration: bool = True
    comment_preservation: bool = True
    semantic_healing: bool = True


class HealConfig(BaseModel):
    """
    Configuration for the healing engine.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
    
    dry_run: bool = True
    compact: bool = False
    cluster_version: str = "v1.29"
    safety_threshold: float = 70.0
    strict_mode: bool = False
    config_manager: Any = None
    # Remediation Flags (Tier 0/1)
    fix_tags: bool = False
    harden: bool = False
    enforce_probes: bool = False
    harden_net: bool = False
    allowed_registries: List[str] = Field(default_factory=lambda: ["*"])

# --- Model Reconstruction (Pydantic 2.x Forward Refs) ---
HealAction.model_rebuild()
AnalysisResult.model_rebuild()
HealFileResult.model_rebuild()
HealResult.model_rebuild()
HealConfig.model_rebuild()
