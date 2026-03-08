"""
Tests for [PRO-12-05]: Cross-Resource Auto-Fix (--fix-refs)

Why: Verifies that:
  1. PortMismatchHealer Strategy A (single port) still works.
  2. PortMismatchHealer Strategy B (named-port fuzzy match) resolves typos.
  3. The ProGate in extract_cli_options() strips fix_refs for OSS users.
"""

import pytest
from unittest.mock import MagicMock
from typing import List

from yamlr.healers.semantic.port_healer import PortMismatchHealer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_identity(kind, name, ns="default", labels=None, container_ports=None):
    """Creates a minimal ManifestIdentity mock for testing."""
    from yamlr.models import ManifestIdentity
    ident = MagicMock(spec=ManifestIdentity)
    ident.kind = kind
    ident.name = name
    ident.namespace = ns
    ident.labels = labels or {}
    ident.container_ports = container_ports or []
    return ident


def _deployment_doc(name, port_num, port_name=None, ns="default", labels=None):
    """Creates a minimal Deployment dict with one named or unnamed container port."""
    port_def = {"containerPort": port_num}
    if port_name:
        port_def["name"] = port_name
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "namespace": ns},
        "spec": {
            "selector": {"matchLabels": labels or {"app": name}},
            "template": {
                "metadata": {"labels": labels or {"app": name}},
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "nginx:1.25",
                            "ports": [port_def],
                        }
                    ]
                },
            },
        },
    }


def _service_doc(name, selector, target_port, port=80, ns="default"):
    """Creates a minimal Service dict targeting the given port."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": name, "namespace": ns},
        "spec": {
            "selector": selector,
            "ports": [{"port": port, "targetPort": target_port}],
        },
    }


# ---------------------------------------------------------------------------
# Unit Tests: PortMismatchHealer
# ---------------------------------------------------------------------------

class TestPortMismatchHealerStrategyA:
    """Strategy A: single container port auto-alignment."""

    def test_single_port_mismatch_is_fixed(self):
        healer = PortMismatchHealer()
        deploy = _deployment_doc("web", port_num=8080, labels={"app": "web"})
        svc = _service_doc("web", selector={"app": "web"}, target_port=80)
        identity = _make_identity(
            "Deployment", "web", labels={"app": "web"}, container_ports=[8080]
        )

        modified = healer.heal_docs([deploy, svc], [identity])

        assert modified == 1
        assert svc["spec"]["ports"][0]["targetPort"] == 8080

    def test_correct_port_is_not_modified(self):
        healer = PortMismatchHealer()
        deploy = _deployment_doc("web", port_num=8080, labels={"app": "web"})
        svc = _service_doc("web", selector={"app": "web"}, target_port=8080)
        identity = _make_identity(
            "Deployment", "web", labels={"app": "web"}, container_ports=[8080]
        )

        modified = healer.heal_docs([deploy, svc], [identity])

        assert modified == 0
        assert svc["spec"]["ports"][0]["targetPort"] == 8080

    def test_no_matching_workload_skips(self):
        healer = PortMismatchHealer()
        svc = _service_doc("orphan-svc", selector={"app": "ghost"}, target_port=99)
        identity = _make_identity(
            "Deployment", "web", labels={"app": "web"}, container_ports=[8080]
        )

        modified = healer.heal_docs([svc], [identity])
        assert modified == 0


class TestPortMismatchHealerStrategyB:
    """Strategy B: named-port fuzzy matching on multi-port workloads."""

    def _multi_port_deployment(self, name, ports, labels=None):
        """Builds a Deployment with multiple named container ports."""
        labels = labels or {"app": name}
        port_defs = [
            {"name": p_name, "containerPort": p_num}
            for p_name, p_num in ports
        ]
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": name, "namespace": "default"},
            "spec": {
                "selector": {"matchLabels": labels},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "containers": [
                            {
                                "name": "app",
                                "image": "nginx:1.25",
                                "ports": port_defs,
                            }
                        ]
                    },
                },
            },
        }

    def test_named_port_typo_is_resolved(self):
        """'http-svc' should fuzzy-match to 'http' and resolve to port 8080."""
        healer = PortMismatchHealer()
        deploy = self._multi_port_deployment(
            "api",
            ports=[("http", 8080), ("metrics", 9090)],
            labels={"app": "api"},
        )
        svc = _service_doc("api", selector={"app": "api"}, target_port="http-svc")

        identity = _make_identity(
            "Deployment", "api", labels={"app": "api"}, container_ports=[8080, 9090]
        )

        modified = healer.heal_docs([deploy, svc], [identity])

        assert modified == 1
        assert svc["spec"]["ports"][0]["targetPort"] == 8080

    def test_low_similarity_is_not_matched(self):
        """A completely different name should NOT be force-matched."""
        healer = PortMismatchHealer()
        deploy = self._multi_port_deployment(
            "api",
            ports=[("http", 8080), ("metrics", 9090)],
            labels={"app": "api"},
        )
        # 'database-backend-rpc' is far from both 'http' and 'metrics'
        svc = _service_doc("api", selector={"app": "api"}, target_port="database-backend-rpc")

        identity = _make_identity(
            "Deployment", "api", labels={"app": "api"}, container_ports=[8080, 9090]
        )

        modified = healer.heal_docs([deploy, svc], [identity])

        # Should NOT modify — no high-confidence match
        assert modified == 0

    def test_exact_named_port_match(self):
        """Exact name match should be resolved via Strategy B (multi-port workload)."""
        healer = PortMismatchHealer()
        deploy = self._multi_port_deployment(
            "api",
            ports=[("http", 8080), ("grpc", 9000)],
            labels={"app": "api"},
        )
        svc = _service_doc("api", selector={"app": "api"}, target_port="grpc")

        identity = _make_identity(
            "Deployment", "api", labels={"app": "api"}, container_ports=[8080, 9000]
        )

        modified = healer.heal_docs([deploy, svc], [identity])

        assert modified == 1
        assert svc["spec"]["ports"][0]["targetPort"] == 9000


# ---------------------------------------------------------------------------
# Unit Tests: Pro Gating
# ---------------------------------------------------------------------------

class TestFixRefsProGating:
    """Verifies --fix-refs is zeroed to False for OSS (non-Pro) users."""

    def _make_args(self, fix_refs=True, **overrides):
        args = MagicMock()
        args.path = ["test.yaml"]
        # Standard flags
        for attr in [
            "kube_version", "max_depth", "ext", "concurrency", "strict", "compact",
            "identity_mode", "summary_only", "verbose", "cpu_limit", "mem_limit",
            "namespace", "health_threshold", "enforce_limits", "enforce_probes",
            "enforce_namespace", "fix_tags", "harden", "stream_to", "fail_on",
            "check_deprecations", "fast", "plain", "pro_preview"
        ]:
            setattr(args, attr, overrides.get(attr, False))
        args.ext = ".yaml,.yml"
        args.cpu_limit = "500m"
        args.mem_limit = "512Mi"
        args.namespace = "default"
        args.health_threshold = 70
        args.max_depth = 10
        args.identity_mode = "infer"
        args.fix_refs = fix_refs
        return args

    def test_fix_refs_disabled_for_oss_users(self, capsys):
        """fix_refs must be zeroed out when is_pro=False."""
        from yamlr.core.entrypoints.base import extract_cli_options

        args = self._make_args(fix_refs=True)
        options = extract_cli_options(args, is_pro=False)

        assert options.fix_refs is False

    def test_fix_refs_enabled_for_pro_users(self):
        """fix_refs must remain True when is_pro=True."""
        from yamlr.core.entrypoints.base import extract_cli_options

        args = self._make_args(fix_refs=True)
        options = extract_cli_options(args, is_pro=True)

        assert options.fix_refs is True

    def test_fix_refs_defaults_to_false(self):
        """fix_refs must default to False when not specified."""
        from yamlr.core.entrypoints.base import extract_cli_options

        args = self._make_args(fix_refs=False)
        options = extract_cli_options(args, is_pro=True)

        assert options.fix_refs is False
