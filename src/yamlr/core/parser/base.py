"""
Yamlr Parser Abstraction
------------------------
Defines the stable interface for YAML parsing and node manipulation,
decoupling the engine from specific library implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import IO, Any, Dict, List, Optional, Union

__all__ = ["YamlrNode", "YamlrParser"]


class YamlrNode(ABC):
    """
    Abstract interface for a YAML document node (Map, Sequence, or Scalar).
    """

    @property
    @abstractmethod
    def is_map(self) -> bool:
        """Returns True if the node is a mapping (dict-like)."""
        pass

    @property
    @abstractmethod
    def is_seq(self) -> bool:
        """Returns True if the node is a sequence (list-like)."""
        pass

    @abstractmethod
    def set_start_comment(self, text: str, indent: int = 0):
        """Sets a leading comment for the node."""
        pass

    @abstractmethod
    def set_eol_comment(self, text: str, key: Any):
        """Sets an end-of-line comment for a specific key in a mapping."""
        pass

    @abstractmethod
    def get_comments(self) -> List[str]:
        """Returns comments associated with this node."""
        pass

    @abstractmethod
    def graft_metadata(self, target: YamlrNode, key: Optional[Any] = None):
        """
        Grafts metadata (comments, layout) from this node to a target node.
        If key is provided, only grafts metadata for that specific key.
        """
        pass

    @abstractmethod
    def create_empty(self) -> YamlrNode:
        """Creates a new empty node of the same type, preserving formatting/style."""
        pass

    @abstractmethod
    def to_dict(self) -> Union[Dict, List, Any]:
        """Converts the node (and its children) to standard Python primitives."""
        pass

    @abstractmethod
    def __getitem__(self, key: Any) -> Any: ...
    @abstractmethod
    def __setitem__(self, key: Any, value: Any): ...
    @abstractmethod
    def __delitem__(self, key: Any): ...
    @abstractmethod
    def keys(self) -> List[Any]: ...
    @abstractmethod
    def items(self) -> List[Tuple[Any, Any]]: ...
    @abstractmethod
    def append(self, value: Any): ...
    @abstractmethod
    def __len__(self) -> int: ...
    @abstractmethod
    def move_to_end(self, key: Any, last: bool = True): ...
    @abstractmethod
    def set_footer_comment(self, text: str): ...


class YamlrParser(ABC):
    """
    Interface for YAML loading and dumping.
    """

    @abstractmethod
    def load(self, stream: Union[str, IO[Any]]) -> YamlrNode:
        """Parses YAML content into a YamlrNode."""
        pass

    @abstractmethod
    def load_all(self, stream: Union[str, IO[Any]]) -> List[YamlrNode]:
        """Parses multi-document YAML content into a list of YamlrNodes."""
        pass

    @abstractmethod
    def dump(self, node: YamlrNode, stream: Optional[IO[Any]] = None) -> Optional[str]:
        """Serializes a YamlrNode back to YAML."""
        pass

    @abstractmethod
    def dump_all(self, nodes: List[YamlrNode], stream: Optional[IO[Any]] = None) -> Optional[str]:
        """Serializes multiple YamlrNodes to a single multi-document YAML stream."""
        pass

    @abstractmethod
    def create_node(self, typ: Optional[str] = None, data: Any = None) -> YamlrNode:
        """Creates a new node, optionally from data or of a specific type ('map', 'seq')."""
        pass
