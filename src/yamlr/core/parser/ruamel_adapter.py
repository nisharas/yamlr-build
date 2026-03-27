"""
Ruamel.yaml Adapter for YamlrParser
-----------------------------------
Implements the YamlrParser interface using ruamel.yaml.
Specifically tailored to support the 'Comment Preservation' pillar.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, IO
try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
except (ImportError, SystemError) as e:
    # [Hardening] If binary extensions are broken, we might need to fail gracefully 
    # or inform the user about the environment issue.
    # In a real scenario, we might try to force-import the pure-python version if possible.
    import logging
    logging.getLogger("yamlr.parser.ruamel").error(f"Failed to load ruamel.yaml: {e}")
    raise

from yamlr.core.parser.base import YamlrParser, YamlrNode

__all__ = ["RuamelNode", "RuamelAdapter"]


class RuamelNode(YamlrNode):
    """
    Adapter for ruamel.yaml CommentedMap and CommentedSeq objects.
    """
    
    def __init__(self, raw_node: Any):
        # [HARDENING] Prevent double-wrapping
        if isinstance(raw_node, RuamelNode):
            self._node = raw_node._node
        elif hasattr(raw_node, "_node"):
             self._node = raw_node._node
        else:
            self._node = raw_node

    @property
    def data(self) -> Any:
        """Exposes the underlying raw data node (Legacy compatibility)."""
        return self._node

    @property
    def is_map(self) -> bool:
        """Checks if the node is a mapping (dict-like)."""
        # [Hardening] typ='safe' results in standard dicts, typ='rt' in CommentedMap.
        # We must support both to prevent 'Unknown' metadata when loading rules.
        return isinstance(self._node, (dict, CommentedMap))

    @property
    def is_seq(self) -> bool:
        """Checks if the node is a sequence (list-like)."""
        return isinstance(self._node, (list, CommentedSeq))

    def get_comments(self) -> List[str]:
        """Extracts leading and trailing comments from the ruamel.yaml node."""
        if not hasattr(self._node, 'ca') or not self._node.ca:
            return []
            
        comments = []
        if hasattr(self._node.ca, 'comment') and self._node.ca.comment:
            for c in self._node.ca.comment:
                comments.extend(self._extract_comment_values(c))
                             
        return comments

    def _extract_comment_values(self, comment_item: Any) -> List[str]:
        """Helper to extract strings from ruamel comment items."""
        values = []
        if not comment_item:
            return values
            
        if hasattr(comment_item, 'value'):
            values.append(comment_item.value.strip())
        elif isinstance(comment_item, list):
            for sub_c in comment_item:
                if sub_c and hasattr(sub_c, 'value'):
                    values.append(sub_c.value.strip())
        return values

    def set_footer_comment(self, text: str):
        """Adds a trailing comment to the bottom of the document."""
        if not text or not text.strip():
            return
            
        # Ensure # prefix for all lines
        lines = []
        for line in text.splitlines():
            s_line = line.strip()
            if s_line and not s_line.startswith("#"):
                lines.append(f"# {line}")
            else:
                lines.append(line)
        joined = "\n".join(lines) + "\n"
        
        if hasattr(self._node, "ca"):
            if not self._node.ca.comment:
                self._node.ca.comment = [None, []]
            
            # Trailing comments are in the second element of the comment list
            # We can just append the raw string as ruamel often accepts it 
            # or try to build a token. 
            # For simplicity and robustness across ruamel versions:
            try:
                from ruamel.yaml.tokens import CommentToken
                # Ensure the text has a leading # if it doesn't already 
                # AND it's not a pure newline (Gap preservation)
                has_content = any(line.strip().startswith('#') for line in joined.splitlines())
                if not has_content:
                    # If it's just newlines, we must NOT prefix with #
                    pass
                elif not joined.strip().startswith('#'):
                    joined = '# ' + joined
                
                token = CommentToken(joined, None, None)
                self._node.ca.comment[1].append(token)
            except Exception:
                # If we can't create a Token, we shouldn't append a raw string 
                # as it causes AttributeErrors in Newer Ruamel versions.
                pass

    def set_start_comment(self, text: str, indent: int = 0):
        """Sets a leading comment for the node."""
        if not text:
            return
        from yamlr.comments import yaml_set_start_comment
        yaml_set_start_comment(self._node, text, indent=indent)

    def set_key_start_comment(self, key: Any, text: str, indent: int = 0):
        """Sets a leading comment for a specific key in a mapping."""
        if not text or not self.is_map:
            return
        from yamlr.comments import yaml_set_key_comment
        yaml_set_key_comment(self._node, key, text, indent=indent)

    def set_eol_comment(self, text: str, key: Any):
        """Sets an end-of-line comment for a specific key in a mapping."""
        if not text or not text.strip() or not self.is_map:
            return
        try:
            self._node.yaml_add_eol_comment(text, key=key)
        except (AttributeError, KeyError, ValueError):
            pass

    def set_footer_comment(self, text: str):
        """Sets a footer comment for the container."""
        if not text:
            return
        from yamlr.comments import yaml_set_footer_comment
        yaml_set_footer_comment(self._node, text)

    def graft_metadata(self, target: YamlrNode, key: Optional[Any] = None):
        """
        Implementation of AttributeGrafter.graft but decoupled.
        """
        if not isinstance(target, RuamelNode) or not hasattr(self._node, "ca") or not self._node.ca:
            return

        target_raw = target._node
        if not hasattr(target_raw, "ca"):
            return

        if key is not None:
            self._graft_key_metadata(target_raw, key)
        else:
            self._graft_node_metadata(target_raw)
        
        # Preserve formatting attributes
        for attr in ["_yaml_format", "_yaml_line_col"]:
            if hasattr(self._node, attr):
                setattr(target_raw, attr, getattr(self._node, attr))

    def _graft_key_metadata(self, target_raw: Any, key: Any):
        """Grafts metadata for a specific key in a mapping."""
        if hasattr(self._node.ca, "items") and key in self._node.ca.items:
            if not hasattr(target_raw.ca, "items"):
                target_raw.ca.items = {}
            target_raw.ca.items[key] = self._node.ca.items[key]

    def _graft_node_metadata(self, target_raw: Any):
        """Grafts node-level metadata (comments and sequence items)."""
        if hasattr(self._node.ca, "comment") and self._node.ca.comment:
            target_raw.ca.comment = self._node.ca.comment
        
        if hasattr(self._node.ca, "items"):
            if not hasattr(target_raw.ca, "items"):
                target_raw.ca.items = {}
            for k, v in self._node.ca.items.items():
                target_raw.ca.items[k] = v
        
        # Preserve formatting attributes
        for attr in ['_yaml_format', '_yaml_line_col']:
            if hasattr(source_raw, attr):
                setattr(target_raw, attr, getattr(source_raw, attr))

    def create_empty(self) -> YamlrNode:
        """Creates a new empty node of the same type, preserving formatting/style."""
        new_raw = None
        if self.is_map:
            new_raw = CommentedMap()
        elif self.is_seq:
            new_raw = CommentedSeq()
        else:
            # Scalar - just return the value or a new scalar?
            # For sorter, we mostly care about maps and seqs
            return RuamelNode(self._node)

        # Preserve formatting
        for attr in ['_yaml_format', '_yaml_line_col']:
            if hasattr(self._node, attr):
                setattr(new_raw, attr, getattr(self._node, attr))
        
        return RuamelNode(new_raw)

    def to_dict(self) -> Union[Dict, List, Any]:
        """Deep conversion of ruamel types to primitives."""
        # [HARDENING] If we're already a YamlrNode, unwrap our inner node
        node = self._node
        if hasattr(node, "to_dict") and node is not self:
             return node.to_dict()

        if self.is_map:
            return {str(k): RuamelNode(v).to_dict() for k, v in node.items()}
        elif self.is_seq:
            return [RuamelNode(v).to_dict() for v in node]
        return node

    def __getitem__(self, key: Any) -> Any:
        val = self._node[key]
        # Auto-wrap children if they are containers
        if isinstance(val, (CommentedMap, CommentedSeq, list, dict)) and not isinstance(val, (str, bytes)):
             return RuamelNode(val)
        return val

    def __setitem__(self, key: Any, value: Any):
        # Unwrap if we are setting a YamlrNode
        raw_val = value._node if isinstance(value, RuamelNode) else value
        self._node[key] = raw_val

    def __delitem__(self, key: Any):
        del self._node[key]

    def pop(self, key: Any, default: Any = None) -> Any:
        """Removes and returns an item from the node."""
        if not self.is_map:
            raise TypeError("pop() only supported on mappings")
        return self._node.pop(key, default)

    def keys(self) -> List[Any]:
        if not self.is_map:
            return []
        return list(self._node.keys())

    def items(self) -> List[Tuple[Any, Any]]:
        return [(k, self[k]) for k in self.keys()]

    def append(self, value: Any):
        raw_val = value._node if isinstance(value, RuamelNode) else value
        self._node.append(raw_val)

    def __len__(self) -> int:
        return len(self._node)

    def move_to_end(self, key: Any, last: bool = True):
        """Delegates to internal CommentedMap move_to_end for reordering."""
        if hasattr(self._node, "move_to_end"):
            self._node.move_to_end(key, last=last)

    def __contains__(self, key: Any) -> bool:
        """Standard check for membership."""
        if self._node is None: return False
        return key in self._node

    def get(self, key: Any, default: Any = None) -> Any:
        """Dict-like get method for the node."""
        if not self.is_map:
            return default
        try:
            return self[key]
        except (KeyError, IndexError, TypeError):
            return default

    def __iter__(self):
        """Allows iteration over sequence items or mapping keys."""
        if self.is_seq:
            for i in range(len(self)):
                yield self[i]
        elif self.is_map:
            yield from self._node.keys()

    def __str__(self) -> str:
        return str(self._node)

    def __repr__(self) -> str:
        return f"RuamelNode({repr(self._node)})"


class RuamelAdapter(YamlrParser):
    """
    Adapter bridging YamlrParser to ruamel.yaml.
    """

    def __init__(self, typ: str = "rt", pure: bool = True, indent: int = 2, offset: int = 0, compact: bool = False):
        self.yaml = YAML(typ=typ, pure=pure)
        self.yaml.preserve_quotes = True
        self.compact = compact
        
        # [HEAL-6] Configure parser for standard K8s indents
        self.yaml.indent(mapping=indent, sequence=indent, offset=offset)
        
        self.yaml.width = 4096

    def set_indent(self, mapping: int = 2, sequence: int = 2, offset: int = 0):
        """Standardized indentation configuration."""
        self.yaml.indent(mapping=mapping, sequence=sequence, offset=offset)


    def load(self, stream: Union[str, IO[Any]]) -> YamlrNode:
        """
        Safely loads a YAML stream with deep protection against Billion Laughs.
        """
        # [Security] Pre-scan for Billion Laughs (VULN-001)
        # Why: ruamel.yaml RT mode has inconsistent max_aliases support across versions.
        #      Manual counting is robust, version-independent, and occurs BEFORE parsing.
        content = ""
        if isinstance(stream, str):
            content = stream
        else:
            try:
                content = stream.read()
                if hasattr(stream, "seek"):
                    stream.seek(0)
            except Exception:
                pass # Fallback to standard load if stream is not readable here

        if content:
            import re
            # Count anchors (&) and aliases (*) while ignoring those in comments or quotes where possible
            # We use a conservative threshold of 50.
            anchors = len(re.findall(r'(?m)(?:^\s*&)|(?:(?<=\s)&(?=\w))', content))
            aliases = len(re.findall(r'\*\w+', content))
            
            if anchors > 50 or aliases > 50:
                 from yamlr.core.exceptions import YamlrSecurityError
                 raise YamlrSecurityError(f"YAML Bomb Detected: Too many aliases ({aliases}) or anchors ({anchors})")

        data = self.yaml.load(stream)
        return RuamelNode(data)

    def load_all(self, stream: Union[str, IO[Any]]) -> List[YamlrNode]:
        docs = list(self.yaml.load_all(stream))
        return [RuamelNode(d) for d in docs]

    def dump(self, node: Union[YamlrNode, Any], stream: Optional[IO[Any]] = None) -> Optional[str]:
        raw_data = node._node if isinstance(node, RuamelNode) else node
        
        if stream is None:
            import io
            buf = io.StringIO()
            self.yaml.dump(raw_data, buf)
            return buf.getvalue()
        
        self.yaml.dump(raw_data, stream)
        return None

    def dump_all(self, nodes: List[YamlrNode], stream: Optional[IO[Any]] = None) -> Optional[str]:
        """Serializes multiple YamlrNodes to a single multi-document YAML stream."""
        raw_docs = [n._node if isinstance(n, RuamelNode) else n for n in nodes]
        
        if stream is None:
            import io
            buf = io.StringIO()
            self.yaml.dump_all(raw_docs, buf)
            return buf.getvalue()
        
        self.yaml.dump_all(raw_docs, stream)
        return None

    def create_node(self, typ: Optional[str] = None, data: Any = None) -> YamlrNode:
        """Creates a new node, optionally from data or of a specific type ('map', 'seq')."""
        if data is not None:
            if isinstance(data, RuamelNode):
                return data
            if isinstance(data, (CommentedMap, CommentedSeq)):
                return RuamelNode(data)
            if isinstance(data, dict):
                return RuamelNode(CommentedMap(data))
            if isinstance(data, list):
                return RuamelNode(CommentedSeq(data))
            return RuamelNode(data)
            
        if typ == "map":
            return RuamelNode(CommentedMap())
        if typ == "seq":
            return RuamelNode(CommentedSeq())
            
        return RuamelNode(None)
