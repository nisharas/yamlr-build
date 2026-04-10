"""
Yamlr PRO BRIDGE - Registry Hook
--------------------------------
What: Plugs Enterprise-grade capability providers into the Core Bridge.
Why: Enforces strict Tier Separation (Core doesn't know about Pro).
Where: Loaded by the Pro binary/extension at startup.
"""

from __future__ import annotations

import logging
from yamlr.core.bridge import YamlrBridge

logger = logging.getLogger("yamlr.pro.bridge")

def initialize_pro_bridge():
    """
    Registers all enterprise capabilities into the YamlrBridge.
    
    Why: This is the heartbeat of the 'Supplier Pivot.' Core provides the 
         orchestration; Pro provides the specialized logic.
    """
    try:
        # 🧪 Registration: Specialized Healing (VAL-02-8 Heritage)
        import yamlr.pro.surgery as surgery
        YamlrBridge.register_capability("surgery", surgery)

        # 🧪 Registration: Enterprise Hardening (VAL-02-1 Forensic)
        import yamlr.pro.shield as shield
        YamlrBridge.register_capability("shield", shield)

        # 🧪 Registration: OPA/Kyverno Adapters
        import yamlr.pro.opa_adapter as opa
        YamlrBridge.register_capability("opa_adapter", opa)

        import yamlr.pro.license as license_pro
        YamlrBridge.register_capability("license", license_pro)

        import yamlr.pro.auth as auth
        YamlrBridge.register_capability("auth", auth)

        # 🧪 Registration: Compliance & Evidence
        import yamlr.pro.compliance.evidence as evidence
        YamlrBridge.register_capability("compliance.evidence", evidence)

        import yamlr.pro.compliance.aggregator as aggregator
        YamlrBridge.register_capability("compliance.aggregator", aggregator)

        import yamlr.pro.compliance.ruleset as ruleset
        YamlrBridge.register_capability("compliance.ruleset", ruleset)

        # 🧪 Registration: Cluster Detection
        import yamlr.pro.cluster_detection as cluster
        YamlrBridge.register_capability("cluster_detection", cluster)

        # 🧪 Registration: Exporter
        import yamlr.pro.exporter as exporter
        YamlrBridge.register_capability("exporter", exporter)

        logger.info("🛡️ Yamlr Pro Bridge registered successfully.")
    except ImportError as e:
        logger.warning(f"⚠️ Failed to register some Pro capabilities: {e}")
    except Exception as e:
        logger.error(f"❌ Critical error during Pro bridge initialization: {e}")

# Trigger registration on import for standalone Pro usage
if __name__ == "yamlr.pro.bridge":
    initialize_pro_bridge()
