#!/usr/bin/env python3
"""
Yamlr STRUCTURER - The Reconciled Architect
-------------------------------------------
Rebuilds the YAML tree from identified shards.
Decomposed and Hardened: v1.1 Refactor.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from io import StringIO
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from yamlr.models import Shard
from yamlr.healers.stabilizer import K8sStabilizer
from yamlr.parsers.physicist import IndentationPhysicist, T_MAP, T_SEQ
from yamlr.parsers.schema_healer import SchemaHealer

if TYPE_CHECKING:
    from yamlr.core.context import HealContext
    from yamlr.validators.schema_validator import SchemaValidator

logger = logging.getLogger("yamlr.parsers.structurer")

class YamlrStructurer:
    """
    The Architect: Orchestrates YAML tree reconstruction.
    """

    def __init__(self, catalog: Dict[str, Any], validator: Optional["SchemaValidator"] = None):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.catalog = catalog
        self.validator = validator
        self.yaml_engine = YAML()
        self.yaml_engine.preserve_quotes = True
        self.yaml_engine.indent(mapping=2, sequence=2, offset=0)

        # Decomposed Components
        self.physicist = IndentationPhysicist()
        self.healer = SchemaHealer(catalog, validator)
        
        # [MODULARITY FIX] Allow injection of custom secret paths
        # Default covers standard K8s Secrets + SealedSecrets + Helm encrypted values
        self.preserve_quote_paths = {
            "data", "stringData", "binaryData", 
            "encryptedData", # SealedSecrets
            "auth", "secret", "token", # Generic sensitive fields
            "password", "key"
        }

    def reconstruct(self, context: "HealContext") -> List[CommentedMap]:
        """[Stage 6] Rebuilds the folder-like structure from flat data shards."""
        all_documents: List[CommentedMap] = []
        current_shards: List[Shard] = []
        doc_count = 0

        try:
            if hasattr(context.shadow_engine, "majority_indent"):
                m_indent = max(2, context.shadow_engine.majority_indent)
                self.yaml_engine.indent(mapping=m_indent, sequence=m_indent, offset=0)

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
                doc = self._process_doc(current_shards, doc_count, context)
                if doc: all_documents.append(doc)

            # Process tracked duplicate keys into findings
            if hasattr(self, "duplicate_keys") and self.duplicate_keys:
                from yamlr.analyzers.base import AnalysisResult
                for d_key, d_shard in self.duplicate_keys:
                    kbs_kind = context.identities[0].kind if context.identities else "Unknown"
                    kbs_name = context.identities[0].name if context.identities else "unknown"
                    context.findings.append(AnalysisResult(
                        analyzer_name="StructurerDuplicateKey",
                        severity="WARNING",
                        message=f"Duplicate key '{d_key}' detected at line {d_shard.line_no}. The latter value overwritten the former.",
                        resource_name=kbs_name,
                        resource_kind=kbs_kind,
                        file_path="unknown",
                        rule_id="yaml/duplicate-key"
                    ))

            return all_documents
        except Exception as e:
            logger.error(f"Stage 6: Critical reconstruction failure: {e}")
            raise

    def _process_doc(self, shards: List[Shard], index: int, context: "HealContext") -> Optional[CommentedMap]:
        """Processes a single document group of shards."""
        identity = context.identities[index] if index < len(context.identities) else None
        kind = identity.kind if identity else None
        api = identity.api_version if identity else None
        
        try:
            doc = self._build_tree(shards, kind, api)
            self._normalize_doc(doc)
            return doc
        except Exception as e:
            import traceback
            logger.error(f"Stage 6: Failed document {index} (kind: {kind}): {e}")
            logger.error(traceback.format_exc())
            return None

    def _normalize_doc(self, doc: CommentedMap):
        """Applies K8s standardizations to the reconstructed document."""
        try:
            kind = (doc.get("kind") or "").lower()
            spec = doc.get("spec") or {}
            pod_spec = spec if kind == "pod" else (spec.get("template") or {}).get("spec") or {}

            for c in pod_spec.get("containers") or []:
                self.normalize_resources(c)
                self.normalize_envfrom(c)

            self.normalize_metadata(doc)
            K8sStabilizer.normalize_deployment_selector(doc)
        except Exception as e:
            logger.debug(f"Normalization skipped: {e}")

    def normalize_resources(self, container: dict):
        """Compatibility proxy for K8sStabilizer."""
        K8sStabilizer.normalize_resources(container)

    def normalize_envfrom(self, container: dict):
        """Compatibility proxy for K8sStabilizer."""
        K8sStabilizer.normalize_envfrom(container)

    def normalize_metadata(self, doc: dict):
        """Compatibility proxy for K8sStabilizer."""
        return K8sStabilizer.normalize_metadata(doc)

    def normalize_deployment_selector_from_template(self, doc: dict):
        """Compatibility proxy for K8sStabilizer."""
        K8sStabilizer.normalize_deployment_selector(doc)

    def serialize(self, documents: List[CommentedMap], compact: bool = False) -> str:
        """[Stage 9] Turns the internal tree back into a text file (YAML)."""
        output = StringIO()
        if compact:
            self.yaml_engine.indent(mapping=2, sequence=2, offset=0)
        try:
            if len(documents) > 1:
                self.yaml_engine.dump_all(documents, output)
            elif documents:
                self.yaml_engine.dump(documents[0], output)
            return output.getvalue()
        finally:
            output.close()

    def _build_tree(self, shards: List[Shard], default_kind: str, default_api: str) -> CommentedMap:
        """The core engine that delegates to Physicist and Healer."""
        rebuilt_tree = CommentedMap()
        
        # 1. Setup Context
        active_kind, active_api = self._discover_identity(shards, default_kind, default_api)
        self.healer.set_resource_context(active_api, active_kind)
        self.physicist.reset(rebuilt_tree)
        
        if not hasattr(self, "duplicate_keys"):
            self.duplicate_keys = []

        for i, shard in enumerate(shards):
            if not shard.key and shard.value is None and not shard.is_list_item:
                continue

            # 2. Extract Shard Properties
            s_key = self.healer.apply_typo_fix(shard)
            s_val = shard.value
            s_indent = shard.indent or 0
            s_is_list = shard.is_list_item
            
            # 3. Resolve Scope via Physics
            self.physicist.resolve_scope(s_indent, s_is_list, s_key, self.healer)
            
            # [PARITY FIX] Handle Tri-State Ambiguity (Nest-Prev)
            # If same indent as sibling, check if we belong to it instead.
            self._handle_nest_prev_ambiguity(s_indent, s_key, s_is_list)
            
            p_indent, p_cont, p_key, dot_path, _ = self.physicist.get_context()

            # 4. Hybrid Construction Logic (Container Dispatch)
            if s_is_list:
                self._handle_explicit_list_item(p_cont, shard, s_key, s_val, s_indent, dot_path)
                continue

            if isinstance(p_cont, T_SEQ):
                self._handle_sequence_append(p_cont, shard, s_key, s_val, s_indent, s_is_list, dot_path, p_indent)
                continue

            self._handle_map_entry(p_cont, shard, i, shards, s_key, s_val, s_indent, dot_path)

        return rebuilt_tree

    def _discover_identity(self, shards: List[Shard], d_kind: str, d_api: str) -> Tuple[str, str]:
        """Scans shards for kind/apiVersion if not provided."""
        ak, api = d_kind, d_api
        for s in shards:
            if not ak and s.key == "kind": ak = str(s.value).strip("'\"")
            if not api and s.key == "apiVersion": api = str(s.value).strip("'\"")
            if ak and api: break
        return ak or "", api or ""

    def _handle_sequence_append(self, seq, shard, key, val, indent, is_list, dot_path, p_indent):
        """Case A: Adding to an existing Sequence."""
        if not is_list and key:
            # Check if we belong to the last item in the sequence
            target = None
            should_merge = False
            
            if len(seq) > 0 and isinstance(seq[-1], T_MAP):
                if indent == p_indent:
                    should_merge = True
                elif indent > p_indent:
                     # Heuristic: If indentation is deeper but it's a valid field of the item, 
                     # assume it belongs to the previous item (messy indentation healing).
                     if self.healer.is_valid_sibling(dot_path, key):
                         should_merge = True

            if should_merge:
                target = seq[-1]
            else:
                target = T_MAP()
                seq.append(target)
                self.physicist.push(indent, target, None, dot_path)

            if self._is_parent(shard, indent):
                self._create_nested_container(target, shard, key, indent, dot_path)
            else:
                if isinstance(target, dict) and key in target:
                    self.duplicate_keys.append((key, shard))
                target[key] = self.healer.clean_value(val, None, dot_path, key, is_flow=shard.is_flow_style)
                self._apply_layout(target, shard, is_key=True)

    def _handle_explicit_list_item(self, cont, shard, key, val, indent, dot_path):
        """Case B: Shard has '-' marker."""
        if isinstance(cont, T_MAP) and key and not self.healer.should_be_array(key, dot_path):
            # Schema-heal: Not an array but marked as one
            if key in cont:
                self.duplicate_keys.append((key, shard))
            cont[key] = self.healer.clean_value(val, key, dot_path, key, is_flow=shard.is_flow_style)
            self._apply_layout(cont, shard, is_key=True)
            self.physicist.push(indent, cont, None, dot_path)
            return

        target_seq = None
        if isinstance(cont, T_MAP) and key:
            if key not in cont:
                target_seq = T_SEQ()
                cont[key] = target_seq
            else:
                target_seq = cont[key]
                # Auto-heal: If target is not a list, convert it to one (Scalar -> List[Scalar])
                if not isinstance(target_seq, list):
                    new_seq = T_SEQ()
                    new_seq.append(target_seq)
                    cont[key] = new_seq
                    target_seq = new_seq
        else:
            target_seq = cont
            
        # Fallback for Map Collision (Map -> Map with generated key)
        if isinstance(target_seq, (dict, T_MAP)):
             safe_key = f"item_{len(target_seq)}"
             if isinstance(val, str) and val and len(val) < 20 and " " not in val:
                  safe_key = val
             
             cleaned_val = self.healer.clean_value(val, None, dot_path, key, is_flow=shard.is_flow_style)
             target_seq[safe_key] = cleaned_val
             
             if isinstance(cleaned_val, (dict, list)):
                 self.physicist.push(indent, cleaned_val, None, dot_path)
             return

        if not key:
            target_seq.append(self.healer.clean_value(val, None, dot_path, None, is_flow=shard.is_flow_style))
        else:
            new_item = T_MAP()
            new_item[key] = self.healer.clean_value(val, key, dot_path, key, is_flow=shard.is_flow_style)
            target_seq.append(new_item)
            self.physicist.update_item_indent(indent)
            self._apply_layout(new_item, shard, is_key=True)
            self.physicist.push(indent, new_item, None, dot_path)

    def _handle_map_entry(self, cont, shard, idx, shards, key, val, indent, dot_path):
        """Case C: Standard key-value entry."""
        if not key: return
        
        if self._is_parent(shard, indent, idx, shards, dot_path):
            self._create_nested_container(cont, shard, key, indent, dot_path)
        else:
            final_val = self.healer.clean_value(val, None, dot_path, key, is_flow=shard.is_flow_style)
            if self.healer.should_be_array(key, dot_path) and not isinstance(final_val, list):
                final_val = [final_val]
            if isinstance(cont, dict) and key in cont:
                self.duplicate_keys.append((key, shard))
            cont[key] = final_val
            self._apply_layout(cont, shard, is_key=True)

    def _is_parent(self, shard, indent, idx=None, shards=None, dot_path=""):
        """Checks if the next shard implies a child relationship."""
        if shard.value is not None:
            return False
            
        if shards and idx is not None and idx + 1 < len(shards):
            next_s = shards[idx + 1]
            if (next_s.indent or 0) > indent: return True
            # Flush-left array child check
            if (next_s.indent or 0) == indent and self.healer.should_be_array(shard.key, dot_path):
                return True
        return False

    def _create_nested_container(self, parent, shard, key, indent, dot_path):
        """Creates and pushes a new Map or Seq container."""
        if self.healer.should_be_array(key, dot_path):
            child = T_SEQ()
        else:
            child = T_MAP()
            if shard.value is not None:
                # Preservation for scalar parents (ConfigMaps)
                if key in ("name", "namespace") and indent == 0:
                    parent[key] = self.healer.clean_value(shard.value, key, dot_path, key)
                    return

        parent[key] = child
        self._apply_layout(parent if isinstance(child, T_SEQ) else child, shard, is_key=not isinstance(child, T_MAP))
        self.physicist.push(indent, child, key, f"{dot_path}.{key}" if dot_path else key)

    def _apply_layout(self, container: Any, shard: Shard, is_key: bool = False):
        """Attaches saved comments and spacing."""
        if shard.layout_sequence:
            comments = [str(item) if isinstance(item, str) else "" * int(getattr(item, "count", 0)) for item in shard.layout_sequence]
            if comments:
                try:
                    container.yaml_set_start_comment("\n".join(comments), indent=shard.indent)
                except Exception as e:
                    logger.debug(f"Layout: Start-comment injection failed for {shard.key or 'unnamed'}: {e}")
        if shard.comment and is_key and isinstance(container, CommentedMap):
            try:
                container.yaml_add_eol_comment(shard.comment, key=shard.key)
            except Exception as e:
                logger.debug(f"Layout: EOL-comment injection failed for {shard.key}: {e}")

    def _handle_nest_prev_ambiguity(self, s_indent: int, s_key: str, s_is_list: bool):
        """
        [Parity] Resolves if a shard at the same indent as its parent actually belongs 
        to the previous sibling as a child (Ambiguity Resolution).
        """
        if s_is_list or not s_key: return

        l_indent, l_cont, _, l_path, _ = self.physicist.get_context()
        if s_indent != l_indent or not isinstance(l_cont, T_MAP) or not l_cont:
            return

        # Check State 2: Does it belong to the previous sibling as a child?
        if self.healer.validator and self.healer.definition_key:
            if not self.healer.is_valid_sibling(l_path, s_key):
                last_key = list(l_cont.keys())[-1]
                field_def = self.healer.get_field_schema(l_path, last_key)
                
                if field_def and s_key in field_def.get("properties", {}):
                    # It belongs to the previous sibling! Nest it.
                    prev_val = l_cont[last_key]
                    if prev_val is None:
                        prev_val = T_MAP()
                        l_cont[last_key] = prev_val
                    
                    if isinstance(prev_val, T_MAP):
                        new_path = f"{l_path}.{last_key}" if l_path else last_key
                        self.physicist.push(s_indent, prev_val, last_key, new_path)
