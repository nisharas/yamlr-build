//! Kubernetes OpenAPI Property Key Dictionaries.
//!
//! Why: Scoped property dictionaries prevent keyword collision traps across
//! Kubernetes resources. For instance, `port` is valid singular in Probes,
//! Ingress backends, and ServicePort items, while `ports` is valid plural in
//! Service specs and Container specs, and `containerPort` is required in ContainerPort items.
//! Isolating these dictionaries guarantees 100% deterministic, collision-free schema healing.

pub static ROOT_KEYS: &[&str] = &[
    "apiVersion",
    "kind",
    "metadata",
    "spec",
    "status",
    "data",
    "stringData",
    "type",
    "rules",
    "roleRef",
    "subjects",
];

pub static METADATA_KEYS: &[&str] = &[
    "name",
    "namespace",
    "labels",
    "annotations",
    "generation",
    "uid",
    "resourceVersion",
    "creationTimestamp",
    "deletionTimestamp",
    "ownerReferences",
    "finalizers",
];

pub static WORKLOAD_SPEC_KEYS: &[&str] = &[
    "replicas",
    "selector",
    "template",
    "strategy",
    "minReadySeconds",
    "revisionHistoryLimit",
    "paused",
    "progressDeadlineSeconds",
    "serviceName",
    "volumeClaimTemplates",
];

pub static JOB_SPEC_KEYS: &[&str] = &[
    "parallelism",
    "completions",
    "backoffLimit",
    "template",
    "ttlSecondsAfterFinished",
    "activeDeadlineSeconds",
    "selector",
    "suspend",
];

pub static CRONJOB_SPEC_KEYS: &[&str] = &[
    "schedule",
    "jobTemplate",
    "concurrencyPolicy",
    "suspend",
    "successfulJobsHistoryLimit",
    "failedJobsHistoryLimit",
];

pub static WORKLOAD_SELECTOR_KEYS: &[&str] = &[
    "matchLabels",
    "matchExpressions",
];

pub static POD_TEMPLATE_KEYS: &[&str] = &[
    "metadata",
    "spec",
];

pub static POD_SPEC_KEYS: &[&str] = &[
    "containers",
    "initContainers",
    "ephemeralContainers",
    "volumes",
    "restartPolicy",
    "terminationGracePeriodSeconds",
    "dnsPolicy",
    "nodeSelector",
    "serviceAccountName",
    "serviceAccount",
    "hostNetwork",
    "hostPID",
    "hostIPC",
    "securityContext",
    "imagePullSecrets",
    "affinity",
    "tolerations",
    "priorityClassName",
    "automountServiceAccountToken",
    "schedulerName",
    "topologySpreadConstraints",
];

pub static CONTAINER_KEYS: &[&str] = &[
    "name",
    "image",
    "command",
    "args",
    "workingDir",
    "ports",
    "env",
    "envFrom",
    "resources",
    "volumeMounts",
    "volumeDevices",
    "livenessProbe",
    "readinessProbe",
    "startupProbe",
    "lifecycle",
    "terminationMessagePath",
    "terminationMessagePolicy",
    "imagePullPolicy",
    "securityContext",
    "stdin",
    "stdinOnce",
    "tty",
];

pub static CONTAINER_PORT_KEYS: &[&str] = &[
    "containerPort",
    "hostPort",
    "name",
    "protocol",
    "hostIP",
];

pub static VOLUME_MOUNT_KEYS: &[&str] = &[
    "name",
    "mountPath",
    "readOnly",
    "subPath",
    "subPathExpr",
    "mountPropagation",
    "recursiveReadOnly",
];

pub static VOLUME_DEVICE_KEYS: &[&str] = &[
    "name",
    "devicePath",
];

pub static VOLUME_SPEC_KEYS: &[&str] = &[
    "name",
    "configMap",
    "secret",
    "persistentVolumeClaim",
    "emptyDir",
    "hostPath",
    "projected",
    "csi",
    "nfs",
    "downwardAPI",
    "fc",
    "flexVolume",
    "flocker",
    "gcePersistentDisk",
    "gitRepo",
    "glusterfs",
    "iscsi",
    "photonPersistentDisk",
    "portworxVolume",
    "quobyte",
    "rbd",
    "scaleIO",
    "storageos",
    "vsphereVolume",
    "ephemeral",
];

pub static VOLUME_SECRET_KEYS: &[&str] = &[
    "secretName",
    "items",
    "defaultMode",
    "optional",
];

pub static VOLUME_CONFIG_MAP_KEYS: &[&str] = &[
    "name",
    "items",
    "defaultMode",
    "optional",
];

pub static SERVICE_SPEC_KEYS: &[&str] = &[
    "ports",
    "selector",
    "type",
    "clusterIP",
    "clusterIPs",
    "externalIPs",
    "sessionAffinity",
    "loadBalancerIP",
    "loadBalancerSourceRanges",
    "externalName",
    "externalTrafficPolicy",
    "ipFamilies",
    "ipFamilyPolicy",
    "publishNotReadyAddresses",
];

pub static SERVICE_PORT_KEYS: &[&str] = &[
    "name",
    "protocol",
    "port",
    "targetPort",
    "nodePort",
    "appProtocol",
];

pub static SERVICE_REFERENCE_KEYS: &[&str] = &[
    "name",
    "namespace",
    "path",
    "port",
];

pub static INGRESS_SPEC_KEYS: &[&str] = &[
    "rules",
    "tls",
    "ingressClassName",
    "defaultBackend",
];

pub static INGRESS_SERVICE_PORT_KEYS: &[&str] = &[
    "number",
    "name",
];

pub static INGRESS_TLS_KEYS: &[&str] = &[
    "hosts",
    "secretName",
];

pub static HTTP_GET_KEYS: &[&str] = &[
    "path",
    "port",
    "host",
    "scheme",
    "httpHeaders",
];

pub static TCP_SOCKET_KEYS: &[&str] = &[
    "port",
    "host",
];

pub static GRPC_PROBE_KEYS: &[&str] = &[
    "port",
    "service",
];

pub static PROBE_KEYS: &[&str] = &[
    "httpGet",
    "tcpSocket",
    "exec",
    "grpc",
    "initialDelaySeconds",
    "timeoutSeconds",
    "periodSeconds",
    "successThreshold",
    "failureThreshold",
    "terminationGracePeriodSeconds",
];

pub static SECURITY_CONTEXT_KEYS: &[&str] = &[
    "runAsUser",
    "runAsGroup",
    "runAsNonRoot",
    "readOnlyRootFilesystem",
    "privileged",
    "allowPrivilegeEscalation",
    "capabilities",
    "seLinuxOptions",
    "seccompProfile",
];

pub static RESOURCE_KEYS: &[&str] = &[
    "limits",
    "requests",
    "claims",
];

pub static ENV_VAR_KEYS: &[&str] = &[
    "name",
    "value",
    "valueFrom",
];

pub static ENV_FROM_KEYS: &[&str] = &[
    "configMapRef",
    "secretRef",
    "prefix",
];

pub static VALUE_FROM_KEYS: &[&str] = &[
    "configMapKeyRef",
    "secretKeyRef",
    "fieldRef",
    "resourceFieldRef",
];

pub static KEY_REF_KEYS: &[&str] = &[
    "name",
    "key",
    "optional",
];

pub static OBJECT_REF_KEYS: &[&str] = &[
    "name",
    "optional",
];

pub static RESOURCE_FIELD_REF_KEYS: &[&str] = &[
    "containerName",
    "resource",
    "divisor",
];

pub static OBJECT_FIELD_SELECTOR_KEYS: &[&str] = &[
    "apiVersion",
    "fieldPath",
];

pub static RBAC_RULE_KEYS: &[&str] = &[
    "apiGroups",
    "resources",
    "verbs",
    "resourceNames",
    "nonResourceURLs",
];

pub static RBAC_ROLE_REF_KEYS: &[&str] = &[
    "apiGroup",
    "kind",
    "name",
];

pub static RBAC_SUBJECT_KEYS: &[&str] = &[
    "kind",
    "name",
    "namespace",
    "apiGroup",
];

pub static NETWORK_POLICY_SPEC_KEYS: &[&str] = &[
    "podSelector",
    "ingress",
    "egress",
    "policyTypes",
];

pub static NETWORK_POLICY_PEER_KEYS: &[&str] = &[
    "podSelector",
    "namespaceSelector",
    "ipBlock",
];

pub static HPA_SPEC_KEYS: &[&str] = &[
    "scaleTargetRef",
    "minReplicas",
    "maxReplicas",
    "metrics",
    "behavior",
];

pub static HPA_METRIC_KEYS: &[&str] = &[
    "type",
    "resource",
    "pods",
    "object",
    "external",
    "containerResource",
];

pub static HPA_RESOURCE_METRIC_KEYS: &[&str] = &[
    "name",
    "target",
];

pub static HPA_METRIC_TARGET_KEYS: &[&str] = &[
    "type",
    "averageUtilization",
    "averageValue",
    "value",
];

pub static PDB_SPEC_KEYS: &[&str] = &[
    "minAvailable",
    "maxUnavailable",
    "selector",
];
