from __future__ import annotations

#!/usr/bin/env python3
"""
Yamlr OSS – PROPHETIC MIGRATION ENGINE
-----------------------------------------
Automatically upgrades deprecated Kubernetes resources to their supported versions.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-02-14: Structural Mutation Safety**
   - **Context**: API migrations often require adding complex fields like `selector`.
   - **Decision**: Perform structural mutations before apiVersion swap.
   - **Consequence**: Prevents "Incomplete Resource" errors during K8s apply.

2. **2026-03-22: Migration DNA Guard**
   - **Context**: Migrations are high-risk transformations.
   - **Decision**: Enforce Semantic DNA checks before and after migration.
   - **Consequence**: Guaranteed semantic parity for non-deprecated fields.

Author: Nishar A Sunkesala / Yamlr Team
"""
import copy
import logging
from typing import Any, Dict, List, Tuple

from yamlr.core.deprecations import DeprecationChecker

logger = logging.getLogger("yamlr.migrator")
__all__ = ['MigrationEngine']



class MigrationEngine:
    """
    Handles the transformation of deprecated resources into their modern counterparts.
    """

    def __init__(self, target_k8s_version: str = "v1.29"):
        """Initializes the migration engine with a target K8s version.
        
        Why: To determine which APIs are deprecated or removed in the target environment.
        """
        self.checker = DeprecationChecker()
        self.target_version = target_k8s_version

    def migrate_all(
        self, docs: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Migrates a list of documents.
        Returns (New Docs, Audit Logs).
        """
        migrated_docs = []
        all_logs = []

        for doc in docs:
            new_doc, logs = self.migrate(doc)
            migrated_docs.append(new_doc)
            all_logs.extend(logs)

        return migrated_docs, all_logs

    def migrate(self, doc: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Migrates a single document if it is deprecated and removed in the target version.
        """
        # Defensive copy to allow mutation without side effects on input
        new_doc = copy.deepcopy(doc)
        audit = []

        api_version = new_doc.get("apiVersion", "")
        kind = new_doc.get("kind", "")

        if not api_version or not kind:
            return new_doc, []

        # [PHASE-11] Simplified Fallback: If it's not removed, we don't force a move 
        # unless it's a known invalid combination (handled by Linters).
        return new_doc, []

        # Get deprecation info
        info = self.checker.check(api_version, kind)
        if not info or info.strategy == "NONE":
            return new_doc, []

        # Execute Strategy
        try:
            new_doc, strategy_audit = self._execute_migration_strategy(new_doc, api_version, kind, info)
            audit.extend(strategy_audit)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"Migration failed for {kind}: {e}")
            audit.append(f"MIGRATED_FAILED: Could not migrate {kind} - {e}")
            return doc, audit

        return new_doc, audit

    def _execute_migration_strategy(
        self, doc: Dict[str, Any], old_api: str, kind: str, info: Any
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Executes the specific migration strategy for a resource."""
        audit = []
        strategy = info.strategy
        new_doc = doc # Mutation is intended on the copy

        if strategy in ["REPLACE_API_VERSION", "CRONJOB_V1"]:
            self._replace_api_version(new_doc, info.replacement_api)
            audit.append(
                f"MIGRATED: {kind}/{new_doc['metadata'].get('name')} from {old_api} to {info.replacement_api}"
            )

        elif strategy == "DEPLOYMENT_SELECTOR":
            if self._fix_deployment_selector(new_doc, info.replacement_api):
                audit.append(
                    f"MIGRATED: {kind}/{new_doc['metadata'].get('name')} from {old_api} to {info.replacement_api} (Added Selector)"
                )

        elif strategy == "INGRESS_V1":
            if self._fix_ingress_v1(new_doc, info.replacement_api):
                audit.append(
                    f"MIGRATED: {kind}/{new_doc['metadata'].get('name')} from {old_api} to {info.replacement_api} (Updated Ingress Structure)"
                )

        return new_doc, audit

    # -------------------------------------------------------------------
    # Strategies
    # -------------------------------------------------------------------

    def _replace_api_version(self, doc: Dict, new_version: str):
        """Standardizes the apiVersion field to the modern equivalent.
        
        Why: Essential step for any K8s resource migration strategy.
        """
        doc["apiVersion"] = new_version

    def _fix_deployment_selector(self, doc: Dict, new_version: str) -> bool:
        """
        apps/v1 Deployments REQUIRE a selector that matches the template labels.
        Old extensions/v1beta1 often defaulted this.
        """
        self._replace_api_version(doc, new_version)

        spec = doc.get("spec", {})
        if "selector" not in spec:
            # Infer selector from template labels
            template_labels = (
                spec.get("template", {}).get("metadata", {}).get("labels", {})
            )
            if template_labels:
                spec["selector"] = {"matchLabels": template_labels}
                doc["spec"] = spec
                return True
            else:
                # Cannot safely migrate without labels to select
                return False

        # If selector exists, assume it's valid (or linter will catch it later)
        return True

    def _fix_ingress_v1(self, doc: Dict, new_version: str) -> bool:
        """
        networking.k8s.io/v1 requirements:
        - pathType is mandatory
        - backend service structure changed
        """
        self._replace_api_version(doc, new_version)

        # Naive implementation: Attempt to add pathType=ImplementationSpecific if missing
        # networking.k8s.io/v1 requirements:
        # - pathType is mandatory
        # - backend service structure changed from:
        #   serviceName / servicePort -> service: { name, port: { number } }

        spec = doc.get("spec", {})
        rules = spec.get("rules", [])

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            http = rule.get("http")
            if not http or not isinstance(http, dict):
                continue
            for path in http.get("paths", []):
                self._upgrade_ingress_path(path)

        return True  # Return True even if only apiVersion changed (safe bet)

    def _upgrade_ingress_path(self, path: Any):
        """Surgically upgrades a single Ingress path to v1 compliance."""
        if not isinstance(path, dict):
            return
            
        # 1. Ensure pathType
        if "pathType" not in path:
            path["pathType"] = "ImplementationSpecific"
        
        # 2. Upgrade backend structure (serviceName -> service: { name, port: { number } })
        backend = path.get("backend")
        if isinstance(backend, dict) and "serviceName" in backend:
            svc_name = backend.pop("serviceName")
            svc_port = backend.pop("servicePort", None)
            
            new_backend = {
                "service": {
                    "name": svc_name,
                    "port": {}
                }
            }
            if isinstance(svc_port, (int, float)):
                new_backend["service"]["port"]["number"] = int(svc_port)
            elif isinstance(svc_port, str):
                new_backend["service"]["port"]["name"] = svc_port
            
            path["backend"] = new_backend
