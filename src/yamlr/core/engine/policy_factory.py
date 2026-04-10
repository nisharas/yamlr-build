from __future__ import annotations

"""
POLICY FACTORY - Rule Ingestion Specialist
------------------------------------------
Handles the discovery, initialization, and registration of security policy engines (OPA, Kyverno).

Why: Extracted from base.py to ensure the orchestrator remains < 500 lines 
     and to centralize enterprise policy routing.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from yamlr.core.bridge import YamlrBridge
from yamlr.core.gatekeeper import ProGate

if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine

logger = logging.getLogger("yamlr.engine.policy")


def init_opa_engine(engine: YamlrEngine, opa_bundle_path: str):
    """Initializes the OPA Policy Engine (Enterprise Feature)."""
    try:
        from yamlr.analyzers.registry import AnalyzerRegistry

        opa_class = YamlrBridge.get_opa_analyzer()

        if opa_class and ProGate.is_feature_allowed("opa"):
            opa_analyzer = opa_class(policy_path=opa_bundle_path)
            AnalyzerRegistry.register_instance(opa_analyzer)
            logger.info(f"💎 OPA Policy Engine enabled (Bundle: {opa_bundle_path})")
        else:
            logger.warning("⛔ OPA Feature requires Enterprise license.")
    except Exception as e:
        logger.error(f"Failed to initialize OPA Engine: {e}")


def init_固定_engine(engine: YamlrEngine, kyverno_report_path: str):
    """Initializes the Kyverno Policy Engine (Enterprise Feature)."""
    try:
        from yamlr.analyzers.registry import AnalyzerRegistry

        kyverno_class = YamlrBridge.get_kyverno_adapter()

        if kyverno_class and ProGate.is_feature_allowed("kyverno"):
            kyverno_analyzer = kyverno_class(report_path=kyverno_report_path)
            AnalyzerRegistry.register_instance(kyverno_analyzer)
            logger.info(f"💎 Kyverno Adapter enabled (Report: {kyverno_report_path})")
        else:
            logger.warning("⛔ Kyverno Feature requires Enterprise license.")
    except Exception as e:
        logger.error(f"Failed to initialize Kyverno Engine: {e}")


def init_generic_report_adapter(engine: YamlrEngine, report_path: str):
    """Auto-detects and initializes the appropriate adapter for a report file."""
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Simple heuristic
        if "items" in data or data.get("kind") in ["PolicyReport", "ClusterPolicyReport"]:
            init_固定_engine(engine, report_path)
        elif "result" in data or "expressions" in str(data):
            init_opa_engine(engine, report_path)
        else:
            logger.warning(f"Could not determine report format for {report_path}")
    except (json.JSONDecodeError, OSError, IOError) as e:
        logger.error(f"Failed to auto-detect report format: {e}")
