"""Integration tests for Phase 8: Native Remediation Transaction Engine & GitOps Waves."""
import os
import tarfile
import tempfile
import yamlr_native


def test_native_apply_fix_atomic_and_journal_and_rollback(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = os.path.join(tmpdir, "remediation_journal.jsonl")
        monkeypatch.setenv("YAMLR_JOURNAL_PATH", journal_path)

        target_file = os.path.join(tmpdir, "workload.yaml")
        initial_yaml = (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: web-app\n"
            "spec:\n"
            "  replicas: 1\n"
        )
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(initial_yaml)

        # 1. Apply atomic fix
        success = yamlr_native.native_apply_fix_atomic(
            target_file,
            "spec.replicas",
            "3",
            "Deployment",
            "web-app"
        )
        assert success is True

        with open(target_file, "r", encoding="utf-8") as f:
            updated_content = f.read()
        assert "replicas: 3" in updated_content

        # 2. Inspect journal
        assert os.path.exists(journal_path)

        entries = yamlr_native.native_list_remediations(journal_path)
        assert len(entries) == 1
        tx = entries[0]
        assert tx.file_path == target_file
        assert tx.field_path == "spec.replicas"
        assert tx.new_value == "3"
        assert tx.status == "COMMITTED"
        assert "replicas: 1" in tx.before_snapshot
        assert "replicas: 3" in tx.after_snapshot

        # 3. Rollback remediation
        rollback_ok = yamlr_native.native_rollback_remediation(journal_path, tx.transaction_id)
        assert rollback_ok is True

        with open(target_file, "r", encoding="utf-8") as f:
            restored_content = f.read()
        assert "replicas: 1" in restored_content

        entries_after = yamlr_native.native_list_remediations(journal_path)
        assert len(entries_after) == 2
        assert entries_after[-1].status == "ROLLED_BACK"


def test_native_vault_evidence_generation(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = os.path.join(tmpdir, "remediation_journal.jsonl")
        monkeypatch.setenv("YAMLR_JOURNAL_PATH", journal_path)

        target_file = os.path.join(tmpdir, "config.yaml")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: my-cfg\n")

        yamlr_native.native_apply_fix_atomic(
            target_file,
            "metadata.name",
            "my-cfg-prod",
            "ConfigMap",
            "my-cfg"
        )

        vault_path = os.path.join(tmpdir, "evidence_vault.tar.gz")
        seal_sha256 = yamlr_native.native_vault_evidence(journal_path, vault_path)

        assert os.path.exists(vault_path)
        assert len(seal_sha256) == 64

        # Companion checksum file
        sha_file = f"{vault_path}.sha256"
        assert os.path.exists(sha_file)
        with open(sha_file, "r", encoding="utf-8") as f:
            sha_content = f.read()
        assert seal_sha256 in sha_content

        # Inspect tar contents
        with tarfile.open(vault_path, "r:gz") as tar:
            names = tar.getnames()
            assert "vault-manifest.json" in names
            assert any(n.startswith("transactions/") for n in names)


def test_native_gitops_wave_stamping():
    raw_crd = (
        "apiVersion: apiextensions.k8s.io/v1\n"
        "kind: CustomResourceDefinition\n"
        "metadata:\n"
        "  name: crontabs.stable.example.com\n"
    )
    stamped_crd, changes = yamlr_native.native_stamp_gitops_waves(raw_crd)
    assert 'argocd.argoproj.io/sync-wave: "-5"' in stamped_crd
    assert 'helm.sh/hook-weight: "-5"' in stamped_crd
    assert len(changes) == 2

    raw_workload = (
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: web-server\n"
    )
    stamped_workload, changes_w = yamlr_native.native_stamp_gitops_waves(raw_workload)
    assert 'argocd.argoproj.io/sync-wave: "0"' in stamped_workload
    assert 'helm.sh/hook-weight: "0"' in stamped_workload
    assert len(changes_w) == 2
