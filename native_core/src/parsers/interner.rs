//! Semantic Key Interning Module
//!
//! Why: Kubernetes YAML manifests are dominated by repeated standard keys
//! (`apiVersion`, `kind`, `metadata`, `spec`, `template`, `containers`, `labels`, `image`).
//! By interning known static strings, we eliminate repeated string allocations,
//! reduce memory churn, and allow O(1) pointer identity checks where applicable.

use std::borrow::Cow;

/// Standard static Kubernetes keys interned in read-only data segment.
pub static KNOWN_K8S_KEYS: &[&str] = &[
    "apiVersion",
    "kind",
    "metadata",
    "name",
    "namespace",
    "labels",
    "annotations",
    "ownerReferences",
    "finalizers",
    "creationTimestamp",
    "generateName",
    "uid",
    "resourceVersion",
    "spec",
    "status",
    "template",
    "containers",
    "initContainers",
    "ephemeralContainers",
    "image",
    "imagePullPolicy",
    "command",
    "args",
    "workingDir",
    "ports",
    "containerPort",
    "hostPort",
    "protocol",
    "env",
    "envFrom",
    "value",
    "valueFrom",
    "configMapKeyRef",
    "secretKeyRef",
    "fieldRef",
    "resourceFieldRef",
    "resources",
    "limits",
    "requests",
    "cpu",
    "memory",
    "ephemeral-storage",
    "volumeMounts",
    "mountPath",
    "subPath",
    "readOnly",
    "livenessProbe",
    "readinessProbe",
    "startupProbe",
    "httpGet",
    "tcpSocket",
    "exec",
    "initialDelaySeconds",
    "periodSeconds",
    "timeoutSeconds",
    "failureThreshold",
    "successThreshold",
    "securityContext",
    "privileged",
    "runAsUser",
    "runAsGroup",
    "runAsNonRoot",
    "readOnlyRootFilesystem",
    "allowPrivilegeEscalation",
    "capabilities",
    "add",
    "drop",
    "restartPolicy",
    "serviceAccountName",
    "serviceAccount",
    "nodeSelector",
    "tolerations",
    "affinity",
    "volumes",
    "configMap",
    "secret",
    "persistentVolumeClaim",
    "claimName",
    "emptyDir",
    "hostPath",
    "replicas",
    "selector",
    "matchLabels",
    "matchExpressions",
    "strategy",
    "type",
    "rollingUpdate",
    "maxSurge",
    "maxUnavailable",
    "clusterIP",
    "sessionAffinity",
    "targetPort",
    "ingressClassName",
    "rules",
    "host",
    "http",
    "paths",
    "path",
    "pathType",
    "backend",
    "service",
    "data",
    "stringData",
    "app",
    "version",
    "tier",
    "component",
    "release",
];

/// Returns a static string slice if the key matches a standard Kubernetes key.
///
/// Fast O(1) match using compiler branch jump table.
pub fn intern_k8s_key(key: &str) -> Option<&'static str> {
    match key {
        "apiVersion" => Some("apiVersion"),
        "kind" => Some("kind"),
        "metadata" => Some("metadata"),
        "name" => Some("name"),
        "namespace" => Some("namespace"),
        "labels" => Some("labels"),
        "annotations" => Some("annotations"),
        "ownerReferences" => Some("ownerReferences"),
        "finalizers" => Some("finalizers"),
        "creationTimestamp" => Some("creationTimestamp"),
        "generateName" => Some("generateName"),
        "uid" => Some("uid"),
        "resourceVersion" => Some("resourceVersion"),
        "spec" => Some("spec"),
        "status" => Some("status"),
        "template" => Some("template"),
        "containers" => Some("containers"),
        "initContainers" => Some("initContainers"),
        "ephemeralContainers" => Some("ephemeralContainers"),
        "image" => Some("image"),
        "imagePullPolicy" => Some("imagePullPolicy"),
        "command" => Some("command"),
        "args" => Some("args"),
        "workingDir" => Some("workingDir"),
        "ports" => Some("ports"),
        "containerPort" => Some("containerPort"),
        "hostPort" => Some("hostPort"),
        "protocol" => Some("protocol"),
        "env" => Some("env"),
        "envFrom" => Some("envFrom"),
        "value" => Some("value"),
        "valueFrom" => Some("valueFrom"),
        "configMapKeyRef" => Some("configMapKeyRef"),
        "secretKeyRef" => Some("secretKeyRef"),
        "fieldRef" => Some("fieldRef"),
        "resourceFieldRef" => Some("resourceFieldRef"),
        "resources" => Some("resources"),
        "limits" => Some("limits"),
        "requests" => Some("requests"),
        "cpu" => Some("cpu"),
        "memory" => Some("memory"),
        "ephemeral-storage" => Some("ephemeral-storage"),
        "volumeMounts" => Some("volumeMounts"),
        "mountPath" => Some("mountPath"),
        "subPath" => Some("subPath"),
        "readOnly" => Some("readOnly"),
        "livenessProbe" => Some("livenessProbe"),
        "readinessProbe" => Some("readinessProbe"),
        "startupProbe" => Some("startupProbe"),
        "httpGet" => Some("httpGet"),
        "tcpSocket" => Some("tcpSocket"),
        "exec" => Some("exec"),
        "initialDelaySeconds" => Some("initialDelaySeconds"),
        "periodSeconds" => Some("periodSeconds"),
        "timeoutSeconds" => Some("timeoutSeconds"),
        "failureThreshold" => Some("failureThreshold"),
        "successThreshold" => Some("successThreshold"),
        "securityContext" => Some("securityContext"),
        "privileged" => Some("privileged"),
        "runAsUser" => Some("runAsUser"),
        "runAsGroup" => Some("runAsGroup"),
        "runAsNonRoot" => Some("runAsNonRoot"),
        "readOnlyRootFilesystem" => Some("readOnlyRootFilesystem"),
        "allowPrivilegeEscalation" => Some("allowPrivilegeEscalation"),
        "capabilities" => Some("capabilities"),
        "add" => Some("add"),
        "drop" => Some("drop"),
        "restartPolicy" => Some("restartPolicy"),
        "serviceAccountName" => Some("serviceAccountName"),
        "serviceAccount" => Some("serviceAccount"),
        "nodeSelector" => Some("nodeSelector"),
        "tolerations" => Some("tolerations"),
        "affinity" => Some("affinity"),
        "volumes" => Some("volumes"),
        "configMap" => Some("configMap"),
        "secret" => Some("secret"),
        "persistentVolumeClaim" => Some("persistentVolumeClaim"),
        "claimName" => Some("claimName"),
        "emptyDir" => Some("emptyDir"),
        "hostPath" => Some("hostPath"),
        "replicas" => Some("replicas"),
        "selector" => Some("selector"),
        "matchLabels" => Some("matchLabels"),
        "matchExpressions" => Some("matchExpressions"),
        "strategy" => Some("strategy"),
        "type" => Some("type"),
        "rollingUpdate" => Some("rollingUpdate"),
        "maxSurge" => Some("maxSurge"),
        "maxUnavailable" => Some("maxUnavailable"),
        "clusterIP" => Some("clusterIP"),
        "sessionAffinity" => Some("sessionAffinity"),
        "targetPort" => Some("targetPort"),
        "ingressClassName" => Some("ingressClassName"),
        "rules" => Some("rules"),
        "host" => Some("host"),
        "http" => Some("http"),
        "paths" => Some("paths"),
        "path" => Some("path"),
        "pathType" => Some("pathType"),
        "backend" => Some("backend"),
        "service" => Some("service"),
        "data" => Some("data"),
        "stringData" => Some("stringData"),
        "app" => Some("app"),
        "version" => Some("version"),
        "tier" => Some("tier"),
        "component" => Some("component"),
        "release" => Some("release"),
        _ => None,
    }
}

/// Returns a `Cow<'static, str>` for a key, borrowing if static or allocating if custom.
pub fn compact_key(key: &str) -> Cow<'static, str> {
    if let Some(static_key) = intern_k8s_key(key) {
        Cow::Borrowed(static_key)
    } else {
        Cow::Owned(key.to_string())
    }
}

/// Returns true if the key is a standard Kubernetes API key.
pub fn is_known_k8s_key(key: &str) -> bool {
    intern_k8s_key(key).is_some()
}

/// Fast FNV-1a hash of a key for O(1) comparison in collections.
pub fn k8s_key_fingerprint(key: &str) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    for byte in key.as_bytes() {
        hash ^= *byte as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_intern_k8s_key_core() {
        assert_eq!(intern_k8s_key("apiVersion"), Some("apiVersion"));
        assert_eq!(intern_k8s_key("kind"), Some("kind"));
        assert_eq!(intern_k8s_key("metadata"), Some("metadata"));
        assert_eq!(intern_k8s_key("spec"), Some("spec"));
        assert_eq!(intern_k8s_key("containers"), Some("containers"));
        assert_eq!(intern_k8s_key("customKey123"), None);
    }

    #[test]
    fn test_compact_key_borrowed_vs_owned() {
        let borrowed = compact_key("metadata");
        assert!(matches!(borrowed, Cow::Borrowed(_)));

        let owned = compact_key("myCustomField");
        assert!(matches!(owned, Cow::Owned(_)));
        assert_eq!(owned, "myCustomField");
    }

    #[test]
    fn test_is_known_k8s_key() {
        assert!(is_known_k8s_key("resources"));
        assert!(is_known_k8s_key("limits"));
        assert!(is_known_k8s_key("requests"));
        assert!(!is_known_k8s_key("unknownField_XYZ"));
    }

    #[test]
    fn test_k8s_key_fingerprint_deterministic() {
        let fp1 = k8s_key_fingerprint("containers");
        let fp2 = k8s_key_fingerprint("containers");
        let fp3 = k8s_key_fingerprint("initContainers");
        assert_eq!(fp1, fp2);
        assert_ne!(fp1, fp3);
    }
}
