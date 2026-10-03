#[cfg(test)]
mod unit_tests {
    use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
    use crate::security::hardening::native_harden_security_context;
    use crate::security::licensing::native_get_machine_id;
    use crate::security::signature::{
        extract_manifest_signature, native_sign_manifest, native_verify_manifest,
        sign_manifest_hmac, strip_manifest_signatures, verify_manifest_hmac,
    };

    #[test]
    fn test_machine_id_is_available() {
        let machine_id = native_get_machine_id();
        assert!(!machine_id.is_empty(), "Machine ID should not be empty");
    }

    #[test]
    fn test_hmac_manifest_signing_and_verification() {
        let manifest = r#"apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: finance
spec:
  replicas: 3
"#;
        let secret_key = "corp-enterprise-hmac-key-999";
        let signed = sign_manifest_hmac(manifest, secret_key);

        assert!(signed.contains("yamlr.dev/signature:"));
        assert!(signed.contains("yamlr.dev/signed-at:"));

        let is_valid = verify_manifest_hmac(&signed, secret_key);
        assert!(is_valid, "Valid manifest signature should verify");

        let wrong_key_valid = verify_manifest_hmac(&signed, "different-key");
        assert!(!wrong_key_valid, "Verification with wrong key should fail");

        // Tampering with manifest content
        let tampered = signed.replace("replicas: 3", "replicas: 99");
        let is_tampered_valid = verify_manifest_hmac(&tampered, secret_key);
        assert!(
            !is_tampered_valid,
            "Tampered manifest must fail verification"
        );
    }

    #[test]
    fn test_native_sign_and_verify_manifest_facade() {
        let manifest = r#"apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  ports:
    - port: 80
"#;
        let secret = "my-secret-token";
        let signed = native_sign_manifest(manifest, secret);
        assert!(signed.contains("yamlr.dev/signature:"));

        let ok = native_verify_manifest(&signed, secret, None);
        assert!(ok);

        let fail = native_verify_manifest(&signed, "wrong-secret", None);
        assert!(!fail);
    }

    #[test]
    fn test_strip_and_extract_manifest_signatures() {
        let signed = r#"apiVersion: v1
kind: Pod
metadata:
  name: demo
  annotations:
    yamlr.io/signature: "abcdef0123456789"
    yamlr.io/signed-at: "2026-09-23T12:00:00Z"
spec:
  containers:
    - name: app
"#;
        let sig = extract_manifest_signature(signed);
        assert_eq!(sig, Some("abcdef0123456789".to_string()));

        let stripped = strip_manifest_signatures(signed);
        assert!(!stripped.contains("yamlr.io/signature:"));
        assert!(!stripped.contains("yamlr.io/signed-at:"));
        assert!(stripped.contains("name: demo"));
    }

    #[test]
    fn test_harden_security_context_pod_and_containers() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    indent: 0,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![
                        SemanticNode {
                            key: "hostNetwork".to_string(),
                            value: Some("true".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: Vec::new(),
                        },
                        SemanticNode {
                            key: "containers".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "name".to_string(),
                                        value: Some("api-server".to_string()),
                                        indent: 6,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    },
                                    SemanticNode {
                                        key: "ports".to_string(),
                                        value: None,
                                        indent: 6,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    },
                                ],
                            }],
                        },
                    ],
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = native_harden_security_context(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty(), "Changes should be recorded");

        let spec = manifest.root.find_node("spec").unwrap();

        // 1. Host isolation
        assert_eq!(spec.find_value("hostNetwork"), Some("false".to_string()));

        // 2. Pod securityContext
        let pod_sec = spec
            .find_node("securityContext")
            .expect("pod securityContext should exist");
        assert_eq!(pod_sec.find_value("runAsNonRoot"), Some("true".to_string()));
        assert_eq!(pod_sec.find_value("runAsUser"), Some("10001".to_string()));
        assert_eq!(pod_sec.find_value("runAsGroup"), Some("10001".to_string()));
        assert_eq!(pod_sec.find_value("fsGroup"), Some("10001".to_string()));
        let seccomp = pod_sec
            .find_node("seccompProfile")
            .expect("seccompProfile should exist");
        assert_eq!(
            seccomp.find_value("type"),
            Some("RuntimeDefault".to_string())
        );

        // 3. Container securityContext
        let containers = spec.find_node("containers").unwrap();
        let api_container = &containers.children[0];
        let c_sec = api_container
            .find_node("securityContext")
            .expect("container securityContext should exist");
        assert_eq!(
            c_sec.find_value("allowPrivilegeEscalation"),
            Some("false".to_string())
        );
        assert_eq!(
            c_sec.find_value("readOnlyRootFilesystem"),
            Some("true".to_string())
        );

        let caps = c_sec
            .find_node("capabilities")
            .expect("capabilities should exist");
        let drop_node = caps
            .find_node("drop")
            .expect("drop capabilities should exist");
        assert_eq!(drop_node.children[0].value, Some("ALL".to_string()));

        // 4. Volume Mount Auto-Fix: /tmp and /var/run because container has ports
        let vm = api_container
            .find_node("volumeMounts")
            .expect("volumeMounts should be injected");
        let mount_paths: Vec<String> = vm
            .children
            .iter()
            .filter_map(|c| c.find_value("mountPath"))
            .collect();
        assert!(mount_paths.contains(&"/tmp".to_string()));
        assert!(mount_paths.contains(&"/var/run".to_string()));

        let vols = spec
            .find_node("volumes")
            .expect("volumes should be injected");
        let vol_names: Vec<String> = vols
            .children
            .iter()
            .filter_map(|v| v.find_value("name"))
            .collect();
        assert!(vol_names.contains(&"yamlr-tmp-dir".to_string()));
        assert!(vol_names.contains(&"yamlr-run-dir".to_string()));
    }
}
