"""Tests for FleetBatcher multi-repo GitOps automation."""
import os
import subprocess
import tempfile
from pathlib import Path

from yamlr.core.fleet_batcher import FleetBatcher

DEPLOYMENT_YAML = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: fleet-app
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: app
          image: nginx:1.24
"""


def test_discover_repositories_manifest_file():
    """Verify repository discovery from a manifest text file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo1 = Path(tmpdir) / "repo1"
        repo2 = Path(tmpdir) / "repo2"
        repo1.mkdir()
        repo2.mkdir()

        manifest_file = Path(tmpdir) / "repos.txt"
        manifest_file.write_text(f"{repo1}\n# comment\n{repo2}\n", encoding="utf-8")

        batcher = FleetBatcher()
        repos = batcher.discover_repositories(manifest_file)
        assert len(repos) == 2
        assert repo1.resolve() in repos
        assert repo2.resolve() in repos


def test_discover_repositories_directory():
    """Verify repository discovery by scanning child directories containing .git."""
    with tempfile.TemporaryDirectory() as tmpdir:
        parent = Path(tmpdir)
        repo_a = parent / "app-a"
        repo_b = parent / "app-b"
        non_repo = parent / "not-a-repo"

        repo_a.mkdir()
        (repo_a / ".git").mkdir()

        repo_b.mkdir()
        (repo_b / ".git").mkdir()

        non_repo.mkdir()

        batcher = FleetBatcher()
        repos = batcher.discover_repositories(parent)
        assert len(repos) == 2
        assert repo_a.resolve() in repos
        assert repo_b.resolve() in repos


def test_batch_process_preview():
    """Verify dry-run / preview batching across repositories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "service-a"
        repo.mkdir()
        manifest = repo / "deployment.yaml"
        manifest.write_text(DEPLOYMENT_YAML, encoding="utf-8")

        batcher = FleetBatcher()
        summary = batcher.batch_process(
            repositories=[repo],
            dry_run=True,
            apply=False
        )

        assert summary["total_repositories"] == 1
        assert summary["repositories_with_changes"] == 1
        assert summary["results"][0]["status"] == "PREVIEW_CHANGES"
        assert summary["results"][0]["modified_files_count"] == 1

        # Manifest should remain untouched in preview
        assert "extensions/v1beta1" in manifest.read_text(encoding="utf-8")


def test_batch_process_apply():
    """Verify apply batching writes healed manifests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "service-b"
        repo.mkdir()
        manifest = repo / "deployment.yaml"
        manifest.write_text(DEPLOYMENT_YAML, encoding="utf-8")

        batcher = FleetBatcher()
        summary = batcher.batch_process(
            repositories=[repo],
            dry_run=False,
            apply=True
        )

        assert summary["total_repositories"] == 1
        assert summary["repositories_with_changes"] == 1
        # Should be healed on disk
        healed_content = manifest.read_text(encoding="utf-8")
        assert "apps/v1" in healed_content


def test_generate_report():
    """Verify markdown fleet audit report generation."""
    batcher = FleetBatcher()
    summary = {
        "total_repositories": 2,
        "repositories_with_changes": 1,
        "total_files_modified": 3,
        "total_rules_triggered": 4,
        "apply": False,
        "results": [
            {
                "repo": "payments-service",
                "status": "PREVIEW_CHANGES",
                "modified_files_count": 3,
                "rules_triggered": 4,
                "pr_url": None,
                "error": None
            },
            {
                "repo": "auth-service",
                "status": "CLEAN",
                "modified_files_count": 0,
                "rules_triggered": 0,
                "pr_url": None,
                "error": None
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "fleet-report.md"
        report_md = batcher.generate_report(summary, str(report_path))

        assert "# Yamlr Fleet Remediation Report" in report_md
        assert "payments-service" in report_md
        assert "auth-service" in report_md
        assert report_path.exists()
