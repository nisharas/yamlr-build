#!/usr/bin/env python3
"""
Yamlr SEMANTIC LEXER (Foundation for Yamlr)
----------------------------------------------
The core sharding engine for yamlr. This module decomposes raw YAML text into
semantic Shard models. Healing logic is delegated to LexicalHealer.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-15 (Refactored)
"""

from __future__ import annotations
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from yamlr.models import Shard
from yamlr.parsers.healer import LexicalHealer
from yamlr.parsers.heuristics.table_continuation import TableContinuationHeuristic

logger = logging.getLogger("yamlr.lexer")
__all__ = ['YamlrLexer']


class YamlrLexer:
    """
    Orchestrates the transition from raw text to semantic Shards.
    Now focuses strictly on Lexing and Semantic Extraction.
    """

    # Security Gates (Round 9)
    MAX_LEX_SIZE = 100 * 1024 * 1024  # 100MiB
    MAX_ANCHOR_DEPTH = 50             # Prevent Billion Laughs
    MAX_ALIAS_COUNT = 1000            # Prevent recursive expansion attacks

    def __init__(self):
        """Initializes the semantic lexer.
        
        Why: To prepare the engine for transforming raw manifest text into a stream of shards.
        """
        self.in_block: bool = False
        self.block_indent: int = 0
        self.healer = LexicalHealer()
        self._anchor_stack_depth = 0
        self._total_aliases = 0

    @property
    def repair_stats(self) -> Dict[str, int]:
        """Returns the cumulative statistics of all lexical repairs performed.
        
        Why: To provide transparency into what 'magic' the lexer performed during sharding.
        """
        return self.healer.stats

    def _clean_artifacts(self, text: str) -> str:
        """Removes common encoding artifacts like Byte Order Marks (BOM) and normalizes line endings.
        
        Why: To ensure that the lexer operates on a clean, deterministic stream of text.
        """
        text = text.lstrip("\ufeff")
        return text.replace("\r\n", "\n")

    def _find_comment_split(self, text: str) -> int:
        """Locates the starting index of a YAML comment, respecting quote boundaries."""
        in_double_quote = False
        in_single_quote = False
        escaped = False
        potential_comment_idx = -1

        for i, char in enumerate(text):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            
            in_double_quote, in_single_quote = self._update_quote_state(char, in_double_quote, in_single_quote)

            if char == "#":
                res = self._check_comment_boundary(text, i, in_double_quote, in_single_quote, potential_comment_idx)
                if res >= 0: return res
                if res == -2: potential_comment_idx = i # Signifies potential match in quotes

        return potential_comment_idx if (in_double_quote or in_single_quote) else -1

    def _update_quote_state(self, char: str, in_double: bool, in_single: bool) -> Tuple[bool, bool]:
        """Helper to track state within strings."""
        if char == '"' and not in_single:
            return not in_double, in_single
        if char == "'" and not in_double:
            return in_double, not in_single
        return in_double, in_single

    def _check_comment_boundary(self, text: str, i: int, in_double: bool, in_single: bool, potential_idx: int) -> int:
        """Checks if a hashtag is a valid comment start or a quoted literal."""
        is_quoted = in_double or in_single
        is_boundary = i == 0 or text[i - 1].isspace()
        
        if not is_quoted and is_boundary:
            return i
        if is_quoted and is_boundary and potential_idx == -1:
            return -2 # Signal potential comment
        return -1

    def _extract_semantics(self, code_part: str) -> Tuple[str, Optional[Any], bool, bool]:
        """Extracts the key, value, and structural markers from a line of YAML code.
        
        Why: To decompose a line into its fundamental building blocks (Key-Value pairs or List items).
        """
        clean = code_part.strip()
        if not clean or clean.startswith("---"):
            return "", None, False, False

        # Guard Round 9: Security Scan for malicious modifiers
        if clean.startswith(("&", "*", "!")):
            return self._handle_modifiers(clean)

        is_list = clean.startswith("-") and not clean.startswith("---")
        if is_list:
            clean = clean[1:].lstrip()
            if not clean: return "", "", True, False

        if ":" in clean:
            return self._parse_key_value(clean, is_list)

        return "", clean, is_list, False

    def _handle_modifiers(self, clean: str) -> Tuple[str, Optional[Any], bool, bool]:
        """Handles YAML anchors, aliases, and tags with security depth checks."""
        split_match = re.search(r'[\s"\'\[\{]', clean[1:])
        split_pos = split_match.start() + 1 if split_match else len(clean)
        modifier = clean[:split_pos]
        
        # Security Guard: Anchor/Alias Depth
        if modifier.startswith("*"):
            self._total_aliases += 1
            if self._total_aliases > self.MAX_ALIAS_COUNT:
                from yamlr.core.exceptions import YamlrSecurityError
                raise YamlrSecurityError("YAML Security: Maximum alias count exceeded.")

        self._anchor_stack_depth += 1
        if self._anchor_stack_depth > self.MAX_ANCHOR_DEPTH:
            from yamlr.core.exceptions import YamlrSecurityError
            raise YamlrSecurityError("YAML Security: Maximum anchor/tag nesting depth exceeded.")

        try:
            remaining = clean[split_pos:].lstrip()
            _, val, is_l, is_f = self._extract_semantics(remaining)
        finally:
            self._anchor_stack_depth -= 1

        return "", f"{modifier} {val or ''}".strip(), is_l, is_f

    def _parse_key_value(self, clean: str, is_list: bool) -> Tuple[str, Optional[Any], bool, bool]:
        """Surgically extracts key and value from a colon-separated line."""
        if clean[0] in ('"', "'"):
            res = self._parse_quoted_key(clean, is_list)
            if res: return res

        key_part, _, val_part = clean.partition(":")
        val = val_part.strip()
        
        # Round 9 Security: Propagate scan to nested anchors/aliases
        if val.startswith(("&", "*", "!")):
            _, val, _, is_f = self._handle_modifiers(val)
            return key_part, val, is_list, is_f
            
        return key_part, val or None, is_list, self._is_flow(val)

    def _parse_quoted_key(self, clean: str, is_list: bool) -> Optional[Tuple[str, Optional[Any], bool, bool]]:
        """Handles keys wrapped in quotes."""
        quote = clean[0]
        end_idx = clean.find(quote, 1)
        if end_idx != -1 and clean[end_idx + 1 :].lstrip().startswith(":"):
            key = clean[1:end_idx]
            val = clean[end_idx+1:].lstrip()[1:].strip()
            return key, val or None, is_list, self._is_flow(val)
        return None

    def _is_flow(self, val: str) -> bool:
        """Simple heuristic for flow-style detection."""
        if val and len(val) >= 2:
            return (val[0] == "{" and val[-1] == "}") or (val[0] == "[" and val[-1] == "]")
        return False

    def shard(self, raw_yaml: str, enable_phase2: bool = True) -> List[Shard]:
        """
        Why: Orchestrates high-performance sharding via native extension.
        """
        self._security_pre_scan(raw_yaml)
        
        import os
        if os.getenv("YAMLR_DISABLE_NATIVE") == "1":
            return self._shard_python(raw_yaml, enable_phase2)

        try:
            # Standardize on both possible module names
            try:
                from yamlr_native import native_shard
            except ImportError:
                from yamlr.native import native_shard
                
            # [Hardening] native_shard (Rust) may throw SystemError if binary is corrupted
            native_shards = native_shard(raw_yaml)
            
            shards = []
            for ns in native_shards:
                with open("d:\\yamlr\\lex_debug.log", "a") as f:
                     f.write(f"DEBUG: Lexer Shard L{ns.line_no} key={ns.key} indent={ns.indent}\n")
                shards.append(Shard(
                    line_no=ns.line_no,
                    indent=ns.indent,
                    key=ns.key,
                    value=ns.value,
                    is_list_item=ns.is_list_item,
                    is_block=ns.is_block,
                    is_doc_boundary=ns.is_doc_boundary,
                    comment=ns.comment,
                    raw_line="", # Native layer removed raw_line for memory efficiency
                    is_flow_style=ns.is_flow_style
                ))
            
            if enable_phase2:
                shards = self.healer.normalize_indentation(shards)
            return shards
            
        except (ImportError, SystemError, Exception):
            # Fallback to pure Python implementation
            return self._shard_python(raw_yaml, enable_phase2)

    def _security_pre_scan(self, raw_yaml: str):
        """
        [Round 13] High-performance pre-scan to enforce limits before native offloading.
        Why: Protects the Rust layer from Billion Laughs and Alias Explosion.
        """
        # 1. Size Guard (already verified in shard, but centralized here)
        if len(raw_yaml) > self.MAX_LEX_SIZE:
             from yamlr.core.exceptions import YamlrSecurityError
             raise YamlrSecurityError(f"Input exceeds maximum lexing size ({self.MAX_LEX_SIZE // (1024*1024)}MB).")

        # 2. Alias Explosion (Count '*' markers)
        # Using a simple count is a conservative but safe upper bound.
        alias_count = raw_yaml.count("*")
        if alias_count > self.MAX_ALIAS_COUNT:
            from yamlr.core.exceptions import YamlrSecurityError
            raise YamlrSecurityError(f"YAML Security: Maximum alias count exceeded ({alias_count}).")

        # 3. Anchor Depth / Malicious Nesting
        # Detect many modifiers in a single line (proxy for recursion)
        for line in raw_yaml.splitlines():
            modifier_count = line.count("!!") + line.count("&") + line.count("*")
            if modifier_count > self.MAX_ANCHOR_DEPTH:
                from yamlr.core.exceptions import YamlrSecurityError
                raise YamlrSecurityError("YAML Security: Maximum anchor/tag nesting depth exceeded on single line.")

    def _shard_python(self, raw_yaml: str, enable_phase2: bool = True) -> List[Shard]:
        """Pure Python implementation of the sharding logic."""
        self.healer.reset_state()
        self.in_block = False
        self.block_indent = 0
        self._total_aliases = 0
        self._anchor_stack_depth = 0
        
        lines = self._clean_artifacts(raw_yaml).splitlines()
        shards: List[Shard] = []

        for i, original_line in enumerate(lines):
            self._process_single_line(original_line, i, lines, shards)
            if shards:
                s = shards[-1]
                with open("d:\\yamlr\\shard_debug.log", "a") as f:
                    f.write(f"SHARD: L{s.line_no} I{s.indent} K={s.key} V={s.value}\n")

        if enable_phase2:
            shards = self.healer.normalize_indentation(shards)
        
        return shards

    def _process_single_line(self, original_line: str, i: int, lines: List[str], shards: List[Shard]):
        """Processes a single line of YAML and emits a Shard."""
        next_line = lines[i+1] if i+1 < len(lines) else None
        repaired_line, intent_tags = self.healer.repair_line(original_line, self.in_block, shards=shards, next_line=next_line)
        
        temp_line = repaired_line.replace("\t", "  ")
        content = temp_line.lstrip()
        indent = len(temp_line) - len(content)
        
        split_idx = self._find_comment_split(repaired_line)
        code_part, comment_part = self._split_code_and_comment(repaired_line, split_idx)

        is_doc = code_part == "---"
        if is_doc:
            self.in_block, self.block_indent = False, 0
        
        self._update_block_state(code_part, indent, is_doc)

        if code_part.strip() or self.in_block or is_doc:
            shard = self._create_shard(i+1, indent, code_part, comment_part, repaired_line, is_doc, intent_tags, shards)
            shards.append(shard)

    def _split_code_and_comment(self, line: str, split_idx: int) -> Tuple[str, str]:
        """Helper to separate comment and code."""
        if split_idx != -1:
            return line[:split_idx].strip(), line[split_idx:].lstrip("# ").rstrip()
        return line.strip(), ""

    def _update_block_state(self, code_part: str, indent: int, is_doc: bool):
        """Standard YAML block scalar detection."""
        if re.search(r"[|>][+\-]?\d?$", code_part):
            self.in_block = True
            self.block_indent = indent + 1
        elif indent < self.block_indent and code_part != "" and not is_doc:
            self.in_block = False

    def _create_shard(self, line_no: int, indent: int, code: str, comment: str, raw: str, is_doc: bool, tags: List[str], shards: List[Shard]) -> Shard:
        """Emits a single semantic shard with all heuristics applied."""
        if self.in_block and not is_doc:
            key, value, is_list, is_flow = ("", code, False, False)
        else:
            key, value, is_list, is_flow = self._extract_semantics(code)
            
        is_table = TableContinuationHeuristic.is_continuation(shards, indent, is_list, is_doc)

        return Shard(
            line_no=line_no, indent=indent, key=key, value=value,
            is_list_item=is_list, is_table_continuation=is_table,
            is_block=self.in_block, is_doc_boundary=is_doc,
            comment=comment, raw_line=raw, is_flow_style=is_flow,
            intent_tag=",".join(tags) if tags else None
        )

    def get_repair_audit_log(self) -> List[str]:
        """Generates a human-readable log of all structural repairs made during lexing.
        
        Why: To populate the 'Advisory' section of the report with lexical findings.
        """
        log = []
        s = self.healer.stats
        if s["flush_left_lists_fixed"] > 0: log.append(f"Lexer: Fixed {s['flush_left_lists_fixed']} flush-left lists")
        if s["nested_lists_normalized"] > 0: log.append(f"Lexer: Normalized {s['nested_lists_normalized']} nested lists")
        if s.get("floating_list_items_fixed", 0) > 0: log.append(f"Lexer: Fixed {s['floating_list_items_fixed']} floating-left list items")
        if s["quote_repairs"] > 0: log.append(f"Lexer: Repaired {s['quote_repairs']} quotes")
        if s["spacing_fixes"] > 0: log.append(f"Lexer: Fixed {s['spacing_fixes']} spacing issues")
        if s["double_dash_normalized"] > 0: log.append(f"Lexer: Normalized {s['double_dash_normalized']} double-dashed items")
        return log

    def prepare_for_scanner(self, shards: List[Shard]) -> Dict[str, Any]:
        """Prepares metadata for Scanner."""
        return {
            "indent_context": [],  # Minimal for now
            "repair_stats": self.repair_stats.copy(),
            "structure_hints": {
                "has_lists": any(s.is_list_item for s in shards),
                "max_nesting_depth": max((s.indent // 2 for s in shards), default=0),
                "document_count": sum(1 for s in shards if s.is_doc_boundary) + 1,
                "has_block_scalars": any(s.is_block for s in shards),
            }
        }


