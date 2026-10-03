"""Enterprise Multi-Repo GitOps PR Batching Engine.

Why: Platform engineering teams manage hundreds of GitOps repositories.
When Kubernetes APIs are deprecated or enterprise hygiene standards change,
manually opening PRs across 100+ repositories takes weeks. FleetBatcher
automates discovery, lossless manifest healing, branch creation, atomic
commits, and PR submission across enterprise fleets.
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from yamlr import heal_yaml
from yamlr.core.scanner import _discover_manifests

logger = logging.getLogger(__name__)


class FleetBatcher:
    """Orchestrates cross-repository manifest remediation and PR generation."""

    def __init__(self, k8s_version: str = "1.30"):
        """Initializes the fleet batcher with the target Kubernetes version."""
        self.k8s_version = k8s_version

    def discover_repositories(self, target: Union[str, Path]) -> List[Path]:
        """Discovers git repositories from a target path, manifest file, or directory.

        Args:
            target: Path to repos manifest (txt, json, yaml), a single repo,
                    or a parent directory containing multiple repos.

        Returns:
            List of unique Path objects pointing to valid repository directories.
        """
        target_path = Path(target).resolve()
        if not target_path.exists():
            return []

        # Case 1: Target is a file containing list of repositories
        if target_path.is_file():
            repos = []
            content = target_path.read_text(encoding="utf-8").strip()
            if target_path.suffix in [".json"]:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for item in data:
                            p = Path(item).resolve()
                            if p.is_dir():
                                repos.append(p)
                except Exception as e:
                    logger.error("Failed to parse JSON repo manifest: %s", e)
            else:
                for line in content.splitlines():
                    cleaned = line.strip()
                    if cleaned and not cleaned.startswith("#"):
                        p = Path(cleaned).resolve()
                        if p.is_dir():
                            repos.append(p)
            return list(dict.fromkeys(repos))

        # Case 2: Target is itself a git repository
        if (target_path / ".git").exists():
            return [target_path]

        # Case 3: Target is a directory containing child git repositories
        discovered = []
        try:
            for child in target_path.iterdir():
                if child.is_dir() and (child / ".git").exists():
                    discovered.append(child)
        except OSError as e:
            logger.error("Failed to iterate directory %s: %s", target_path, e)

        return sorted(discovered)

    def heal_repository(
        self, repo_path: Path, apply: bool = False
    ) -> List[Dict[str, Any]]:
        """Scans and optionally heals all manifests within a repository.

        Args:
            repo_path: Path to repository root.
            apply: Whether to overwrite files on disk.

        Returns:
            List of modified file records.
        """
        modified_files = []
        files = _discover_manifests(str(repo_path))

        for fpath in files:
            try:
                content = Path(fpath).read_text(encoding="utf-8")
                res = heal_yaml(content, k8s_version=self.k8s_version)
                if res.had_changes:
                    if apply:
                        Path(fpath).write_text(res.healed_yaml, encoding="utf-8")
                    modified_files.append({
                        "path": fpath,
                        "changes": res.changes
                    })
            except Exception as e:
                logger.warning("Error processing manifest %s: %s", fpath, e)

        return modified_files

    def batch_process(
        self,
        repositories: List[Union[str, Path]],
        branch: str = "yamlr/fleet-upgrade",
        title: str = "fix(k8s): automated fleet manifest remediation",
        apply: bool = False,
        create_pr: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Runs manifest healing and GitOps branch/PR batching across repositories.

        Args:
            repositories: List of repository directories to process.
            branch: Target branch name for Git commit and PR.
            title: Commit and PR title.
            apply: Whether to write healed manifests to disk.
            create_pr: Whether to attempt PR creation via CLI (gh / glab).
            dry_run: Force preview-only execution.

        Returns:
            Dictionary containing fleet execution metrics and per-repo results.
        """
        should_apply = apply and not dry_run
        results: List[Dict[str, Any]] = []
        total_files_modified = 0
        total_rules_triggered = 0

        for repo in repositories:
            repo_path = Path(repo).resolve()
            repo_name = repo_path.name

            diff_files = self.heal_repository(repo_path, apply=should_apply)
            rules_in_repo = sum(len(f["changes"]) for f in diff_files)
            total_files_modified += len(diff_files)
            total_rules_triggered += rules_in_repo

            repo_status = "CLEAN"
            pr_url = None
            error_msg = None

            if diff_files:
                if not should_apply:
                    repo_status = "PREVIEW_CHANGES"
                else:
                    repo_status = "HEALED"
                    git_ok, git_err = self._create_git_commit(
                        repo_path, branch, title, diff_files
                    )
                    if not git_ok:
                        error_msg = git_err
                        repo_status = "GIT_ERROR"
                    elif create_pr:
                        pr_ok, pr_res = self._create_pull_request(
                            repo_path, branch, title
                        )
                        if pr_ok:
                            repo_status = "PR_CREATED"
                            pr_url = pr_res
                        else:
                            repo_status = "COMMITTED_NO_PR"
                            error_msg = pr_res

            results.append({
                "repo": repo_name,
                "path": str(repo_path),
                "status": repo_status,
                "modified_files_count": len(diff_files),
                "rules_triggered": rules_in_repo,
                "pr_url": pr_url,
                "error": error_msg
            })

        return {
            "total_repositories": len(repositories),
            "repositories_with_changes": sum(1 for r in results if r["modified_files_count"] > 0),
            "total_files_modified": total_files_modified,
            "total_rules_triggered": total_rules_triggered,
            "apply": should_apply,
            "results": results
        }

    def _create_git_commit(
        self, repo_path: Path, branch: str, title: str, modified_files: list
    ) -> tuple[bool, Optional[str]]:
        """Creates an atomic branch and commit for healed files."""
        try:
            subprocess.run(
                ["git", "checkout", "-B", branch],
                cwd=repo_path, check=True, capture_output=True, text=True
            )
            for f in modified_files:
                subprocess.run(
                    ["git", "add", f["path"]],
                    cwd=repo_path, check=True, capture_output=True, text=True
                )
            commit_body = f"{title}\n\nAutomated remediation by Yamlr.\nModified files:\n"
            for f in modified_files:
                commit_body += f"- {Path(f['path']).name} ({len(f['changes'])} issue(s) fixed)\n"

            subprocess.run(
                ["git", "commit", "-m", commit_body],
                cwd=repo_path, check=True, capture_output=True, text=True
            )
            return True, None
        except Exception as e:
            return False, str(e)

    def _create_pull_request(
        self, repo_path: Path, branch: str, title: str
    ) -> tuple[bool, str]:
        """Attempts to push branch and open a PR via gh or glab CLI."""
        try:
            push_res = subprocess.run(
                ["git", "push", "-u", "origin", branch],
                cwd=repo_path, capture_output=True, text=True
            )
            if push_res.returncode != 0:
                return False, f"Git push failed: {push_res.stderr.strip()}"

            gh_res = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", "Automated fleet remediation by Yamlr.", "--head", branch],
                cwd=repo_path, capture_output=True, text=True
            )
            if gh_res.returncode == 0:
                return True, gh_res.stdout.strip()

            gl_res = subprocess.run(
                ["glab", "mr", "create", "--title", title, "--description", "Automated fleet remediation by Yamlr.", "--source-branch", branch],
                cwd=repo_path, capture_output=True, text=True
            )
            if gl_res.returncode == 0:
                return True, gl_res.stdout.strip()

            return False, "Neither gh nor glab CLI available to create PR; branch pushed successfully."
        except Exception as e:
            return False, str(e)

    def generate_report(
        self, summary: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """Generates a clean markdown fleet audit report."""
        lines = [
            "# Yamlr Fleet Remediation Report",
            "",
            f"- **Repositories Scanned**: {summary['total_repositories']}",
            f"- **Repositories with Upgrades**: {summary['repositories_with_changes']}",
            f"- **Total Files Modified**: {summary['total_files_modified']}",
            f"- **Total Rules Triggered**: {summary['total_rules_triggered']}",
            f"- **Mode**: {'Applied' if summary['apply'] else 'Preview (Dry Run)'}",
            "",
            "| Repository | Status | Files Modified | Rules Triggered | Detail / PR |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        for r in summary["results"]:
            detail = r.get("pr_url") or r.get("error") or "-"
            lines.append(
                f"| `{r['repo']}` | **{r['status']}** | {r['modified_files_count']} | {r['rules_triggered']} | {detail} |"
            )

        lines.append("")
        report_text = "\n".join(lines)

        if output_path:
            out = Path(output_path).resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report_text, encoding="utf-8")

        return report_text
