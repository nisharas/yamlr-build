"""Policy Ingestion Stage for OPA Gatekeeper and Kyverno violations.

Parses external violation reports from Open Policy Agent (Gatekeeper) and Kyverno,
maps policy findings to Yamlr healing stages, and executes surgical auto-repair.
"""
import json
import os
from typing import Any, Dict, List, Tuple

from yamlr.ui.theme import ICON_SUCCESS, console


class PolicyIngestionStage:
    """Ingests OPA Gatekeeper and Kyverno reports to auto-repair targeted manifests."""

    @staticmethod
    def ingest_and_heal(
        report_path: str,
        target_dir: str = ".",
        report_type: str = "opa",
        apply: bool = False
    ) -> List[Dict[str, Any]]:
        """Parses report, finds matching files in target_dir, and applies repairs.

        Args:
            report_path: Path to OPA or Kyverno JSON report.
            target_dir: Workspace root containing Kubernetes manifests.
            report_type: "opa" or "kyverno".
            apply: Whether to write repairs to disk.

        Returns:
            List of remediation summaries.
        """
        if not os.path.exists(report_path):
            console.print(f"[bold red][!] Report file not found: {report_path}[/bold red]")
            return []

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        violations = []
        if report_type == "opa":
            violations = PolicyIngestionStage._parse_opa(data)
        elif report_type == "kyverno":
            violations = PolicyIngestionStage._parse_kyverno(data)

        console.print(f"\n[bold cyan][*] Ingested {len(violations)} {report_type.upper()} policy violation(s)[/bold cyan]")

        import yamlr_native

        from yamlr import heal_yaml
        from yamlr.core.scanner import _discover_manifests

        manifest_files = _discover_manifests(target_dir)
        results = []

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

                # Check if this file matches any violation
                matched_violations = [
                    v for v in violations
                    if v.get("kind", "").lower() == identity.kind.lower()
                    and (not v.get("name") or v.get("name").lower() == identity.name.lower())
                ]

                if matched_violations:
                    heal_res = heal_yaml(content)
                    if heal_res.had_changes:
                        if apply:
                            with open(fpath, "w", encoding="utf-8") as f:
                                f.write(heal_res.healed_yaml)
                        action_summary = {
                            "file": fpath,
                            "kind": identity.kind,
                            "name": identity.name,
                            "policies_addressed": [v.get("policy") for v in matched_violations],
                            "fixes_applied": heal_res.changes
                        }
                        results.append(action_summary)
                        status_tag = "[bold green][APPLIED][/bold green]" if apply else "[bold yellow][PREVIEW][/bold yellow]"
                        console.print(f"  {status_tag} {fpath} ({len(heal_res.changes)} fixes applied for {len(matched_violations)} policy violations)")
            except Exception:
                continue

        return results

    @staticmethod
    def _parse_opa(data: Any) -> List[Dict[str, Any]]:
        """Extracts violations from OPA Gatekeeper JSON."""
        violations = []
        # Support both {"violations": [...]} and standard Gatekeeper items array
        items = data.get("violations", data.get("items", [])) if isinstance(data, dict) else data
        for item in items:
            policy = item.get("constraint", item.get("rule", "OPA-Constraint"))
            resource = item.get("resource", {})
            kind = resource.get("kind", item.get("kind", ""))
            name = resource.get("name", item.get("name", ""))
            msg = item.get("message", "")
            violations.append({"policy": policy, "kind": kind, "name": name, "message": msg})
        return violations

    @staticmethod
    def _parse_kyverno(data: Any) -> List[Dict[str, Any]]:
        """Extracts violations from Kyverno PolicyReport JSON."""
        violations = []
        results = data.get("results", []) if isinstance(data, dict) else []
        for r in results:
            policy = r.get("policy", r.get("rule", "Kyverno-Policy"))
            for res in r.get("resources", [{}]):
                kind = res.get("kind", "")
                name = res.get("name", "")
                msg = r.get("message", "")
                violations.append({"policy": policy, "kind": kind, "name": name, "message": msg})
        return violations
