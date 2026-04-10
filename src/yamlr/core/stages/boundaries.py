#!/usr/bin/env python3
"""
MUTATION BOUNDARIES - Healer Safety Contract
--------------------------------------------
Defines the allowed scopes for manifest mutations, providing
a 'Safety-First' boundary for healers.

Why: To prevent 'God Objects' and unintended side-effects during healing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Set


class MutationScope(str, Enum):
    """
    Defines the areas of a manifest that can be mutated.
    """

    METADATA = "metadata"
    SPEC_RESOURCES = "spec.template.spec.containers.resources"
    SPEC_SECURITY = "spec.template.spec.securityContext"
    SPEC_PROBES = "spec.template.spec.containers.probes"
    SPEC_IMAGE = "spec.template.spec.containers.image"
    SPEC_NETWORK = "spec.networkPolicy"
    SPEC_SELECTOR = "spec.selector"
    SPEC_PORTS = "spec.ports"
    SPEC_NAMESPACE = "metadata.namespace"
    SPEC_STORAGE = "spec.volumes,spec.volumeClaimTemplates"
    SPEC_RBAC = "rules,subjects"  # Role/ClusterRole/Binding
    RELATIONAL = "relational"  # Cross-resource stubs
    STRUCTURAL = "structural"  # Indentation, layout recovery


@dataclass(frozen=True)
class HealerPermit:
    """
    Defines what a specific healer instance is allowed to touch.
    Locked (Frozen) at runtime to prevent permission escalation.
    """

    name: str
    allowed_scopes: Set[MutationScope] = field(default_factory=set)
    audit_only: bool = False

    def is_allowed(self, scope: MutationScope) -> bool:
        """Checks if a specific scope is within the permit."""
        return scope in self.allowed_scopes or MutationScope.STRUCTURAL in self.allowed_scopes


class BoundaryEnforcer:
    """
    Enforces mutation boundaries during pipeline execution.
    """

    @staticmethod
    def validate_mutation(permit: HealerPermit, scope: MutationScope, context: any) -> bool:
        """Validates a mutation against the healer's permit and records forensics."""
        # [Phase 16] Forensics Snapshot 1.0: Record mutation trail
        if hasattr(context, "mutation_trace"):
             context.mutation_trace.append({
                 "healer": permit.name,
                 "scope": scope.value,
                 "allowed": permit.is_allowed(scope),
                 "ts_seq": getattr(context, "mutation_count", 0)
             })

        # [Phase 10] Circuit Breaker: Prevent infinite rule loops
        if hasattr(context, "mutation_count"):
            context.mutation_count += 1
            if context.mutation_count > 50:
                msg = f"🛑 CIRCUIT BREAKER TRIPPED: Rule Engine recursion limit (50) reached for '{permit.name}'."
                if hasattr(context, "errors"):
                    context.errors.append(msg)
                raise RuntimeError(msg)

        if not permit.is_allowed(scope):
            msg = f"🛡️ BOUNDARY VIOLATION: Healer '{permit.name}' attempted to mutate '{scope.value}' without permit."
            if hasattr(context, "audit_log"):
                context.audit_log.append(msg)
            return False
        return True
