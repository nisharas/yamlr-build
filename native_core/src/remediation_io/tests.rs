#[cfg(test)]
mod unit_tests {
    use crate::models::NativeTelemetry;
    use crate::remediation_io::gitops::{
        calculate_enterprise_gitops_wave, native_stamp_gitops_waves,
    };
    use crate::remediation_io::journal::{
        native_apply_fix_atomic, native_list_remediations, native_rollback_remediation,
    };
    use crate::remediation_io::vault::native_vault_evidence;
    use std::fs;
    use std::path::PathBuf;

    fn get_temp_test_dir(name: &str) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!("yamlr-test-{}-{}", name, uuid::Uuid::new_v4()));
        let _ = fs::create_dir_all(&p);
        p
    }

    #[test]
    fn test_apply_fix_atomic_and_journal_and_rollback() {
        let tmpdir = get_temp_test_dir("atomic-test");
        let manifest_path = tmpdir.join("workload.yaml");
        let journal_path = tmpdir.join("test_journal.jsonl");

        std::env::set_var("YAMLR_JOURNAL_PATH", journal_path.to_str().unwrap());

        let original_yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: payment-api\nspec:\n  replicas: 1\n";
        fs::write(&manifest_path, original_yaml).unwrap();

        // 1. Apply atomic fix
        let success = native_apply_fix_atomic(
            manifest_path.to_str().unwrap().to_string(),
            "spec.replicas".to_string(),
            "3".to_string(),
            Some("Deployment".to_string()),
            Some("payment-api".to_string()),
        )
        .expect("Apply atomic should succeed");

        assert!(success, "Fix should be applied");

        let mutated_yaml = fs::read_to_string(&manifest_path).unwrap();
        assert!(mutated_yaml.contains("replicas: 3"));

        // 2. Inspect journal
        let entries = native_list_remediations(journal_path.to_str().unwrap().to_string())
            .expect("Listing remediations should succeed");
        assert!(!entries.is_empty(), "Journal should have at least 1 entry");

        let entry = entries.last().unwrap();
        assert_eq!(entry.field_path, "spec.replicas");
        assert_eq!(entry.new_value, "3");
        assert_eq!(entry.before_snapshot, original_yaml);
        assert_eq!(entry.status, "COMMITTED");

        let tx_id = entry.transaction_id.clone();

        // 3. Rollback remediation
        let rb_success =
            native_rollback_remediation(journal_path.to_str().unwrap().to_string(), tx_id)
                .expect("Rollback should succeed");
        assert!(rb_success, "Rollback should report success");

        let restored_yaml = fs::read_to_string(&manifest_path).unwrap();
        assert_eq!(
            restored_yaml, original_yaml,
            "Manifest should be restored byte-for-byte"
        );

        // Verify rollback entry appended
        let updated_entries =
            native_list_remediations(journal_path.to_str().unwrap().to_string()).unwrap();
        let last_entry = updated_entries.last().unwrap();
        assert_eq!(last_entry.status, "ROLLED_BACK");

        std::env::remove_var("YAMLR_JOURNAL_PATH");
        let _ = fs::remove_dir_all(&tmpdir);
    }

    #[test]
    fn test_vault_evidence_generation() {
        let tmpdir = get_temp_test_dir("vault-test");
        let journal_path = tmpdir.join("journal.jsonl");
        let vault_output = tmpdir.join("audit-evidence.tar.gz");

        let entry_line = serde_json::to_string(&crate::models::RemediationEntry {
            transaction_id: "tx-demo-123".to_string(),
            timestamp: "2026-09-23T12:00:00Z".to_string(),
            file_path: "d:/test/manifest.yaml".to_string(),
            resource_key: "Deployment/web".to_string(),
            field_path: "spec.replicas".to_string(),
            previous_value: Some("1".to_string()),
            new_value: "3".to_string(),
            before_snapshot: "replicas: 1\n".to_string(),
            after_snapshot: "replicas: 3\n".to_string(),
            status: "COMMITTED".to_string(),
        })
        .unwrap();

        fs::write(&journal_path, format!("{}\n", entry_line)).unwrap();

        let checksum = native_vault_evidence(
            journal_path.to_str().unwrap().to_string(),
            vault_output.to_str().unwrap().to_string(),
        )
        .expect("Vault generation should succeed");

        assert!(!checksum.is_empty(), "Checksum must be generated");
        assert!(vault_output.exists(), "Vault tar.gz must be created");

        let companion_checksum_path = format!("{}.sha256", vault_output.to_str().unwrap());
        assert!(
            std::path::Path::new(&companion_checksum_path).exists(),
            "Companion sha256 must exist"
        );

        let _ = fs::remove_dir_all(&tmpdir);
    }

    #[test]
    fn test_7_tier_gitops_wave_stamping() {
        assert_eq!(
            calculate_enterprise_gitops_wave("Namespace", "production"),
            -5
        );
        assert_eq!(
            calculate_enterprise_gitops_wave("CustomResourceDefinition", "vaults.corp.io"),
            -5
        );

        assert_eq!(
            calculate_enterprise_gitops_wave("ConfigMap", "app-config"),
            -3
        );
        assert_eq!(calculate_enterprise_gitops_wave("Secret", "db-creds"), -3);
        assert_eq!(
            calculate_enterprise_gitops_wave("ClusterRole", "view-all"),
            -3
        );

        assert_eq!(
            calculate_enterprise_gitops_wave("PersistentVolumeClaim", "data-pvc"),
            -2
        );
        assert_eq!(
            calculate_enterprise_gitops_wave("StorageClass", "fast-ssd"),
            -2
        );

        assert_eq!(
            calculate_enterprise_gitops_wave("Deployment", "frontend"),
            0
        );
        assert_eq!(
            calculate_enterprise_gitops_wave("StatefulSet", "redis-cluster"),
            0
        );

        assert_eq!(
            calculate_enterprise_gitops_wave("Service", "frontend-svc"),
            2
        );
        assert_eq!(calculate_enterprise_gitops_wave("Ingress", "public-gw"), 2);

        assert_eq!(
            calculate_enterprise_gitops_wave("HorizontalPodAutoscaler", "frontend-hpa"),
            3
        );
        assert_eq!(
            calculate_enterprise_gitops_wave("NetworkPolicy", "default-deny"),
            3
        );

        assert_eq!(calculate_enterprise_gitops_wave("Job", "db-migrate"), 5);
        assert_eq!(
            calculate_enterprise_gitops_wave("CronJob", "daily-backup"),
            5
        );
    }

    #[test]
    fn test_native_stamp_gitops_waves_manifest() {
        let shards = crate::sharder::native_shard(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: app-env\ndata:\n  ENV: prod\n",
        );
        let mut manifest = crate::structurer::native_structurize(shards);
        let mut telemetry = NativeTelemetry::default();

        let changes = native_stamp_gitops_waves(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty(), "Should record GitOps changes");

        let argo_wave = manifest
            .root
            .find_annotation("argocd.argoproj.io/sync-wave")
            .expect("Argo wave must exist");
        assert_eq!(argo_wave, "\"-3\"");

        let helm_weight = manifest
            .root
            .find_annotation("helm.sh/hook-weight")
            .expect("Helm weight must exist");
        assert_eq!(helm_weight, "\"-3\"");
    }
}
