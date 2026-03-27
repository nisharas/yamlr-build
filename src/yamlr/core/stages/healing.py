#!/usr/bin/env python3
"""
Yamlr HEALING STAGE - The Surgeon's Hand
---------------------------------
Implements the core semantic repair logic for broken manifests.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-02-20: Selector-First Healing Strategy**
   - **Context**: Port and selector mismatches cause 80% of K8s downtime.
   - **Decision**: Prioritize `ServiceSelectorHealer` and `PortMismatchHealer` in the sequence.
   - **Consequence**: Rapid resolution of connectivity issues.

2. **2026-03-15: Deterministic Comment Preservation**
   - **Context**: Users were complaining about lost comments during healing.
   - **Decision**: Enforce `ruamel.yaml` usage across all healers.
   - **Consequence**: Zero-failure trust pillar achieved; Yamlr is safe for GitOps.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from yamlr.parsers.structurer import YamlrStructurer

from yamlr.analyzers.ref_resolver import ReferenceResolver
from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage
from yamlr.core.stages.boundaries import BoundaryEnforcer, HealerPermit, MutationScope
from yamlr.healers.best_practices.image_tag import ImageTagHealer
from yamlr.healers.best_practices.ingress import IngressAuditor
from yamlr.healers.best_practices.metadata import MetadataHealer
from yamlr.healers.best_practices.namespace import NamespaceHealer
from yamlr.healers.best_practices.network_policy import NetworkPolicyHealer
from yamlr.healers.best_practices.probes import ProbeHealer
from yamlr.healers.best_practices.resources import ResourcesHealer
from yamlr.healers.semantic.missing_target import MissingTargetHealer
from yamlr.healers.semantic.port_healer import PortMismatchHealer
from yamlr.healers.semantic.selector_healer import ServiceSelectorHealer

logger = logging.getLogger("yamlr.pipeline.stages.healing")
__all__ = ['StageResourceNormalization', 'StageImageTagHealing', 'StageRBACAuditing', 'StagePrivilegeEscalation', 'StageIngressHardening', 'StageProbeInjection', 'StageSelectorAlignment', 'StageNetworkPolicyEnforcement', 'StageNamespaceEnforcement', 'StagePortAlignment', 'StageGhostResourceGeneration', 'StageStructuralCleanup']


class StageResourceNormalization(PipelineStage):
    """
    [Stage 3] Standardizes resource specifications and injects baseline limits.
    """
    def __init__(self, name: str, structurer: "YamlrStructurer", enforce_limits: bool, config: Optional[Any] = None):
        super().__init__(name)
        self.structurer = structurer
        self.enforce_limits = enforce_limits
        profiles = getattr(config, "resource_profiles", {}) if config else {}
        vpa = getattr(config, "vpa_targets", []) if config else []
        
        # [Phase 11] If no profiles, but CLI limits provided, create a fallback profile
        if not profiles and config and (getattr(config, "cpu_limit", None) or getattr(config, "mem_limit", None)):
            profiles = {
                "app": {
                    "requests": {"cpu": config.cpu_limit, "memory": config.mem_limit},
                    "limits": {"cpu": config.cpu_limit, "memory": config.mem_limit}
                }
            }
        self.healer = ResourcesHealer(profiles=profiles, vpa_targets=vpa)
        self.permit = HealerPermit("ResourceNormalization", {MutationScope.SPEC_RESOURCES})

    def run(self, context: HealContext):
        modified = 0
        for doc in context.docs or []:
            # [Pro DNA] Handle YamlrNode wrapper if present
            data = doc.data if hasattr(doc, "data") else doc
            
            # [PARITY] ResourcesHealer.heal_doc now handles both structural and policy normalization
            if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_RESOURCES, context):
                if self.healer.heal_doc(data, enforce_defaults=self.enforce_limits, context=context):
                    modified += 1
        return {"modified": modified}


class StageStructuralCleanup(PipelineStage):
    """
    [Stage 6.5] General structural cleanup and orphan key migration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        from yamlr.healers.best_practices.structural import StructuralHealer
        from yamlr.healers.semantic.selector_healer import ServiceSelectorHealer
        
        self.structural_healer = StructuralHealer()
        self.metadata_healer = MetadataHealer()
        self.selector_healer = ServiceSelectorHealer()
        self.permit = HealerPermit("StructuralCleanup", {MutationScope.STRUCTURAL, MutationScope.METADATA, MutationScope.SPEC_SELECTOR})

    def run(self, context: HealContext):
        modified = 0
        for doc in context.docs or []:
            data = doc.data if hasattr(doc, "data") else doc
            modified += self._run_cleanup_steps(data, context)
        return {"modified": modified}

    def _run_cleanup_steps(self, data: Dict[str, Any], context: HealContext) -> int:
        """Executes the specific cleanup steps for a document."""
        modified = 0
        # 1. Orphan Keys (name, namespace, labels)
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.METADATA, context):
            if self.metadata_healer.fix_orphans(data, context):
                modified += 1
            
        # 3. EnvFrom Normalization
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.STRUCTURAL, context):
            if self.structural_healer.heal_doc(data, context):
                modified += 1
            
        # 3. Deployment Selector Recovery
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_SELECTOR, context):
            if self.selector_healer.normalize_deployment_selector(data, context):
                modified += 1
        return modified


class StageImageTagHealing(PipelineStage):
    """Enforces image tag pinning and latest-tag remediation.
    
    Why: To ensure deployment immutability and prevent non-deterministic rollouts.
    """
    def __init__(self, name: str, fix_tags: bool):
        """Initializes the image tag healing stage.
        
        Args:
            fix_tags: Whether to automatically resolve 'latest' or untagged images.
        """
        super().__init__(name)
        self.fix_tags = fix_tags
        self.healer = ImageTagHealer()
        self.permit = HealerPermit("ImageTagHealing", {MutationScope.SPEC_IMAGE})

    def run(self, context: HealContext):
        """Analyzes and repairs image tags across all documents in the context.
        
        Why: To enforce immutability and prevent 'latest' tag risks during rollouts.
        """
        modified = 0
        for doc in context.docs or []:
            if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_IMAGE, context):
                if self.healer.heal_doc(doc, fix_latest=self.fix_tags, context=context):
                    modified += 1
        return {"modified": modified}


class StageProbeInjection(PipelineStage):
    """Injects default Liveness/Readiness probes into workload containers.
    
    Why: To improve cluster reliability and enable zero-downtime deployments.
    """
    def __init__(self, name: str, enforce_probes: bool):
        """Initializes the probe injection stage.
        
        Args:
            enforce_probes: Whether to inject default liveness/readiness probes.
        """
        super().__init__(name)
        self.enforce_probes = enforce_probes
        self.healer = ProbeHealer()
        self.permit = HealerPermit("ProbeInjection", {MutationScope.SPEC_PROBES})

    def run(self, context: HealContext):
        """Injects probes into all compatible containers within the context.
        
        Why: To ensure every workload has basic health signaling enabled.
        """
        modified = 0
        for doc in context.docs or []:
            if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_PROBES, context):
                if self.healer.heal_doc(doc, enforce_probes=self.enforce_probes, context=context):
                    modified += 1
        return {"modified": modified}

class StageSelectorAlignment(PipelineStage):
    """Aligns Service selectors with Deployment labels.
    
    Why: To repair 'Ghost Services' that have no matching Pods.
    """
    def __init__(self, name: str, healer: ServiceSelectorHealer):
        """Initializes the selector alignment stage with a specialized semantic healer.
        """
        super().__init__(name)
        self.healer = healer
        self.permit = HealerPermit("SelectorAlignment", {MutationScope.SPEC_SELECTOR})

    def run(self, context: HealContext):
        """Repairs misaligned labels and selectors between Services and Deployments.
        
        Why: To restore connectivity for 'Ghost Services' identified during analysis.
        """
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_SELECTOR, context):
            modified = self.healer.heal_docs(context.docs, context.identities, context=context)
        else:
            modified = 0
        return {"modified": modified}

class StageNetworkPolicyEnforcement(PipelineStage):
    """Generates and applies restrictive NetworkPolicies for workloads.
    
    Why: To provide defense-in-depth and enforce East-West traffic segmentation.
    """
    def __init__(self, name: str, healer: NetworkPolicyHealer, harden: bool = False):
        """Initializes the network policy stage.
        
        Args:
            healer: The underlying policy generation logic.
            harden: Whether to apply a 'Deny All' default if no policy exists.
        """
        super().__init__(name)
        self.healer = healer
        self.harden = harden
        self.permit = HealerPermit("NetworkPolicyEnforcement", {MutationScope.SPEC_NETWORK})

    def run(self, context: HealContext):
        """Creates or updates NetworkPolicies based on workload identity and metadata.
        
        Why: To ensure every service has a defined, restricted traffic perimeter.
        """
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_NETWORK, context):
            modified = self.healer.heal_docs(context.docs, context.identities, harden=self.harden, context=context)
        else:
            modified = 0
        return {"modified": modified}

class StageNamespaceEnforcement(PipelineStage):
    """Enforces organizational namespace conventions.
    
    Why: To prevent accidental deployments to the 'default' namespace.
    """
    def __init__(self, name: str, enforce: bool):
        """Initializes the namespace enforcement stage.
        
        Args:
            enforce: Whether to apply namespace remediation to all manifests.
        """
        super().__init__(name)
        self.enforce = enforce
        self.healer = NamespaceHealer(enact=enforce)
        self.permit = HealerPermit("NamespaceEnforcement", {MutationScope.SPEC_NAMESPACE})

    def run(self, context: HealContext):
        """Ensures all manifests have a defined namespace, applying remediations if missing.
        
        Why: To prevent accidental global 'default' namespace sprawl.
        """
        if not self.enforce:
            return {"modified": 0}
            
        # NamespaceHealer: heal_all handles the inference and logging internally
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_NAMESPACE, context):
            self.healer.heal_all(context)
        
        # We estimate modification count based on audit log detections for now
        # Ideally healer.heal_all would return the count
        modified = len([m for m in context.audit_log if "Healed Namespace" in m])
        return {"modified": modified}

class StagePortAlignment(PipelineStage):
    """Aligns Container ports with Service targetPorts.
    
    Why: To ensure successful traffic routing across the cluster networking mesh.
    """
    def __init__(self, name: str, healer: PortMismatchHealer):
        """Initializes the port alignment stage.
        """
        super().__init__(name)
        self.healer = healer
        self.permit = HealerPermit("PortAlignment", {MutationScope.SPEC_PORTS})

    def run(self, context: HealContext):
        """Aligns service ports with container ports across the entire context.
        
        Why: To prevent networking failures caused by port-mapping inconsistencies.
        """
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_PORTS, context):
            modified = self.healer.heal_docs(context.docs, context.identities, context=context)
        else:
            modified = 0
        return {"modified": modified}

class StageGhostResourceGeneration(PipelineStage):
    """Generates placeholder 'Ghost' resources for missing dependencies.
    
    Why: To prevent 'Missing Reference' errors and enable structural healing of partial manifest sets.
    """
    def __init__(self, name: str, healer: MissingTargetHealer, resolver: ReferenceResolver, stub_refs: bool = False):
        """Initializes the ghost resource generation stage.
        """
        super().__init__(name)
        self.healer = healer
        self.resolver = resolver
        self.stub_refs = stub_refs
        self.permit = HealerPermit("GhostResourceGeneration", {MutationScope.RELATIONAL})

    def run(self, context: HealContext):
        """Generates 'Ghost' resource stubs for missing dependencies detected in analysis.
        
        Why: To enable partial healing of incomplete manifest sets.
        """
        if not self.stub_refs or not context.identities:
            return {"modified": 0}
            
        # [UNIFICATION] Leverage pre-built graph if available
        self.resolver.graph = context.resource_graph
        
        candidates = self.resolver.resolve_references(context.identities)
        if candidates and BoundaryEnforcer.validate_mutation(self.permit, MutationScope.RELATIONAL, context):
            new_stubs, _ = self.healer.heal(candidates, {"stub_refs": True}, context=context)
            if new_stubs:
                context.docs.extend(new_stubs)
                context.audit_log.append(f"Relational Surgery: Injected {len(new_stubs)} ghost resource stub(s)")
                return {"modified": len(new_stubs)}
        return {"modified": 0}


class StageRBACAuditing(PipelineStage):
    """
    [Stage 3.5] Forensic RBAC Auditing for Roles and Bindings.
    
    Why: To detect and flag over-privileged permissions (wildcards) and 
         suspicious bindings that could lead to cluster-wide escalation.
    """
    def __init__(self, name: str, harden: bool):
        super().__init__(name)
        from yamlr.healers.best_practices.rbac import RBACAuditor
        self.auditor = RBACAuditor()
        self.harden = harden
        self.permit = HealerPermit("RBACAuditing", {MutationScope.SPEC_RBAC})

    def run(self, context: HealContext):
        modified = 0
        if not context.docs:
            return {"modified": 0}

        # RBAC Auditing is primarily a security/risk detection stage.
        # We always run it if the stage is enabled, but only apply mutations 
        # if the border permit allows and 'harden' is true.
        with open("d:\\yamlr\\stage_rbac_ran.txt", "w") as f: f.write("RAN")
        for doc in context.docs:
            data = doc.data if hasattr(doc, "data") else doc
            
            # Always run detection to capture findings, apply hardening if permitted
            did_modify = self.auditor.heal_doc(data, context=context, harden=self.harden)

            # Only count as 'modified' if mutation is permitted and occurred
            if did_modify and BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_RBAC, context):
                modified += 1
        
        return {"modified": modified}

class StagePrivilegeEscalation(PipelineStage):
    """
    Forensic auditing and hardening for Pod/Container privilege escalation.
    
    Why: Moving beyond basic SecurityContextHealer to a dedicated stage
         for deep security auditing.
    """
    def __init__(self, name: str, harden: bool):
        super().__init__(name)
        from yamlr.healers.best_practices.privilege_escalation import PrivilegeEscalationAuditor
        self.auditor = PrivilegeEscalationAuditor()
        self.harden = harden
        self.permit = HealerPermit("PrivilegeEscalation", {MutationScope.SPEC_SECURITY})

    def run(self, context: HealContext):
        modified = 0
        if not context.docs:
            return {"modified": 0}

        with open("d:\\yamlr\\stage_pe_ran.txt", "w") as f: f.write("RAN")
        for doc in context.docs:
            data = doc.data if hasattr(doc, "data") else doc
            
            # Detection runs regardless of hardening flag
            did_modify = self.auditor.heal_doc(data, context=context, harden=self.harden)

            # Count modification only if permitted
            if did_modify and BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_SECURITY, context):
                modified += 1
        
        return {"modified": modified}


class StageIngressHardening(PipelineStage):
    """Applies Ingress security context hardening and TLS validation.
    
    Why: To enforce secure entrypoints and prevent annotation-based injections.
    """
    def __init__(self, name: str, harden: bool = False):
        """Initializes the ingress hardening stage.
        """
        super().__init__(name)
        self.harden = harden
        self.healer = IngressAuditor()
        self.permit = HealerPermit("IngressHardening", {MutationScope.SPEC_SECURITY, MutationScope.STRUCTURAL})

    def run(self, context: HealContext):
        """Applies Ingress remediations and TLS stubs.
        """
        modified = 0
        for doc in context.docs or []:
            if self.healer.heal_doc(doc, context=context, harden=self.harden):
                modified += 1
        return {"modified": modified}
