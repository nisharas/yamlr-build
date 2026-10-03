"""Fleet-Wide Kubernetes API Deprecation Upgrade Stage.

Scans repositories and fleets to identify deprecated Kubernetes API versions and
spec schemas (e.g. Ingress backends, CronJob, HPA) and upgrades them to modern
targets (e.g. v1.25 -> v1.30+) while preserving comments and formatting.
"""
import os
import re
from typing import Any, Dict, List, Tuple

from yamlr.ui.theme import ICON_SUCCESS, console

DEPRECATION_MAP = {
    ("extensions/v1beta1", "Deployment"): "apps/v1",
    ("extensions/v1beta1", "DaemonSet"): "apps/v1",
    ("extensions/v1beta1", "StatefulSet"): "apps/v1",
    ("extensions/v1beta1", "ReplicaSet"): "apps/v1",
    ("apps/v1beta1", "Deployment"): "apps/v1",
    ("apps/v1beta2", "Deployment"): "apps/v1",
    ("extensions/v1beta1", "Ingress"): "networking.k8s.io/v1",
    ("networking.k8s.io/v1beta1", "Ingress"): "networking.k8s.io/v1",
    ("policy/v1beta1", "PodDisruptionBudget"): "policy/v1",
    ("batch/v1beta1", "CronJob"): "batch/v1",
    ("batch/v2alpha1", "CronJob"): "batch/v1",
    ("autoscaling/v2beta1", "HorizontalPodAutoscaler"): "autoscaling/v2",
    ("autoscaling/v2beta2", "HorizontalPodAutoscaler"): "autoscaling/v2",
    ("rbac.authorization.k8s.io/v1beta1", "Role"): "rbac.authorization.k8s.io/v1",
    ("rbac.authorization.k8s.io/v1beta1", "ClusterRole"): "rbac.authorization.k8s.io/v1",
    ("rbac.authorization.k8s.io/v1beta1", "RoleBinding"): "rbac.authorization.k8s.io/v1",
    ("rbac.authorization.k8s.io/v1beta1", "ClusterRoleBinding"): "rbac.authorization.k8s.io/v1",
    ("flowcontrol.apiserver.k8s.io/v1beta1", "FlowSchema"): "flowcontrol.apiserver.k8s.io/v1",
    ("flowcontrol.apiserver.k8s.io/v1beta2", "FlowSchema"): "flowcontrol.apiserver.k8s.io/v1",
}


class DeprecationUpgradeStage:
    """Upgrades deprecated Kubernetes manifests across a workspace or fleet."""

    @staticmethod
    def execute_fleet_upgrade(
        target_path: str = ".",
        target_k8s_version: str = "1.30",
        apply: bool = False
    ) -> List[Dict[str, Any]]:
        """Upgrades all deprecated manifests in target_path.

        Args:
            target_path: File or directory to scan.
            target_k8s_version: Target Kubernetes release (e.g. '1.30').
            apply: Whether to write upgraded manifests to disk.

        Returns:
            List of upgrade records.
        """
        console.print(f"\n[bold cyan][*] Running Fleet Deprecation Upgrade (Target: K8s v{target_k8s_version}) on: {target_path}[/bold cyan]")

        import yamlr_native

        from yamlr import heal_yaml
        from yamlr.core.scanner import _discover_manifests

        manifest_files = _discover_manifests(target_path)
        upgraded_records = []

        for fpath in manifest_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                shards = yamlr_native.native_shard(content)
                if not shards:
                    continue

                identity = yamlr_native.extract_native_identity(shards)
                if not identity:
                    continue

                curr_api = (identity.api_version or "").strip().strip('"\'')
                kind = (identity.kind or "").strip()

                target_api = DEPRECATION_MAP.get((curr_api, kind))
                if target_api:
                    # Execute upgrade using heal_yaml
                    heal_res = heal_yaml(content, k8s_version=target_k8s_version)
                    if heal_res.had_changes:
                        if apply:
                            with open(fpath, "w", encoding="utf-8") as f:
                                f.write(heal_res.healed_yaml)

                        record = {
                            "file": fpath,
                            "kind": kind,
                            "name": identity.name,
                            "old_api": curr_api,
                            "new_api": target_api,
                            "changes": heal_res.changes
                        }
                        upgraded_records.append(record)
                        status_tag = "[bold green][APPLIED][/bold green]" if apply else "[bold yellow][PREVIEW][/bold yellow]"
                        console.print(f"  {status_tag} {fpath}: {kind} migrated {curr_api} -> {target_api}")
            except Exception:
                continue

        console.print(f"\n[bold green]{ICON_SUCCESS} Upgrade Scan Complete: {len(upgraded_records)} manifest(s) ready for modern K8s v{target_k8s_version}[/bold green]\n")
        return upgraded_records
