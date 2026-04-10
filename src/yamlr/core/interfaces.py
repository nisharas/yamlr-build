"""
Yamlr CORE INTERFACES
--------------------
Defines strict protocols (shapes) for the fundamental data objects.
Why: To prevent circular dependencies between 'models' and 'core'.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-03-10
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

__all__ = ["ShardInterface", "HealActionInterface", "ManifestIdentityInterface"]


@runtime_checkable
class ShardInterface(Protocol):
    line_no: int
    indent: int
    key: str
    value: Optional[Any]
    is_list_item: bool
    is_table_continuation: bool
    is_block: bool
    is_doc_boundary: bool
    comment: Optional[str]
    raw_line: str
    original_indent: int
    is_flow_style: bool
    layout_sequence: List[Any]
    intent_tag: Optional[str]


@runtime_checkable
class HealActionInterface(Protocol):
    stage: str
    action_type: str
    target: str
    description: str
    severity: str

    def to_dict(self) -> Dict[str, Any]: ...


@runtime_checkable
class ManifestIdentityInterface(Protocol):
    api_version: Optional[str]
    kind: Optional[str]
    name: Optional[str]
    namespace: Optional[str]
    doc_index: int
    was_repaired: bool
    file_path: Optional[str]

    def is_deprecated(self) -> bool: ...

    def is_complete(self) -> bool: ...

    def to_dict(self) -> Dict[str, Any]: ...
