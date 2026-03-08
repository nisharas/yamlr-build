#!/usr/bin/env python3
"""
Yamlr HEALING STAGES - Stages 6.7 - 6.12
---------------------------------------
Implements specific remediation logic for K8s best practices.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import List, Dict, Any

from yamlr.core.stages.base import PipelineStage
from yamlr.core.context import HealContext
from yamlr.healers.best_practices.resources import ResourcesHealer
from yamlr.healers.best_practices.image_tag import ImageTagHealer
from yamlr.healers.best_practices.security import SecurityContextHealer
from yamlr.healers.best_practices.probes import ProbeHealer
from yamlr.healers.semantic.selector_healer import ServiceSelectorHealer
from yamlr.healers.best_practices.network_policy import NetworkPolicyHealer
from yamlr.healers.best_practices.metadata import MetadataHealer
from yamlr.healers.semantic.port_healer import PortMismatchHealer
from yamlr.healers.semantic.missing_target import MissingTargetHealer
from yamlr.analyzers.ref_resolver import ReferenceResolver

logger = logging.getLogger("yamlr.pipeline.stages.healing")

class StageResourceNormalization(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, structurer: Any, enforce_limits: bool):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Resource Normalization")
        self.structurer = structurer
        self.enforce_limits = enforce_limits
        self.healer = ResourcesHealer()

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = 0
        for doc in context.docs or []:
            if self.healer.heal_doc(doc, structurer=self.structurer, enforce_defaults=self.enforce_limits):
                modified += 1
        context.audit_log.append(f"Stage 6.7: Normalized {modified} resource spec(s)")
        return {"modified": modified}

class StageImageTagHealing(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, fix_tags: bool):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Image Tag Healing")
        self.fix_tags = fix_tags
        self.healer = ImageTagHealer()

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = 0
        for doc in context.docs or []:
            if self.healer.heal_doc(doc, fix_latest=self.fix_tags):
                modified += 1
        return {"modified": modified}

class StageSecurityHardening(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, harden: bool):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Security Hardening")
        self.harden = harden
        self.healer = SecurityContextHealer()

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = 0
        for doc in context.docs or []:
            if self.healer.heal_doc(doc, harden=self.harden):
                modified += 1
        return {"modified": modified}

class StageProbeInjection(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, enforce_probes: bool):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Probe Injection")
        self.enforce_probes = enforce_probes
        self.healer = ProbeHealer()

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = 0
        for doc in context.docs or []:
            if self.healer.heal_doc(doc, enforce_probes=self.enforce_probes):
                modified += 1
        return {"modified": modified}

class StageSelectorAlignment(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, healer: ServiceSelectorHealer):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Selector Alignment")
        self.healer = healer

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = self.healer.heal_docs(context.docs, context.identities)
        return {"modified": modified}

class StageNetworkPolicyEnforcement(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, healer: NetworkPolicyHealer, harden: bool = False):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Network Policy Enforcement")
        self.healer = healer
        self.harden = harden

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = self.healer.heal_docs(context.docs, context.identities, harden=self.harden)
        return {"modified": modified}

class StageNamespaceEnforcement(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, enforce: bool):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Namespace Enforcement")
        self.enforce = enforce
        self.healer = MetadataHealer()

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.enforce:
            return {"modified": 0}
            
        modified = 0
        for doc in context.docs or []:
            if self.healer.heal_namespace(doc, default_namespace=context.default_namespace):
                modified += 1
        return {"modified": modified}

class StagePortAlignment(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, healer: PortMismatchHealer):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Port Alignment")
        self.healer = healer

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        modified = self.healer.heal_docs(context.docs, context.identities)
        return {"modified": modified}

class StageGhostResourceGeneration(PipelineStage):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    def __init__(self, healer: MissingTargetHealer, resolver: ReferenceResolver, stub_refs: bool = False):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage Ghost Resource Generation")
        self.healer = healer
        self.resolver = resolver
        self.stub_refs = stub_refs

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if not self.stub_refs or not context.identities:
            return {"modified": 0}
            
        candidates = self.resolver.resolve_references(context.identities)
        if candidates:
            new_stubs, _ = self.healer.heal(candidates, {"stub_refs": True})
            if new_stubs:
                context.docs.extend(new_stubs)
                context.audit_log.append(f"Relational Surgery: Injected {len(new_stubs)} ghost resource stub(s)")
                return {"modified": len(new_stubs)}
        return {"modified": 0}
