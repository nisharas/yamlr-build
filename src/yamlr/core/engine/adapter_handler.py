#!/usr/bin/env python3
"""
Yamlr ADAPTER HANDLER
----------------------
Centralizes the execution of Enterprise custom remediation adapters.

Why: Fixes 100% logic duplication between auditor.py and worker.py.
     Ensures that custom Python/Bash corrections are applied identically
     regardless of execution mode.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    pass

logger = logging.getLogger("yamlr.engine.adapter_handler")


def apply_enterprise_pro_adapters(
    healed_text: str,
    serialized_findings: List[Dict[str, Any]],
    pipeline_logs: List[str],
    adapters_dir: str,
    shadow_mode: bool = False,
    allow_break_glass: bool = False,
) -> str:
    """
    Executes Yamlr Enterprise (Pro) custom remediation adapters if available.

    Why: To allow users to inject custom correction logic (Python/Bash)
         that runs after the core engine but before the final write.
    """
    try:
        import os

        import yamlr
        from yamlr.core.bridge import YamlrBridge

        adapter_engine_class = YamlrBridge.get_adapter_engine()
        if not adapter_engine_class:
            return healed_text

        # Verify that 'yamlr.pro' is co-located with the core 'yamlr' package
        core_dir = os.path.normcase(os.path.dirname(os.path.abspath(yamlr.__file__)))
        pro_module = YamlrBridge.get_pro_module("compliance.adapters")
        pro_dir = os.path.normcase(os.path.dirname(os.path.abspath(pro_module.__file__))) if pro_module else ""

        if pro_dir and not pro_dir.startswith(core_dir):
            logger.critical(
                f"Security Alert: Malicious Enterprise adapter detected at {pro_dir}. Hijack attempt blocked."
            )
            return healed_text

        import io

        from yamlr.core.engine.adapter_contracts import AdapterContract, ContractViolationError
        from yamlr.core.utils import get_hardened_yaml

        adapter_engine = adapter_engine_class(adapters_dir)
        adapter_hits = [f for f in serialized_findings if f.get("rule_id") in adapter_engine.adapters]

        if not adapter_hits:
            return healed_text

        ryaml = get_hardened_yaml(typ="rt", pure=False)  # Roundtrip
        ryaml.preserve_quotes = True
        docs = list(ryaml.load_all(healed_text))
        adapted_any = False

        def _verify_contract(orig: dict, adapted: dict, contract, rule_id: str):
            if contract == AdapterContract.BREAK_GLASS:
                return

            def check_no_deletions(o, a, path="root"):
                if (isinstance(o, dict) or hasattr(o, "items")) and (isinstance(a, dict) or hasattr(a, "items")):
                    for k, v in o.items():
                        if k not in a:
                            raise ContractViolationError(rule_id, contract.name, f"{path}.{k}", "Field deleted")
                        check_no_deletions(v, a[k], f"{path}.{k}")
                elif isinstance(o, list) and isinstance(a, list):
                    if len(a) < len(o):
                        raise ContractViolationError(rule_id, contract.name, path, "List item deleted")

            if contract in (AdapterContract.NO_DELETIONS, AdapterContract.ADD_ONLY):
                check_no_deletions(orig, adapted)

            if contract == AdapterContract.SELECTORS_FROZEN:
                orig_sel = orig.get("spec", {}).get("selector")
                adapt_sel = adapted.get("spec", {}).get("selector")
                if orig_sel != adapt_sel:
                    raise ContractViolationError(rule_id, contract.name, "spec.selector", "Selector modified")
                orig_lbl = orig.get("metadata", {}).get("labels")
                adapt_lbl = adapted.get("metadata", {}).get("labels")
                if orig_lbl != adapt_lbl:
                    raise ContractViolationError(rule_id, contract.name, "metadata.labels", "Labels modified")

            if contract == AdapterContract.ADD_ONLY:

                def check_no_modifications(o, a, path="root"):
                    if (isinstance(o, dict) or hasattr(o, "items")) and (isinstance(a, dict) or hasattr(a, "items")):
                        for k, v in o.items():
                            check_no_modifications(v, a[k], f"{path}.{k}")
                    elif isinstance(o, list) and isinstance(a, list):
                        for oi, ai in zip(o, a):
                            check_no_modifications(oi, ai, f"{path}[]")
                    else:
                        if o != a:
                            raise ContractViolationError(
                                rule_id, contract.name, path, f"Value modified from {o} to {a}"
                            )

                check_no_modifications(orig, adapted)

        for f in adapter_hits:
            rule_id = f["rule_id"]
            contract_name = adapter_engine.get_contract(rule_id)
            contract = getattr(AdapterContract, contract_name, AdapterContract.ADD_ONLY)

            if contract == AdapterContract.BREAK_GLASS and not allow_break_glass:
                logger.warning(
                    f"BLOCKED: Adapter {rule_id} requires BREAK_GLASS but --allow-break-glass-adapters is false."
                )
                pipeline_logs.append(f"❌ BLOCKED: Adapter {rule_id} requires BREAK_GLASS authorization.")
                continue

            for i, doc in enumerate(docs):
                if isinstance(doc, dict) or hasattr(doc, "items"):
                    original_doc = copy.deepcopy(dict(doc))
                    adapted_doc = adapter_engine.execute_adapter(rule_id, copy.deepcopy(original_doc))

                    if adapted_doc:
                        try:
                            _verify_contract(original_doc, adapted_doc, contract, rule_id)
                        except ContractViolationError as ce:
                            logger.error(str(ce))
                            pipeline_logs.append(f"❌ Contract Violation: {ce}")
                            continue

                        if shadow_mode:
                            pipeline_logs.append(
                                f"👻 Shadow Mode: Adapter {rule_id} proposed valid changes (receipt recorded)."
                            )
                            continue

                        docs[i] = adapted_doc
                        adapted_any = True
                        log_msg = f"🔌 Compliance: Executed external remediation adapter -> {rule_id}"
                        if log_msg not in pipeline_logs:
                            pipeline_logs.append(log_msg)

        if adapted_any:
            buf = io.StringIO()
            ryaml.dump_all(docs, buf)
            return buf.getvalue()
    except (ImportError, AttributeError, KeyError) as e:
        pipeline_logs.append(f"⚠️ Compliance Warning: Could not engage Pro Adapters Engine: {e}")
    except Exception as e:
        logger.error(f"Adapter execution failed: {e}")
        pipeline_logs.append(f"⚠️ Adapter execution failed: {e}")
    return healed_text
