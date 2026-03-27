#!/usr/bin/env python3
"""
Yamlr STRUCTURER - The Reconciled Architect
-------------------------------------------
Rebuilds the YAML tree from identified shards.
Decomposed and Hardened: v1.1 Refactor.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from yamlr.core.parser.base import YamlrParser, YamlrNode
from yamlr.models import Shard
from yamlr.parsers.physicist import IndentationPhysicist
from yamlr.parsers.schema_healer import SchemaHealer

if TYPE_CHECKING:
    from yamlr.core.context import HealContext
    from yamlr.validators.schema_validator import SchemaValidator


logger = logging.getLogger("yamlr.parsers.structurer")
__all__ = ['YamlrStructurer']


class YamlrStructurer:
    """The Architect: Orchestrates YAML tree reconstruction.
    
    Why: To provide a structured, schema-aware representation of Kubernetes manifests.
    """

    def __init__(self, catalog: Dict[str, Any], validator: Optional["SchemaValidator"] = None):
        """Initializes the structurer with a schema catalog and validator.
        
        Why: To enable intelligent reconstruction of YAML trees using Kubernetes API awareness.
        """
        self.catalog = catalog
        self.validator = validator
        self._had_leading_boundary = False # [Phase 8] Pro Preservation 

        from yamlr.core.utils import get_hardened_yaml
        self.parser: YamlrParser = get_hardened_yaml(typ="rt", pure=False) # Roundtrip for structure preservation
        
        # Decomposed Components
        self.physicist = IndentationPhysicist()
        self.healer = SchemaHealer(catalog, validator)
        
        # [MODULARITY FIX] Allow injection of custom secret paths
        self.preserve_quote_paths = {
            "data", "stringData", "binaryData", 
            "encryptedData", # SealedSecrets
            "auth", "secret", "token", # Generic sensitive fields
            "password", "key"
        }

    def reconstruct(self, context: "HealContext") -> List[YamlrNode]:
        """[Stage 6] Rebuilds the folder-like structure from flat data shards."""
        if not context.shards:
            return []

        if context.shards[0].is_doc_boundary:
            self._had_leading_boundary = True

        try:
            self._setup_physics(context)
            all_documents = self._split_shards_into_docs(context)
            self._audit_duplicate_keys(context)
            return all_documents
        except Exception as e:
            logger.error(f"Stage 6: Critical reconstruction failure: {e}")
            raise

    def _setup_physics(self, context: "HealContext"):
        """Initializes indentation physics for the current shards."""
        context.shadow_engine.physicist = self.physicist
        self.physicist.calculate_majority_indent()
        logger.debug(f"Physics Resolved: Majority Indent = {self.physicist.majority_indent}")
        m_indent = max(2, self.physicist.majority_indent)
        self.parser.set_indent(mapping=m_indent, sequence=m_indent, offset=0)

    def _split_shards_into_docs(self, context: "HealContext") -> List[YamlrNode]:
        """Iterates shards and groups them into individual documents."""
        all_documents: List[YamlrNode] = []
        current_shards: List[Shard] = []
        doc_count = 0

        for shard in context.shards:
            if shard.is_doc_boundary:
                if current_shards:
                    doc = self._process_doc(current_shards, doc_count, context)
                    if doc: all_documents.append(doc)
                    current_shards = []
                    doc_count += 1
            else:
                current_shards.append(shard)

        if current_shards:
            with open("d:\\yamlr\\struct_debug.log", "a") as f:
                for s in current_shards:
                    f.write(f"STRUCT_SHARD: L{s.line_no} I{s.indent} K={s.key}\n")
            doc = self._process_doc(current_shards, doc_count, context)
            if doc: all_documents.append(doc)
            
        return all_documents

    def _audit_duplicate_keys(self, context: "HealContext"):
        """Processes tracked duplicate keys into findings."""
        if not hasattr(self, "duplicate_keys") or not self.duplicate_keys:
            return
            
        from yamlr.analyzers.base import AnalysisResult
        ident = context.identities[0] if context.identities else None
        kbs_kind = ident.kind if ident else "Unknown"
        kbs_name = ident.name if ident else "unknown"
        
        for d_key, d_shard in self.duplicate_keys:
            context.findings.append(AnalysisResult(
                analyzer_name="StructurerDuplicateKey",
                severity="WARNING",
                message=f"Duplicate key '{d_key}' detected at line {d_shard.line_no}. The latter value overwritten the former.",
                resource_name=kbs_name,
                resource_kind=kbs_kind,
                file_path="unknown",
                rule_id="yaml/duplicate-key",
                line_number=d_shard.line_no
            ))

    def _detect_indent(self, shards: List[Shard]) -> int:
        """Calculates the dominant indentation step for a set of shards."""
        indents = [s.indent for s in shards if s.indent > 0]
        if not indents: return 2
        diffs = [indents[i] - indents[i-1] for i in range(1, len(indents)) if indents[i] > indents[i-1]]
        if not diffs: 
            # If no diffs, use the smallest indent found (likely the first level)
            return min(indents) if indents else 2
        return max(set(diffs), key=diffs.count)

    def _process_doc(self, shards: List[Shard], index: int, context: "HealContext") -> Optional[YamlrNode]:
        """Processes a single document group of shards."""
        identity = context.identities[index] if index < len(context.identities) else None
        kind = identity.kind if identity else None
        api = identity.api_version if identity else None
        
        try:
            doc = self._build_tree(shards, kind, api)
            doc.indent_step = self._detect_indent(shards)
            return doc
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            import traceback
            logger.error(f"Stage 6: Failed document {index} (kind: {kind}): {e}")
            logger.error(traceback.format_exc())
            return None


    def serialize(self, documents: List[YamlrNode], compact: bool = False, custom_priority: Optional[Dict[str, int]] = None) -> str:
        """[Stage 9] Turns the internal tree back into a text file (YAML)."""
        self._apply_sorting(documents, custom_priority)
        
        content = ""
        if len(documents) > 1:
            content = self._serialize_multi_doc(documents)
        elif documents:
            content = self._serialize_single_doc(documents[0])
            
        if self._had_leading_boundary and not content.startswith("---"):
            content = "---\n" + content
            
        if compact:
            content = self._apply_compact_mode(content)
                
        return content

    def _apply_sorting(self, documents: List[YamlrNode], custom_priority: Optional[Dict[str, int]]):
        """Helper to apply schema-aware sorting to a list of documents."""
        from yamlr.core.sorting import SortingEngine
        sorter = SortingEngine(custom_priority=custom_priority)
        for doc in documents:
            sorter.reorder_node(
                doc, 
                kind=doc.get("kind") if hasattr(doc, "get") else None, 
                validator=self.validator, 
                catalog=self.catalog
            )

    def _serialize_multi_doc(self, documents: List[YamlrNode]) -> str:
        """Serializes multiple documents with boundary and document-order preservation."""
        # [DETERMINISM] Sort documents by Kind and Name to ensure stable output
        sorted_docs = sorted(
            documents, 
            key=lambda d: (str(d.get("kind", "")), str(d.get("metadata", {}).get("name", "")))
        )
        
        final_docs = []
        for doc in sorted_docs:
            doc_str = self._serialize_single_doc(doc)
            if doc_str:
                if not doc_str.startswith("---"):
                    doc_str = "---\n" + doc_str
                final_docs.append(doc_str.strip())
        return "\n".join(final_docs)

    def _serialize_single_doc(self, doc: YamlrNode) -> str:
        """Serializes a single document with its specific indentation."""
        indent = getattr(doc, "indent_step", 2)
        self.parser.set_indent(mapping=indent, sequence=indent)
        return self.parser.dump(doc)

    def _apply_compact_mode(self, content: str) -> str:
        """Delegates to StageTenVacuum for line-level compaction."""
        from yamlr.core.stages.vacuum import StageTenVacuum
        from yamlr.core.context import HealContext
        dummy_context = HealContext(raw_text=content)
        vacuum_stage = StageTenVacuum(enabled=True)
        vacuum_stage.run(dummy_context)
        return dummy_context.raw_text


    def _build_tree(self, shards: List[Shard], default_kind: str, default_api: str) -> YamlrNode:
        """The core engine that delegates to Physicist and Healer."""
        rebuilt_tree = self.parser.create_node(typ="map")
        
        # 1. Setup Context
        active_kind, active_api = self._discover_identity(shards, default_kind, default_api)
        self.healer.set_resource_context(active_api, active_kind)
        self.physicist.reset(rebuilt_tree)
        
        if not hasattr(self, "duplicate_keys"):
            self.duplicate_keys = []

        # [PHASE 6 FIX] Seed required fields
        self._seed_required_fields(rebuilt_tree, shards)

        for i, shard in enumerate(shards):
            if self._should_skip_shard(shard): continue
            if self._is_required_field_shard(shard):
                self._apply_layout(rebuilt_tree, shard, is_key=True)
                continue

            s_key = self.healer.apply_typo_fix(shard)
            self._process_single_shard(shard, i, shards, s_key)

        # [PHASE 6 FIX] Apply trailing layout
        if shards:
            self._apply_layout(rebuilt_tree, shards[-1], is_trailing=True)

        return rebuilt_tree

    def _seed_required_fields(self, tree: YamlrNode, shards: List[Shard]):
        """Seeds apiVersion and kind at the top for deterministic sorting."""
        for shard in shards:
            if shard.is_list_item or shard.indent > 0: continue
            if shard.key in ["apiVersion", "kind"]:
                tree[shard.key] = shard.value

    def _is_required_field_shard(self, shard: Shard) -> bool:
        """Checks if a shard represents a top-level required field."""
        return shard.indent == 0 and not shard.is_list_item and shard.key in ["apiVersion", "kind"]

    def _process_single_shard(self, shard: Shard, idx: int, shards: List[Shard], s_key: str):
        """Orchestrates the resolution and dispatching of a single shard."""
        s_indent = shard.indent or 0
        s_is_list = shard.is_list_item
        
        self.physicist.resolve_scope(s_indent, s_is_list, s_key, self.healer, is_block=shard.is_block)
        self._handle_nest_prev_ambiguity(s_indent, s_key, s_is_list)
        
        context_data = self.physicist.get_context()
        self._dispatch_shard_to_handler(shard, idx, shards, s_key, s_indent, s_is_list, context_data)

    def _should_skip_shard(self, shard: Shard) -> bool:
        """Determines if a shard is empty and should be ignored."""
        return not shard.key and shard.value is None and not shard.is_list_item

    def _dispatch_shard_to_handler(self, shard: Shard, idx: int, shards: List[Shard], s_key: Optional[str], s_indent: int, s_is_list: bool, context_data: Tuple):
        """Dispatches shard processing to list or map handlers based on context."""
        p_indent, p_cont, _, dot_path, _ = context_data
        s_val = shard.value

        if s_is_list:
            self._handle_explicit_list_item(p_cont, shard, s_key, s_val, s_indent, dot_path)
            return

        if hasattr(p_cont, "is_seq") and p_cont.is_seq:
            self._handle_sequence_append(p_cont, shard, s_key, s_val, s_indent, s_is_list, dot_path, p_indent)
            return

        self._handle_map_entry(p_cont, shard, idx, shards, s_key, s_val, s_indent, dot_path)

    def _discover_identity(self, shards: List[Shard], d_kind: str, d_api: str) -> Tuple[str, str]:
        """Scans shards for kind/apiVersion if not provided."""
        ak, api = d_kind, d_api
        for s in shards:
            if not ak and s.key == "kind": ak = str(s.value).strip("'\"")
            if not api and s.key == "apiVersion": api = str(s.value).strip("'\"")
            if ak and api: break
        return ak or "", api or ""

    def _handle_sequence_append(self, seq: YamlrNode, shard: Shard, key: Optional[str], val: Any, indent: int, is_list: bool, dot_path: str, p_indent: int):
        """Case A: Adding to an existing Sequence."""
        if is_list or not key:
            return

        should_merge = self._should_merge_with_last_item(seq, indent, p_indent, key, dot_path)
        
        if should_merge:
            target = seq[-1]
        else:
            target = self.parser.create_node(typ="map")
            seq.append(target)
            self.physicist.push(indent, target, None, dot_path)

        if self._is_parent(shard, indent):
            self._create_nested_container(target, shard, key, indent, dot_path)
        else:
            if key in target:
                self.duplicate_keys.append((key, shard))
            target[key] = self.healer.clean_value(val, dot_path, key, is_flow=shard.is_flow_style)
            self._apply_layout(target, shard, is_key=True)

    def _should_merge_with_last_item(self, seq: YamlrNode, indent: int, p_indent: int, key: str, dot_path: str) -> bool:
        """Determines if the current key belongs to the preceding sequence item."""
        if not seq or not hasattr(seq[-1], "is_map") or not seq[-1].is_map:
            return False
            
        is_sib = self.healer.is_valid_sibling(dot_path, key)
        with open("d:\\yamlr\\pe_debug.log", "a") as f:
            f.write(f"DEBUG: _should_merge_with_last_item key={key} path={dot_path} is_sib={is_sib}\n")
        
        if indent == p_indent:
            return True
        if indent > p_indent:
            return self.healer.is_valid_sibling(dot_path, key)
        return False

    def _handle_explicit_list_item(self, cont: YamlrNode, shard: Shard, key: Optional[str], val: Any, indent: int, dot_path: str):
        """Case B: Shard has '-' marker."""
        if hasattr(cont, "is_map") and cont.is_map and key and not self.healer.should_be_array(key, dot_path):
            self._heal_non_array_list_marker(cont, shard, key, val, indent, dot_path)
            return

        target_seq = self._get_or_create_sequence(cont, key)
            
        if hasattr(target_seq, "is_map") and target_seq.is_map:
            self._handle_map_to_map_collision(target_seq, shard, key, val, indent, dot_path)
            return

        if not key:
            target_seq.append(self.healer.clean_value(val, dot_path, None, is_flow=shard.is_flow_style))
        else:
            self._append_map_to_sequence(target_seq, shard, key, val, indent, dot_path)

    def _heal_non_array_list_marker(self, cont: YamlrNode, shard: Shard, key: str, val: Any, indent: int, dot_path: str):
        """Standardizes markers that shouldn't be lists according to schema."""
        if key in cont:
            self.duplicate_keys.append((key, shard))
        cont[key] = self.healer.clean_value(val, dot_path, key, is_flow=shard.is_flow_style)
        self._apply_layout(cont, shard, is_key=True)
        self.physicist.push(indent, cont, None, dot_path)

    def _get_or_create_sequence(self, cont: YamlrNode, key: Optional[str]) -> YamlrNode:
        """Helper to ensure a sequence exists at the current path."""
        if not (hasattr(cont, "is_map") and cont.is_map and key):
            return cont
            
        if key not in cont:
            seq = self.parser.create_node(typ="seq")
            cont[key] = seq
            return seq
            
        target = cont[key]
        if not (hasattr(target, "is_seq") and target.is_seq):
            new_seq = self.parser.create_node(typ="seq")
            new_seq.append(target)
            cont[key] = new_seq
            return new_seq
        return target

    def _handle_map_to_map_collision(self, target: YamlrNode, shard: Shard, key: Optional[str], val: Any, indent: int, dot_path: str):
        """Handles structural conflicts where a list item is forced into a map."""
        safe_key = f"item_{len(target)}"
        if isinstance(val, str) and val and len(val) < 20 and " " not in val:
            safe_key = val
        
        cleaned_val = self.healer.clean_value(val, dot_path, key, is_flow=shard.is_flow_style)
        target[safe_key] = cleaned_val
        
        if hasattr(cleaned_val, "is_map"):
            self.physicist.push(indent, cleaned_val, None, dot_path)

    def _append_map_to_sequence(self, seq: YamlrNode, shard: Shard, key: str, val: Any, indent: int, dot_path: str):
        """Creates a new map item within a sequence."""
        new_item = self.parser.create_node(typ="map")
        new_item[key] = self.healer.clean_value(val, dot_path, key, is_flow=shard.is_flow_style)
        seq.append(new_item)
        self.physicist.update_item_indent(indent)
        child_path = dot_path + "." + key if dot_path else key
        self.physicist.push(indent, new_item, key, child_path)
        self._apply_layout(new_item, shard, is_key=True)
        self.physicist.push(indent, new_item, None, dot_path)

    def _handle_map_entry(self, cont: YamlrNode, shard: Shard, idx: int, shards: List[Shard], key: Optional[str], val: Any, indent: int, dot_path: str):
        """Case C: Standard key-value entry."""
        if not key: return
        
        if self._is_parent(shard, indent, idx, shards, dot_path):
            self._create_nested_container(cont, shard, key, indent, dot_path)
        else:
            final_val = self.healer.clean_value(val, dot_path, key, is_flow=shard.is_flow_style)
            if self.healer.should_be_array(key, dot_path) and not (isinstance(final_val, list) or (hasattr(final_val, "is_seq") and final_val.is_seq)):
                final_val = [final_val]
            if key in cont:
                self.duplicate_keys.append((key, shard))
            cont[key] = final_val
            self._apply_layout(cont, shard, is_key=True)

    def _is_parent(self, shard: Shard, indent: int, idx: Optional[int] = None, shards: Optional[List[Shard]] = None, dot_path: str = ""):
        """Checks if the next shard implies a child relationship."""
        if shard.value is not None:
            return False
            
        if shards and idx is not None and idx + 1 < len(shards):
            next_s = shards[idx + 1]
            is_p = (next_s.indent or 0) > indent
            with open("d:\\yamlr\\pe_debug.log", "a") as f:
                f.write(f"DEBUG: _is_parent key={shard.key} indent={indent} next_indent={next_s.indent} res={is_p}\n")
            if is_p: return True
            
            if (next_s.indent or 0) == indent and self.healer.should_be_array(shard.key, dot_path):
                return True
        return False

    def _create_nested_container(self, parent: YamlrNode, shard: Shard, key: str, indent: int, dot_path: str):
        """Creates a nested Map or Sequence based on schema or intent."""
        is_arr = self.healer.should_be_array(key, dot_path)
        with open("d:\\yamlr\\pe_debug.log", "a") as f:
            f.write(f"DEBUG: _create_nested_container key={key} path={dot_path} is_arr={is_arr}\n")
            
        if is_arr:
            child = self.parser.create_node(typ="seq")
        else:
            child = self.parser.create_node(typ="map")
            if shard.value is not None:
                # Preservation for scalar parents (ConfigMaps)
                if key in ("name", "namespace") and indent == 0:
                    parent[key] = self.healer.clean_value(shard.value, dot_path, key)
                    return

        parent[key] = child
        self._apply_layout(parent, shard, is_key=True)
        self.physicist.push(indent, child, key, f"{dot_path}.{key}" if dot_path else key)

    def _apply_layout(self, container: YamlrNode, shard: Shard, is_key: bool = False, is_trailing: bool = False):
        """Attaches saved comments and spacing.
        
        Why: To satisfy the 'Comment Preservation' trust pillar.
        """
        self._apply_start_layout(container, shard, is_key)
        self._apply_trailing_layout(container, shard, is_trailing)

        if shard.comment and is_key:
            container.set_eol_comment(shard.comment, key=shard.key)

    def _apply_start_layout(self, container: YamlrNode, shard: Shard, is_key: bool):
        """Helper to apply indentation-aware start comments."""
        if not shard.layout_sequence:
            return
            
        comments = [str(item) if isinstance(item, str) else "\n" * int(getattr(item, "count", 1)) for item in shard.layout_sequence]
        joined = "\n".join(comments)
        if not joined:
            return
            
        if is_key and shard.key and hasattr(container, "set_key_start_comment"):
            container.set_key_start_comment(shard.key, joined, indent=shard.indent)
        else:
            container.set_start_comment(joined, indent=shard.indent)

    def _apply_trailing_layout(self, container: YamlrNode, shard: Shard, is_trailing: bool):
        """Helper to apply footer comments."""
        if not (is_trailing and shard.trailing_layout_sequence):
            return
            
        comments = [str(item) if isinstance(item, str) else "\n" * int(getattr(item, "count", 1)) for item in shard.trailing_layout_sequence]
        joined = "\n".join(comments)
        if joined and hasattr(container, "set_footer_comment"):
            container.set_footer_comment(joined)

    def _handle_nest_prev_ambiguity(self, s_indent: int, s_key: str, s_is_list: bool):
        """Resolves if a shard belongs to the previous sibling as a child."""
        if s_is_list or not s_key:
            return

        l_indent, l_cont, _, l_path, _ = self.physicist.get_context()
        if s_indent != l_indent or not (hasattr(l_cont, "is_map") and l_cont.is_map) or not l_cont:
            return

        last_key = list(l_cont.keys())[-1]
        target_v = self._resolve_ambiguity_target(l_path, last_key, s_key)
        
        if target_v:
            new_path = f"{l_path}.{last_key}" if l_path else last_key
            self.physicist.push(s_indent, target_v, last_key, new_path)

    def _resolve_ambiguity_target(self, path: str, last_key: str, s_key: str) -> Optional[YamlrNode]:
        """Discovery logic for ambiguity resolution."""
        if not (self.healer.validator and self.healer.definition_key):
            return None
        if self.healer.is_valid_sibling(path, s_key):
            return None
            
        l_cont = self.physicist.get_context()[1]
        field_def = self.healer.get_field_schema(path, last_key)
        
        if field_def and s_key in (field_def.get("properties") or {}):
            prev_val = l_cont[last_key]
            if prev_val is None:
                prev_val = self.parser.create_node(typ="map")
                l_cont[last_key] = prev_val
            
            return prev_val if (hasattr(prev_val, "is_map") and prev_val.is_map) else None
        return None
