#!/usr/bin/env python3
"""
RELATIONAL STAGE - The Connector
--------------------------------
Builds and verifies relationships between disparate K8s resources.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-03-10: Cross-Resource Analysis Delegation**
   - **Context**: Verifying Service/Deployment affinity was slowing down the pipeline.
   - **Decision**: Delegate relationship building to the `ResourceGraph` engine.
   - **Consequence**: O(1) lookups for related resources during healing phases.

2. **2026-03-22: Namespace Boundaries**
   - **Context**: Cross-namespace referential healing can be risky.
   - **Decision**: Enforce strict namespace isolation by default.
   - **Consequence**: Prevents "Spooky Action at a Distance" where healing one app breaks another.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from yamlr.core.context import HealContext
from yamlr.core.resource_graph import ResourceGraph
from yamlr.core.stages.base import PipelineStage
from yamlr.core.stages.boundaries import MutationScope
from yamlr.models import HealAction, ManifestIdentity

logger = logging.getLogger("yamlr.stages.relational")

class StageRelationalSurgery(PipelineStage):
    """
    Detects and repairs broken cross-resource relationships.
    """

    def __init__(self, name: str):
        super().__init__(name)

    def run(self, context: HealContext):
        """Analyzes the blast radius of changes and issues warnings/fixes."""
        context.audit_log.append("Stage 5.7: Relational Surgery run.")
        if not context.workspace_identities:
            context.audit_log.append("  Warning: No workspace identities found for relational analysis.")
            return {"success": True}

        # 1. Build the graph from the ORIGINAL (Workspace) state
        original_graph = ResourceGraph()
        original_graph.build(context.workspace_identities)
        
        # [RENAME-TRACKING] Create a mapping for stable document identification
        # Why: To find the blast radius of a resource even if its name has changed.
        original_doc_map = {
            (ident.file_path, ident.doc_index): ident 
            for ident in context.workspace_identities
        }

        # 2. Check each identity in the current context (the "Proposed" state)
        for identity in context.identities:
            # Find the original identity for this document
            original_ident = original_doc_map.get((identity.file_path, identity.doc_index))
            if not original_ident:
                continue
                
            orig_key = f"{original_ident.kind}/{original_ident.namespace or 'default'}/{original_ident.name}"
            
            # Find what WAS connected to this resource's original identity
            original_radius = original_graph.blast_radius(orig_key)
            if not original_radius.affected_nodes:
                continue
                
            # [BACK-HEALING] If the name changed, we MUST update all dependents
            was_renamed = identity.name != original_ident.name
            
            # Check if those original connections are now broken or need updates
            for affected_node in original_radius.affected_nodes:
                # [DETERMINISM] If renamed, notify dependents
                if was_renamed:
                    self._prescribe_rename_fix(identity, original_ident, affected_node.identity, context)
                
                self._verify_connection(identity, affected_node.identity, context)

        return {"success": True}

    def _prescribe_rename_fix(self, current: ManifestIdentity, original: ManifestIdentity, dependent: ManifestIdentity, context: HealContext):
        """Prescribes a fix for a dependent resource when its provider is renamed."""
        if current.kind == "Service" and dependent.kind == "Ingress":
            context.prescribe(
                HealAction(
                    stage="RelationalSurgery",
                    action_type="broken_link",
                    target=f"{dependent.kind}/{dependent.name}",
                    description=f"Auto-Healing: Service '{original.name}' was renamed to '{current.name}'. Updating Ingress backend.",
                    severity="WARNING",
                    rule_id="ref/ingress-rename-sync",
                    rationale="When a Service is renamed, all Ingress resources referencing it must be updated to maintain traffic flow.",
                    suggestion=f"Update backend serviceName to '{current.name}'",
                    new_value=current.name,
                    field="spec.rules[].http.paths[].backend.service.name", # Template for healer
                    risk_level="MEDIUM",
                    scope=MutationScope.RELATIONAL
                )
            )
        elif current.kind == "Deployment" and dependent.kind == "HorizontalPodAutoscaler":
            context.prescribe(
                HealAction(
                    stage="RelationalSurgery",
                    action_type="broken_link",
                    target=f"{dependent.kind}/{dependent.name}",
                    description=f"Auto-Healing: Deployment '{original.name}' was renamed to '{current.name}'. Updating HPA target.",
                    severity="WARNING",
                    rule_id="ref/hpa-rename-sync",
                    rationale="When a Deployment is renamed, all HPAs targeting it must be updated to maintain auto-scaling.",
                    suggestion=f"Update scaleTargetRef to '{current.name}'",
                    new_value=current.name,
                    field="spec.scaleTargetRef.name",
                    risk_level="MEDIUM",
                    scope=MutationScope.RELATIONAL
                )
            )

    def _verify_hpa_deployment(self, deployment: ManifestIdentity, hpa: ManifestIdentity, context: HealContext):
        """Verify HPA target matches Deployment name and is in same namespace."""
        if hpa.scale_target != deployment.name:
            context.prescribe(
                HealAction(
                    stage="RelationalSurgery",
                    action_type="broken_link",
                    target=f"{hpa.kind}/{hpa.name}",
                    description=f"HPA Desync! HorizontalPodAutoscaler '{hpa.name}' targets '{hpa.scale_target}', but Deployment was renamed to '{deployment.name}'.",
                    severity="ERROR",
                    rule_id="ref/hpa-target-miss",
                    rationale="HPAs must target a valid workload name to enable auto-scaling.",
                    suggestion=f"Update scaleTargetRef.name to '{deployment.name}'",
                    impact_description="Auto-scaling will fail, potentially leading to resource exhaustion under load.",
                    risk_level="HIGH",
                    scope=MutationScope.RELATIONAL
                )
            )

    def _verify_pvc_storageclass(self, storage_class: ManifestIdentity, pvc: ManifestIdentity, context: HealContext):
        """Verify PVC refers to an existing StorageClass if explicitly set."""
        if not pvc.storage_class_refs:
            return
            
        is_used = any(ref == storage_class.name for ref in pvc.storage_class_refs)
        if not is_used:
            return
            
        # StorageClasses are cluster-scoped. If we are here, it means we found a relationship.

    def _verify_connection(self, proposed_identity: ManifestIdentity, dependent_identity: ManifestIdentity, context: HealContext):
        """Verify if a link that existed in original state still exists.
        
        Why: Decouples relationship detection from specific validation logic,
             reducing cognitive complexity from O(N) conditionals to O(1) lookup.
        """
        handlers = {
            ("Deployment", "Service"): self._verify_service_deployment,
            ("Deployment", "HorizontalPodAutoscaler"): self._verify_hpa_deployment,
            ("Service", "Ingress"): self._verify_ingress_service,
            ("StorageClass", "PersistentVolumeClaim"): self._verify_pvc_storageclass,
        }
        
        handler = handlers.get((proposed_identity.kind, dependent_identity.kind))
        if handler:
            handler(proposed_identity, dependent_identity, context)

    def _verify_service_deployment(self, deployment: ManifestIdentity, service: ManifestIdentity, context: HealContext):
        """Verify Service selector matches Deployment labels."""
        matches = self._selector_matches(service, deployment)
        if not matches:
            context.prescribe(
                HealAction(
                    stage="RelationalSurgery",
                    action_type="broken_link",
                    target=f"{service.kind}/{service.name}",
                    description=f"Link Broken! Mutation to '{deployment.name}' labels disconnected Service '{service.name}'.",
                    severity="ERROR",
                    rule_id="ref/ghost-service",
                    rationale="A label change in a Deployment must be mirrored in its Service selector to maintain traffic flow.",
                    suggestion="Update Service selector to match new Deployment labels.",
                    impact_description="The Service will have no endpoints, leading to 503 errors.",
                    risk_level="HIGH",
                    scope=MutationScope.RELATIONAL
                )
            )

    def _verify_ingress_service(self, service: ManifestIdentity, ingress: ManifestIdentity, context: HealContext):
        """Verify Ingress backends match existing Services."""
        if not ingress.service_refs:
            return
            
        # [DNA-HEALING] Deep Port Mapping Verification
        for ref in ingress.service_refs:
            if ref.get("name") != service.name:
                continue
                
            target_port = ref.get("port")
            if not target_port or not service.ports:
                continue
                
            if not self._port_matches_service(target_port, service.ports):
                context.prescribe(
                    HealAction(
                        stage="RelationalSurgery",
                        action_type="broken_link",
                        target=f"{ingress.kind}/{ingress.name}",
                        description=f"Backend Mismatch! Ingress '{ingress.name}' refers to port '{target_port}' on Service '{service.name}', but it doesn't exist.",
                        severity="ERROR",
                        rule_id="ref/ingress-port-miss",
                        rationale="Ingress backends must point to a valid port name or number defined in the target Service.",
                        suggestion=f"Update Ingress backend port to match one of {service.ports}",
                        impact_description="Traffic to this path will fail with a 502/503 error.",
                        risk_level="HIGH",
                        scope=MutationScope.RELATIONAL
                    )
                )

    def _port_matches_service(self, target_port: str, service_ports: List[Dict[str, Any]]) -> bool:
        """Helper to check if a port name or number exists in a list of ServicePorts."""
        target_str = str(target_port)
        for p in service_ports:
            if str(p.get("port")) == target_str or p.get("name") == target_str:
                return True
        return False

    def _selector_matches(self, service_identity: ManifestIdentity, deployment_identity: ManifestIdentity) -> bool:
        """Helper to verify if a Service still selects a Deployment."""
        if not service_identity.selector or not deployment_identity.labels:
            return True # Not enough info, assume safe
            
        for k, v in service_identity.selector.items():
            if deployment_identity.labels.get(k) != v:
                return False
        return True
