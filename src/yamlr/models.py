#!/usr/bin/env python3
"""
Yamlr CORE MODELS - The Forensic DNA Contract
---------------------------------------------
Defines the fundamental data structures used across the Yamlr engine.

Why: Re-exports established models from specialized sub-modules to maintain
     backward compatibility while breaking circular import chains.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

# --- Level 2: Execution Results ---
from yamlr.core.engine.models import (
    AnalysisResult, 
    HealFileResult, 
    HealStatus, 
    HealAction, 
    HealResult,
    PipelineStats,
    PipelineCapabilities,
    HealConfig
)

# --- Level 1: Core Geometry (No dependencies on engine) ---
from yamlr.core.identity import (
    APPS_V1,
    BATCH_V1,
    CLUSTER_SCOPED_KINDS,
    FORCED_ARRAY_FIELDS,
    K8S_CORE_KEYS,
    NETWORKING_V1,
    RBAC_V1,
    RESOURCE_CATALOG,
    SAFE_OBJECT_FIELDS,
    SPECIAL_PURPOSE_BLOCKS,
    STORAGE_V1,
    V1,
    WORKLOAD_KINDS,
    ManifestIdentity,
)

from yamlr.core.stages.boundaries import MutationScope

@dataclass(slots=True)
class Shard:
    """
    The Atomic Unit of Yamlr - The 'DNA Strand'.

    Why: Shards provide a side-effect-free representation of a YAML 
         line, including its indentation, comments, and structure. 
         This allows the Lexical Physicist and Healers to mutate 
         manifests while 100% preserving original formatting.
    """
    line_no: int
    indent: int
    key: str
    value: Optional[Union[str, int, float, bool, Dict[str, Any], List[Any]]] = None
    is_list_item: bool = False
    is_table_continuation: bool = False
    is_block: bool = False
    is_doc_boundary: bool = False
    comment: Optional[str] = None
    raw_line: str = ""
    original_indent: int = 0
    is_flow_style: bool = False
    layout_sequence: List[Union[str, Any]] = field(default_factory=list)
    trailing_layout_sequence: List[Union[str, Any]] = field(default_factory=list)
    intent_tag: Optional[str] = None

__all__ = [
    "Shard",
    "ManifestIdentity",
    "HealAction",
    "HealFileResult",
    "HealStatus",
    "AnalysisResult",
    "HealResult",
    "PipelineStats",
    "PipelineCapabilities",
    "HealConfig",
    "WORKLOAD_KINDS",
    "CLUSTER_SCOPED_KINDS",
    "RESOURCE_CATALOG",
    "K8S_CORE_KEYS",
    "MutationScope",
]
