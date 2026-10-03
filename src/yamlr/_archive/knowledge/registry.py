"""Knowledge registry providing technical rationale and concepts for K8s manifest safety."""

from typing import Any, Dict, Optional


class KnowledgeRegistry:
    """The authoritative technical repository for Yamlr concepts and K8s safety."""

    DATA = {
        "HEAL": {
            "title": "Autonomous Remediation (Heal)",
            "definition": "The process of programmatically correcting manifest violations while preserving non-structural data.",
            "rationale": "Manual remediation is error-prone and scales poorly. Yamlr uses a 'Surgical AST' approach to apply fixes without stripping developer comments or formatting.",
            "impact": "Reduces MTTR (Mean Time To Repair) for security violations by 90% in large-scale CI/CD pipelines.",
            "example": "yamlr heal manifests/ --apply --dry-run"
        },
        "DISCOVERY": {
            "title": "Relational Topology Mapping",
            "definition": "A forensic scan that identifies implicit links between disparate K8s resources (e.g., Services to Deployments via Selectors).",
            "rationale": "Manifests are often treated as isolated files. Yamlr treats them as a 'Connected Graph', allowing it to detect 'Ghost Services' or 'Dangling Selectors'.",
            "impact": "Prevents 'Broken Link' production outages where a Service exists but has no healthy backing pods.",
            "example": "yamlr scan . --dna"
        },
        "Y-101": {
            "title": "Violation: Privileged Container",
            "definition": "The container has 'securityContext.privileged: true' enabled.",
            "rationale": "Privileged containers have access to all devices on the host and can bypass most isolation layers. This is a Tier 1 security risk.",
            "impact": "Yamlr can auto-heal this by injecting 'privileged: false' or removing the block entirely.",
            "example": "spec:\n  containers:\n  - name: exploit\n    securityContext:\n      privileged: true # VIOLATION"
        },
        "DNA": {
            "title": "Semantic DNA Integrity",
            "definition": "A cryptographic-grade fingerprint of a manifest's semantic meaning, ignoring whitespace and comments.",
            "rationale": "Standard MD5/SHA hashes change if you add a comment. DNA hashes only change if the *behavior* of the manifest changes.",
            "impact": "Enables 'Pure GitOps' by allowing teams to reformat code without triggering unnecessary deployment rollouts.",
            "example": "yamlr dna deployment.yaml"
        }
    }

    @classmethod
    def lookup(cls, key: str) -> Optional[Dict[str, str]]:
        """Deep lookup with case-insensitive normalization."""
        return cls.DATA.get(key.upper())
