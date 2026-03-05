#!/usr/bin/env python3
"""
Yamlr SEMANTIC LEXER (Foundation for Yamlr)
----------------------------------------------
The core sharding engine for yamlr. This module decomposes raw YAML text into
semantic Shard models. Healing logic is delegated to LexicalHealer.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-15 (Refactored)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from yamlr.models import Shard
from yamlr.parsers.healer import LexicalHealer

logger = logging.getLogger("yamlr.lexer")

class YamlrLexer:
    """
    Orchestrates the transition from raw text to semantic Shards.
    Now focuses strictly on Lexing and Semantic Extraction.
    """

    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.in_block: bool = False
        self.block_indent: int = 0
        self.healer = LexicalHealer()

    @property
    def repair_stats(self) -> Dict[str, int]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.healer.stats

    def _clean_artifacts(self, text: str) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        text = text.lstrip("\ufeff")
        return text.replace("\r\n", "\n")

    def _find_comment_split(self, text: str) -> int:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
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
            if char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote

            if char == "#":
                is_quoted = in_double_quote or in_single_quote
                is_boundary = i == 0 or text[i - 1].isspace()
                if not is_quoted and is_boundary:
                    return i
                if is_quoted and is_boundary and potential_comment_idx == -1:
                    potential_comment_idx = i

        if (in_double_quote or in_single_quote) and potential_comment_idx != -1:
            return potential_comment_idx
        return -1

    def _extract_semantics(self, code_part: str) -> Tuple[str, Optional[Any], bool, bool]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        clean = code_part.strip()
        if not clean or clean.startswith("---"):
            return "", None, False, False

        if clean.startswith(("&", "*", "!")):
            split_match = re.search(r'[\s"\'\[\{]', clean[1:])
            split_pos = split_match.start() + 1 if split_match else len(clean)
            modifier = clean[:split_pos]
            remaining = clean[split_pos:].lstrip()
            _, val, is_l, is_f = self._extract_semantics(remaining)
            return "", f"{modifier} {val or ''}".strip(), is_l, is_f

        is_list = clean.startswith("-") and not clean.startswith("---")
        if is_list:
            clean = clean[1:].lstrip()
            if not clean:
                return "", "", True, False

        if ":" in clean:
            if clean[0] in ('"', "'"):
                quote = clean[0]
                end_idx = clean.find(quote, 1)
                if end_idx != -1 and clean[end_idx + 1 :].lstrip().startswith(":"):
                    key = clean[1:end_idx]
                    val = clean[end_idx + 1 :].lstrip()[1:].strip()
                    # Detect flow-style
                    is_flow = False
                    if val and len(val) >= 2:
                        if (val[0] == "{" and val[-1] == "}") or (val[0] == "[" and val[-1] == "]"):
                            is_flow = True
                    return key, val or None, is_list, is_flow

            key_part, _, val_part = clean.partition(":")
            val = val_part.strip()
            if val.lower() in {"yes", "no", "y", "n", "on", "off"}:
                val = f'"{val}"'
                self.healer.stats["quote_repairs"] += 1
            
            # Detect flow-style (simple heuristic)
            is_flow = False
            if val and len(val) >= 2:
                if (val[0] == "{" and val[-1] == "}") or (val[0] == "[" and val[-1] == "]"):
                    is_flow = True
            
            key = key_part.strip().strip("\"'")
            val = val_part.strip()
            final_val = val if val else None
            # logger.debug(f"Lexer extracted: '{key}' : '{final_val}' from '{clean}'")
            return key, final_val, is_list, is_flow
        return "", clean, is_list, False

    def shard(self, raw_yaml: str, enable_phase2: bool = True) -> List[Shard]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.healer.reset_state()
        self.in_block = False
        self.block_indent = 0
        
        lines = self._clean_artifacts(raw_yaml).splitlines()
        shards: List[Shard] = []

        for i, original_line in enumerate(lines):
            working_line = self.healer.fix_flush_left_lists(shards, original_line)
            working_line = self.healer.heal_double_dash(working_line)
            working_line = self.healer.heal_fused_keywords(working_line)
            
            next_line = lines[i+1] if i+1 < len(lines) else None
            working_line = self.healer.heal_missing_colon(working_line, next_line)

            # Heuristic pipeline repair
            repaired_line = self.healer.repair_line(working_line, self.in_block)
            
            # Recalculate indent and split comment
            temp_line = repaired_line.replace("\t", "  ")
            content = temp_line.lstrip()
            indent = len(temp_line) - len(content)
            
            split_idx = self._find_comment_split(repaired_line)
            if split_idx != -1:
                code_part = repaired_line[:split_idx].strip()
                comment_part = repaired_line[split_idx:].lstrip("# ").rstrip()
            else:
                code_part = repaired_line.strip()
                comment_part = ""

            # Document boundary
            is_doc = code_part == "---"
            if is_doc:
                self.in_block = False
                self.block_indent = 0
            
            # Block state management (Lexer's responsibility to know if we are in block)
            if re.search(r"[|>][+\-]?\d?$", code_part):
                self.in_block = True
                self.block_indent = indent + 1
            elif indent < self.block_indent and content != "" and not is_doc:
                self.in_block = False

            if code_part.strip() or self.in_block or is_doc:
                if self.in_block and not is_doc:
                    key, value, is_list, is_flow = ("", code_part, False, False)
                else:
                    key, value, is_list, is_flow = self._extract_semantics(code_part)
                
                shards.append(Shard(
                    line_no=i+1, indent=indent, key=key, value=value,
                    is_list_item=is_list, is_block=self.in_block, is_doc_boundary=is_doc,
                    comment=comment_part, raw_line=repaired_line, is_flow_style=is_flow
                ))

        if enable_phase2:
            shards = self.healer.normalize_indentation(shards)
        
        return shards

    def get_repair_audit_log(self) -> List[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        log = []
        s = self.healer.stats
        if s["flush_left_lists_fixed"] > 0: log.append(f"Lexer: Fixed {s['flush_left_lists_fixed']} flush-left lists")
        if s["nested_lists_normalized"] > 0: log.append(f"Lexer: Normalized {s['nested_lists_normalized']} nested lists")
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

KubeLexer = YamlrLexer
