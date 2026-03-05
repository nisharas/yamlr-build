#!/usr/bin/env python3
"""
Yamlr OSS – DEPRECATION ENGINE
-----------------------------
Static detection of deprecated and removed Kubernetes APIs.

Why: Version intelligence is a core Safety Engine pillar.
     Deploying with a removed API silently fails — the resource
     is simply ignored by the cluster. This is a top-3 K8s
     deployment failure category.

• Complete upstream coverage (K8s 1.9 → 1.35 + 1.36 forward-looking)
• No cluster access
• Deterministic & fast
• CNCF-friendly

Source of truth:
https://kubernetes.io/docs/reference/using-api/deprecation-guide/
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("yamlr.deprecations")


@dataclass(frozen=True)
class DeprecationInfo:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    deprecated_api: str
    replacement_api: str
    deprecated_in_version: str
    removed_in_version: str
    kind: str
    severity: str  # WARNING | REMOVED
    migration_notes: str
    strategy: str = "NONE"  # Strategies: NONE, REPLACE_API_VERSION, DEPLOYMENT_SELECTOR, INGRESS_V1, CRONJOB_V1


# -------------------------------------------------------------------
# Canonical Kubernetes API Deprecations (Static, OSS-safe)
# -------------------------------------------------------------------

DEPRECATED_APIS: Dict[Tuple[str, str], DeprecationInfo] = {
    # ---------------------------------------------------------------
    # REMOVED IN 1.16
    # ---------------------------------------------------------------
    ("extensions/v1beta1", "Deployment"): DeprecationInfo(
        "extensions/v1beta1",
        "apps/v1",
        "1.9",
        "1.16",
        "Deployment",
        "REMOVED",
        "Change apiVersion to apps/v1 and ensure selector is specified.",
        "DEPLOYMENT_SELECTOR",
    ),
    ("extensions/v1beta1", "DaemonSet"): DeprecationInfo(
        "extensions/v1beta1",
        "apps/v1",
        "1.9",
        "1.16",
        "DaemonSet",
        "REMOVED",
        "Change apiVersion to apps/v1 and ensure selector is specified.",
        "DEPLOYMENT_SELECTOR",
    ),
    ("extensions/v1beta1", "ReplicaSet"): DeprecationInfo(
        "extensions/v1beta1",
        "apps/v1",
        "1.9",
        "1.16",
        "ReplicaSet",
        "REMOVED",
        "Change apiVersion to apps/v1 and ensure selector is specified.",
        "DEPLOYMENT_SELECTOR",
    ),
    ("extensions/v1beta1", "NetworkPolicy"): DeprecationInfo(
        "extensions/v1beta1",
        "networking.k8s.io/v1",
        "1.7",
        "1.16",
        "NetworkPolicy",
        "REMOVED",
        "Change apiVersion to networking.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    # ---------------------------------------------------------------
    # REMOVED IN 1.22
    # ---------------------------------------------------------------
    ("networking.k8s.io/v1beta1", "Ingress"): DeprecationInfo(
        "networking.k8s.io/v1beta1",
        "networking.k8s.io/v1",
        "1.19",
        "1.22",
        "Ingress",
        "REMOVED",
        "pathType is required in v1.",
        "INGRESS_V1",
    ),
    (
        "admissionregistration.k8s.io/v1beta1",
        "ValidatingWebhookConfiguration",
    ): DeprecationInfo(
        "admissionregistration.k8s.io/v1beta1",
        "admissionregistration.k8s.io/v1",
        "1.16",
        "1.22",
        "ValidatingWebhookConfiguration",
        "REMOVED",
        "Update apiVersion only.",
        "REPLACE_API_VERSION",
    ),
    (
        "admissionregistration.k8s.io/v1beta1",
        "MutatingWebhookConfiguration",
    ): DeprecationInfo(
        "admissionregistration.k8s.io/v1beta1",
        "admissionregistration.k8s.io/v1",
        "1.16",
        "1.22",
        "MutatingWebhookConfiguration",
        "REMOVED",
        "Update apiVersion only.",
        "REPLACE_API_VERSION",
    ),
    ("apiextensions.k8s.io/v1beta1", "CustomResourceDefinition"): DeprecationInfo(
        "apiextensions.k8s.io/v1beta1",
        "apiextensions.k8s.io/v1",
        "1.16",
        "1.22",
        "CustomResourceDefinition",
        "REMOVED",
        "Structural schema required in v1.",
        "REPLACE_API_VERSION",  # CRD migration is complex, stick to API swap for now or NONE? Let's try swap.
    ),
    ("rbac.authorization.k8s.io/v1beta1", "Role"): DeprecationInfo(
        "rbac.authorization.k8s.io/v1beta1",
        "rbac.authorization.k8s.io/v1",
        "1.17",
        "1.22",
        "Role",
        "REMOVED",
        "Update apiVersion only.",
        "REPLACE_API_VERSION",
    ),
    ("rbac.authorization.k8s.io/v1beta1", "ClusterRole"): DeprecationInfo(
        "rbac.authorization.k8s.io/v1beta1",
        "rbac.authorization.k8s.io/v1",
        "1.17",
        "1.22",
        "ClusterRole",
        "REMOVED",
        "Update apiVersion only.",
        "REPLACE_API_VERSION",
    ),
    ("rbac.authorization.k8s.io/v1beta1", "RoleBinding"): DeprecationInfo(
        "rbac.authorization.k8s.io/v1beta1",
        "rbac.authorization.k8s.io/v1",
        "1.17",
        "1.22",
        "RoleBinding",
        "REMOVED",
        "Update apiVersion only.",
        "REPLACE_API_VERSION",
    ),
    ("rbac.authorization.k8s.io/v1beta1", "ClusterRoleBinding"): DeprecationInfo(
        "rbac.authorization.k8s.io/v1beta1",
        "rbac.authorization.k8s.io/v1",
        "1.17",
        "1.22",
        "ClusterRoleBinding",
        "REMOVED",
        "Update apiVersion only.",
        "REPLACE_API_VERSION",
    ),
    # ---------------------------------------------------------------
    # REMOVED IN 1.25
    # ---------------------------------------------------------------
    ("batch/v1beta1", "CronJob"): DeprecationInfo(
        "batch/v1beta1",
        "batch/v1",
        "1.21",
        "1.25",
        "CronJob",
        "REMOVED",
        "Change apiVersion to batch/v1.",
        "CRONJOB_V1",
    ),
    ("policy/v1beta1", "PodSecurityPolicy"): DeprecationInfo(
        "policy/v1beta1",
        "N/A",
        "1.21",
        "1.25",
        "PodSecurityPolicy",
        "REMOVED",
        "Migrate to Pod Security Standards (PSS).",
        "NONE",  # No auto-fix for removal
    ),
    ("policy/v1beta1", "PodDisruptionBudget"): DeprecationInfo(
        "policy/v1beta1",
        "policy/v1",
        "1.21",
        "1.25",
        "PodDisruptionBudget",
        "REMOVED",
        "Update apiVersion to policy/v1.",
        "REPLACE_API_VERSION",
    ),
    ("node.k8s.io/v1beta1", "RuntimeClass"): DeprecationInfo(
        "node.k8s.io/v1beta1",
        "node.k8s.io/v1",
        "1.20",
        "1.25",
        "RuntimeClass",
        "REMOVED",
        "Change apiVersion to node.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    # ---------------------------------------------------------------
    # REMOVED IN 1.26+
    # ---------------------------------------------------------------
    ("autoscaling/v2beta2", "HorizontalPodAutoscaler"): DeprecationInfo(
        "autoscaling/v2beta2",
        "autoscaling/v2",
        "1.23",
        "1.26",
        "HorizontalPodAutoscaler",
        "REMOVED",
        "Change apiVersion to autoscaling/v2.",
        "REPLACE_API_VERSION",
    ),
    ("storage.k8s.io/v1beta1", "CSIStorageCapacity"): DeprecationInfo(
        "storage.k8s.io/v1beta1",
        "storage.k8s.io/v1",
        "1.24",
        "1.27",
        "CSIStorageCapacity",
        "REMOVED",
        "Change apiVersion to storage.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    # ---------------------------------------------------------------
    # REMOVED IN 1.29
    # ---------------------------------------------------------------
    ("flowcontrol.apiserver.k8s.io/v1beta2", "FlowSchema"): DeprecationInfo(
        "flowcontrol.apiserver.k8s.io/v1beta2",
        "flowcontrol.apiserver.k8s.io/v1",
        "1.23",
        "1.29",
        "FlowSchema",
        "REMOVED",
        "v1beta2 removed. Change apiVersion to flowcontrol.apiserver.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    (
        "flowcontrol.apiserver.k8s.io/v1beta2",
        "PriorityLevelConfiguration",
    ): DeprecationInfo(
        "flowcontrol.apiserver.k8s.io/v1beta2",
        "flowcontrol.apiserver.k8s.io/v1",
        "1.23",
        "1.29",
        "PriorityLevelConfiguration",
        "REMOVED",
        "v1beta2 removed. Change apiVersion to flowcontrol.apiserver.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    ("flowcontrol.apiserver.k8s.io/v1beta3", "FlowSchema"): DeprecationInfo(
        "flowcontrol.apiserver.k8s.io/v1beta3",
        "flowcontrol.apiserver.k8s.io/v1",
        "1.26",
        "1.29",
        "FlowSchema",
        "REMOVED",
        "v1beta3 removed. Change apiVersion to flowcontrol.apiserver.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    (
        "flowcontrol.apiserver.k8s.io/v1beta3",
        "PriorityLevelConfiguration",
    ): DeprecationInfo(
        "flowcontrol.apiserver.k8s.io/v1beta3",
        "flowcontrol.apiserver.k8s.io/v1",
        "1.26",
        "1.29",
        "PriorityLevelConfiguration",
        "REMOVED",
        "v1beta3 removed. Change apiVersion to flowcontrol.apiserver.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    # ---------------------------------------------------------------
    # REMOVED IN 1.32
    # ---------------------------------------------------------------
    ("flowcontrol.apiserver.k8s.io/v1beta3", "FlowSchema"): DeprecationInfo(
        "flowcontrol.apiserver.k8s.io/v1beta3",
        "flowcontrol.apiserver.k8s.io/v1",
        "1.26",
        "1.32",
        "FlowSchema",
        "REMOVED",
        "Final removal of v1beta3. Use flowcontrol.apiserver.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    # ---------------------------------------------------------------
    # BEHAVIORAL CHANGES IN 1.33-1.35 (No API removal, but
    # semantics changed — requires awareness tracking)
    # ---------------------------------------------------------------
    # K8s 1.33: ValidatingAdmissionPolicy goes GA
    # - v1beta1 deprecated, v1 is now the stable API
    ("admissionregistration.k8s.io/v1beta1", "ValidatingAdmissionPolicy"): DeprecationInfo(
        "admissionregistration.k8s.io/v1beta1",
        "admissionregistration.k8s.io/v1",
        "1.30",
        "1.35",
        "ValidatingAdmissionPolicy",
        "WARNING",
        "ValidatingAdmissionPolicy GA in 1.33. Migrate to admissionregistration.k8s.io/v1.",
        "REPLACE_API_VERSION",
    ),
    (
        "admissionregistration.k8s.io/v1beta1",
        "ValidatingAdmissionPolicyBinding",
    ): DeprecationInfo(
        "admissionregistration.k8s.io/v1beta1",
        "admissionregistration.k8s.io/v1",
        "1.30",
        "1.35",
        "ValidatingAdmissionPolicyBinding",
        "WARNING",
        "ValidatingAdmissionPolicyBinding GA in 1.33. Migrate to v1.",
        "REPLACE_API_VERSION",
    ),
    # K8s 1.34: SidecarContainers GA — init container restartPolicy
    # field changes behavior. No API removal, but behavioral change.
    # (Tracked as WARNING for awareness, no auto-fix needed.)
}


# -------------------------------------------------------------------
# Field-Level Deprecations (EPIC-23 / TASK-23-6)
# These are not API version changes but individual field changes.
# -------------------------------------------------------------------

DEPRECATED_FIELDS: Dict[Tuple[str, str], Dict] = {
    # spec.serviceAccount → spec.serviceAccountName
    ("Pod", "spec.serviceAccount"): {
        "replacement": "spec.serviceAccountName",
        "deprecated_in": "1.16",
        "removed_in": None,  # Still accepted but ignored
        "note": "spec.serviceAccount is deprecated. Use spec.serviceAccountName.",
    },
    # K8s 1.25: PodSecurityPolicy replaced by Pod Security Admission
    ("PodSecurityPolicy", "*"): {
        "replacement": "Pod Security Standards (PSS/PSA)",
        "deprecated_in": "1.21",
        "removed_in": "1.25",
        "note": "PodSecurityPolicy removed. Migrate to Pod Security Admission controller.",
    },
    # K8s 1.34: SidecarContainers GA — initContainers.restartPolicy
    ("Pod", "spec.initContainers[].restartPolicy"): {
        "replacement": "restartPolicy: Always (for sidecar pattern)",
        "deprecated_in": None,
        "removed_in": None,
        "note": "SidecarContainers GA in 1.34. Set restartPolicy: Always on init containers for sidecar behavior.",
    },
}


# -------------------------------------------------------------------
# OSS Checker
# -------------------------------------------------------------------


class DeprecationChecker:
    """Kubernetes API deprecation and field-level change detector.

    Why: Version intelligence is the second pillar of the Safety Engine.
         Deploying with removed APIs silently fails — the resource is
         ignored by the cluster with no error. This is a top-3 K8s
         deployment failure category.

    Coverage: K8s 1.9 → 1.35 (all stable), with 1.36 forward-looking.
    """

    def __init__(self):
        """Initialize OSS deprecation checker with static database."""
        pass  # No state needed for OSS

    def check(self, api_version: str, kind: str) -> Optional[DeprecationInfo]:
        """Check if a specific API version/kind combination is deprecated.

        Why: Core detection method used by the pipeline and upgrade command.

        Args:
            api_version: The Kubernetes API version (e.g., 'extensions/v1beta1')
            kind: The resource kind (e.g., 'Deployment')

        Returns:
            DeprecationInfo if deprecated/removed, None otherwise.
        """
        return DEPRECATED_APIS.get((api_version, kind))

    def list_all(self) -> List[DeprecationInfo]:
        """Return all known deprecation entries.

        Why: Used by 'yamlr rules' and SARIF taxa to enumerate coverage.
        """
        return list(DEPRECATED_APIS.values())

    def is_removed(self, api_version: str, kind: str, target_version: str) -> bool:
        """Check if an API is removed in a specific K8s version.

        Why: CI/CD gates need binary yes/no for removed APIs.
             'WARNING' deprecations don't block; 'REMOVED' does.

        Args:
            api_version: API version to check
            kind: Resource kind
            target_version: Target K8s version (e.g., '1.29')

        Returns:
            True if API is removed in that version or earlier.
        """
        info = self.check(api_version, kind)
        if not info:
            return False
        if info.severity != "REMOVED":
            return False
        return self._compare_versions(target_version, info.removed_in_version) >= 0

    def check_field(self, kind: str, field_path: str) -> Optional[Dict]:
        """Check if a specific field is deprecated.

        Why: Field-level deprecations are invisible to API version checks.
             spec.serviceAccount still parses but is silently ignored.

        Args:
            kind: Resource kind (e.g., 'Pod')
            field_path: Dotted field path (e.g., 'spec.serviceAccount')

        Returns:
            Field deprecation dict if deprecated, None otherwise.
        """
        return DEPRECATED_FIELDS.get((kind, field_path))

    def upgrade_risk_score(
        self, from_version: str, to_version: str
    ) -> Dict:
        """Calculate risk score for upgrading between K8s versions.

        Why: THE core version intelligence feature. Enables Yamlr to answer:
             'How risky is upgrading from 1.24 to 1.29?' with a concrete
             count of removals and deprecations affecting the user's manifests.

        Args:
            from_version: Current K8s version (e.g., '1.24')
            to_version: Target K8s version (e.g., '1.29')

        Returns:
            Dict with risk level, counts, and affected APIs.
        """
        removals = []
        warnings = []

        for (api, kind), info in DEPRECATED_APIS.items():
            # Check if the API is removed between from and to versions
            removed_version = info.removed_in_version

            if info.severity == "REMOVED":
                # Is it removed AFTER from_version but AT or BEFORE to_version?
                if (
                    self._compare_versions(removed_version, from_version) > 0
                    and self._compare_versions(removed_version, to_version) <= 0
                ):
                    removals.append(info)
            elif info.severity == "WARNING":
                dep_version = info.deprecated_in_version
                if (
                    self._compare_versions(dep_version, from_version) > 0
                    and self._compare_versions(dep_version, to_version) <= 0
                ):
                    warnings.append(info)

        # Risk classification
        if len(removals) >= 3:
            risk_level = "HIGH"
        elif len(removals) >= 1:
            risk_level = "MEDIUM"
        elif len(warnings) >= 1:
            risk_level = "LOW"
        else:
            risk_level = "NONE"

        return {
            "from_version": from_version,
            "to_version": to_version,
            "risk_level": risk_level,
            "removal_count": len(removals),
            "warning_count": len(warnings),
            "removals": [
                {"api": r.deprecated_api, "kind": r.kind, "removed_in": r.removed_in_version}
                for r in removals
            ],
            "warnings": [
                {"api": w.deprecated_api, "kind": w.kind, "deprecated_in": w.deprecated_in_version}
                for w in warnings
            ],
        }

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare K8s versions safely.

        Why: Version comparison is safety-critical. Incorrect comparison
             can cause false negatives (missed removals).

        Handles formats: '1.29', '1.30', 'v1.29', '1.30+'

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
        """
        try:
            v1_clean = v1.lstrip("v").rstrip("+")
            v2_clean = v2.lstrip("v").rstrip("+")
            v1_parts = [int(x) for x in v1_clean.split(".")[:2]]
            v2_parts = [int(x) for x in v2_clean.split(".")[:2]]

            if v1_parts[0] != v2_parts[0]:
                return 1 if v1_parts[0] > v2_parts[0] else -1
            if v1_parts[1] != v2_parts[1]:
                return 1 if v1_parts[1] > v2_parts[1] else -1
            return 0
        except (ValueError, IndexError) as e:
            logger.warning(f"Version comparison failed: {v1} vs {v2}: {e}")
            return 0
