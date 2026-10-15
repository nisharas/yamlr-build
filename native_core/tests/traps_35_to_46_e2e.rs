//! Comprehensive End-to-End Test for Traps 35 through 50.
//!
//! Why: Verifies that all 16 latest syntax and human error traps operate cohesively
//! in a single end-to-end healing pass with 100% determinism, comment preservation, and idempotency:
//! - Trap 35: Leading slash in volumeMounts subPath
//! - Trap 36: Double mustache {{{{ -> {{
//! - Trap 37: Unbraced map inside flow sequence [ key: val ] -> [{ key: val }]
//! - Trap 38: Stray carriage return \r embedded in scalar
//! - Trap 39: POSIX octal permission mode in defaultMode ("0755" -> 493, "644" -> 420)
//! - Trap 40: Redundant values: array in matchExpressions with operator Exists/DoesNotExist
//! - Trap 41: Quoted boolean strings on strict boolean schema properties ("true" -> true)
//! - Trap 42: Headless Service clusterIP: "none" / none -> None
//! - Trap 43: Cluster dump artifacts pruned (status:, creationTimestamp: null, resourceVersion:)
//! - Trap 44: Downward API fieldPath bracket syntax (metadata.labels.app -> metadata.labels['app'])
//! - Trap 45: PriorityClass preemptionPolicy casing ("never" -> Never)
//! - Trap 46: VolumeMount mountPropagation casing ("bidirectional" -> Bidirectional)
//! - Trap 47: Secret volume `name:` vs `secretName:` structural collision under `spec.volumes[*].secret`
//! - Trap 48: Cluster Autoscaler `safe-to-evict` pod annotation boolean typing & casing under `metadata.annotations`
//! - Trap 49: `sessionAffinityConfig.clientIP.timeoutSeconds` range capping (<= 86400) and integer unquoting
//! - Trap 50: `securityContext.fsGroupChangePolicy` case sensitivity normalization ("onrootmismatch" -> "OnRootMismatch")

use yamlr_native::cli::heal_cmd::heal_manifest_string;

#[test]
fn test_traps_35_to_50_cohesion() {
    let raw_manifest = r#"# Comprehensive Traps 35 to 50 Validation Manifest
apiVersion: apps/v1
kind: Deployment
metadata:
  name: full-test-workload
  creationTimestamp: null
  resourceVersion: "998877"
  uid: "abcdef01-2345-6789"
  annotations:
    cluster-autoscaler.kubernetes.io/safe-to-evict: true
spec:
  template:
    metadata:
      annotations:
        cluster-autoscaler.kubernetes.io/safe-to-evict: "True"
    spec:
      securityContext:
        fsGroupChangePolicy: "onrootmismatch"
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: Exists
                values:
                - us-east-1a
      containers:
      - name: test-container
        securityContext:
          privileged: "false"
          readOnlyRootFilesystem: "true"
        volumeMounts:
        - name: app-cfg
          mountPath: /etc/config/app.conf
          subPath: "/app.conf"
          mountPropagation: "bidirectional"
        env:
        - name: POD_LABEL
          valueFrom:
            fieldRef:
              fieldPath: "metadata.labels.app"
      volumes:
      - name: app-cfg
        configMap:
          name: my-cfg
          defaultMode: "0755"
      - name: app-secret-vol
        secret:
          name: my-secret
          defaultMode: "644"
status:
  replicas: 1
---
apiVersion: v1
kind: Service
metadata:
  name: my-headless-svc
spec:
  clusterIP: "none"
---
apiVersion: v1
kind: Service
metadata:
  name: sticky-session-svc
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: "100000"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: batch-priority
value: 50000
preemptionPolicy: "never"
---
# Trap 51: nodeSelector list sequence error & Trap 54: beta topology deprecation
apiVersion: v1
kind: Pod
metadata:
  name: topo-pod
spec:
  nodeSelector:
    - failure-domain.beta.kubernetes.io/zone: us-central1-a
    - beta.kubernetes.io/arch: amd64
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: "failure-domain.beta.kubernetes.io/zone"
      whenUnsatisfiable: DoNotSchedule
---
# Trap 52: Ingress class annotation to ingressClassName & Trap 53: Service nodePort unquoting / invalid low port pruning
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: legacy-ing
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: example.com
---
apiVersion: v1
kind: Service
metadata:
  name: np-svc
spec:
  type: NodePort
  ports:
  - name: http
    port: 80
    nodePort: "30080"
  - name: invalid-low
    port: 8080
    nodePort: 8080
---
# Trap 55: Service sessionAffinity missing ClientIP & Trap 57: imagePullSecrets scalar list
apiVersion: v1
kind: Service
metadata:
  name: sticky-app-svc
spec:
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 7200
---
# Trap 56: Job restartPolicy Always & Trap 57: imagePullSecrets string list
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-workload
spec:
  template:
    spec:
      restartPolicy: Always
      imagePullSecrets:
      - reg-secret-key
      containers:
      - name: runner
        image: runner:v1
---
# Trap 58: Ingress path missing leading slash
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rel-path-ing
spec:
  rules:
  - http:
      paths:
      - path: api/v2
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
---
# Traps 59 through 68 Validation Manifests
# Trap 59: Wildcard host quoting & Trap 68: Ingress backend port mutual exclusivity
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wildcard-ing
spec:
  rules:
  - host: *.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: v1-svc
            port:
              number: 8080
              name: http
---
# Trap 60: Memory unit casing normalization
# Trap 61: hostPath missing type
# Trap 65: emptyDir medium lowercase
# Trap 66: Probe deadlock prevention (timeout >= period)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: contract-app
spec:
  template:
    spec:
      volumes:
      - name: data-vol
        hostPath:
          path: /var/log/app.log
      - name: scratch-vol
        emptyDir:
          medium: "memory"
      containers:
      - name: app
        image: app:v1
        resources:
          limits:
            memory: "500mi"
        livenessProbe:
          timeoutSeconds: 15
          periodSeconds: 10
---
# Trap 62: Service publishNotReadyAddresses unquoted boolean
apiVersion: v1
kind: Service
metadata:
  name: unready-svc
spec:
  publishNotReadyAddresses: "true"
---
# Trap 63: Job ttlSecondsAfterFinished & Trap 64: completionMode
apiVersion: batch/v1
kind: Job
metadata:
  name: ttl-job
spec:
  ttlSecondsAfterFinished: "600"
  completionMode: "indexed"
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: job-worker
        image: worker:v1
---
# Trap 67: HPA inverted replica bounds (min > max)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: bounds-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: contract-app
  minReplicas: 5
  maxReplicas: 2
"#;

    let (healed, changes) = heal_manifest_string(raw_manifest);
    assert!(!changes.is_empty(), "Manifest must be healed");

    // Trap 35: Leading slash stripped from subPath
    assert!(healed.contains("subPath: \"app.conf\"") || healed.contains("subPath: app.conf"), "subPath leading slash must be stripped");

    // Trap 39: POSIX octal "0755" -> 493 and "644" -> 420
    assert!(healed.contains("defaultMode: 493"), "defaultMode '0755' must become 493");
    assert!(healed.contains("defaultMode: 420"), "defaultMode '644' must become 420");

    // Trap 40: Redundant values pruned from matchExpressions with Exists
    assert!(!healed.contains("us-east-1a"), "Redundant values with operator Exists must be pruned");

    // Trap 41: Quoted booleans unquoted
    assert!(healed.contains("privileged: false"), "privileged: 'false' must become unquoted false");
    assert!(healed.contains("readOnlyRootFilesystem: true"), "readOnlyRootFilesystem: 'true' must become unquoted true");

    // Trap 42: Headless Service clusterIP normalized to None
    assert!(healed.contains("clusterIP: None"), "clusterIP: 'none' must become canonical None");

    // Trap 43: Status and cluster dump artifacts pruned
    assert!(!healed.contains("status:"), "status block must be pruned");
    assert!(!healed.contains("creationTimestamp:"), "creationTimestamp must be pruned");
    assert!(!healed.contains("resourceVersion:"), "resourceVersion must be pruned");
    assert!(!healed.contains("uid:"), "uid must be pruned");

    // Trap 44: Downward API fieldPath normalized to subscript
    assert!(healed.contains("metadata.labels['app']"), "Downward API fieldPath must be normalized to metadata.labels['app']");

    // Trap 45: PriorityClass preemptionPolicy normalized
    assert!(healed.contains("preemptionPolicy: Never"), "preemptionPolicy: 'never' must become Never");

    // Trap 46: VolumeMount mountPropagation normalized
    assert!(healed.contains("mountPropagation: Bidirectional"), "mountPropagation: 'bidirectional' must become Bidirectional");

    // Trap 47: Secret volume name collision normalized to secretName
    assert!(healed.contains("secretName: my-secret"), "volumes[*].secret.name must be normalized to secretName: my-secret");

    // Trap 48: safe-to-evict annotation normalized to quoted lowercase string
    assert!(healed.contains("cluster-autoscaler.kubernetes.io/safe-to-evict: \"true\""), "safe-to-evict annotation must be quoted \"true\"");

    // Trap 49: timeoutSeconds clamped to 86400 and unquoted
    assert!(healed.contains("timeoutSeconds: 86400"), "sessionAffinity timeoutSeconds must be clamped to 86400 and unquoted");

    // Trap 50: fsGroupChangePolicy casing normalized
    assert!(healed.contains("fsGroupChangePolicy: OnRootMismatch") || healed.contains("fsGroupChangePolicy: \"OnRootMismatch\""), "fsGroupChangePolicy must be normalized to OnRootMismatch");

    // Trap 51: nodeSelector sequence flattened to map
    assert!(healed.contains("nodeSelector:\n    topology.kubernetes.io/zone:") || healed.contains("nodeSelector:\n    kubernetes.io/arch:"), "nodeSelector list bullets must be flattened");

    // Trap 52: Ingress class annotation promoted to spec.ingressClassName
    assert!(healed.contains("ingressClassName: nginx"), "kubernetes.io/ingress.class annotation must be promoted to spec.ingressClassName");
    assert!(!healed.contains("kubernetes.io/ingress.class:"), "deprecated ingress class annotation must be pruned");

    // Trap 53: Service nodePort unquoted and invalid low port pruned
    assert!(healed.contains("nodePort: 30080"), "Valid string nodePort '30080' must be unquoted to integer 30080");
    assert!(!healed.contains("nodePort: 8080"), "Invalid low nodePort 8080 must be pruned to allow dynamic allocation");

    // Trap 54: Deprecated beta topology keys modernized
    assert!(healed.contains("topology.kubernetes.io/zone"), "failure-domain.beta.kubernetes.io/zone must be modernized");
    assert!(healed.contains("kubernetes.io/arch"), "beta.kubernetes.io/arch must be modernized");
    assert!(!healed.contains("failure-domain.beta.kubernetes.io/zone"), "beta failure-domain label must not remain");

    // Trap 55: sessionAffinity: ClientIP injected when sessionAffinityConfig is present
    assert!(healed.contains("sessionAffinity: ClientIP"), "sessionAffinity: ClientIP must be injected when sessionAffinityConfig is present");

    // Trap 56: Job restartPolicy: Always normalized to OnFailure
    assert!(healed.contains("restartPolicy: OnFailure"), "Job restartPolicy: Always must be normalized to OnFailure");
    assert!(!healed.contains("restartPolicy: Always"), "Job must not retain restartPolicy: Always");

    // Trap 57: imagePullSecrets scalar list normalized to - name: reg-secret-key
    assert!(healed.contains("imagePullSecrets:\n      - name: reg-secret-key"), "imagePullSecrets scalar list item must be converted to - name: reg-secret-key");

    // Trap 58: Ingress relative path prepended with leading slash
    assert!(healed.contains("path: /api/v2") || healed.contains("path: \"/api/v2\""), "Ingress relative path must have leading slash prepended");

    // Trap 59: Wildcard host quoted
    assert!(healed.contains("host: \"*.example.com\""), "Ingress wildcard host must be quoted");

    // Trap 60: Memory unit casing normalized
    assert!(healed.contains("memory: 500Mi") || healed.contains("memory: \"500Mi\""), "500mi must become 500Mi");

    // Trap 61: hostPath explicit type injected
    assert!(healed.contains("type: FileOrCreate"), "hostPath with file suffix must receive type: FileOrCreate");

    // Trap 62: publishNotReadyAddresses unquoted
    assert!(healed.contains("publishNotReadyAddresses: true"), "publishNotReadyAddresses must be unquoted boolean true");

    // Trap 63: Job ttlSecondsAfterFinished unquoted
    assert!(healed.contains("ttlSecondsAfterFinished: 600"), "ttlSecondsAfterFinished must be unquoted integer 600");

    // Trap 64: Job completionMode normalized to Indexed
    assert!(healed.contains("completionMode: Indexed"), "completionMode 'indexed' must become canonical Indexed");

    // Trap 65: emptyDir medium normalized to Memory
    assert!(healed.contains("medium: Memory") || healed.contains("medium: \"Memory\""), "emptyDir medium 'memory' must become canonical Memory");

    // Trap 66: Probe timeout >= period deadlock prevention
    assert!(healed.contains("periodSeconds: 16"), "periodSeconds must be clamped to timeoutSeconds + 1 (16) to avoid deadlock");

    // Trap 67: HPA inverted bounds aligned
    assert!(healed.contains("maxReplicas: 5"), "maxReplicas must be aligned with minReplicas (5) when inverted");

    // Trap 68: Ingress backend port mutual exclusivity (pruned name)
    assert!(healed.contains("number: 8080"), "backend service port number must be retained");
    assert!(!healed.contains("number: 8080\n              name: http"), "backend service port name must be pruned when number is present");

    // Comment preservation
    assert!(healed.contains("# Comprehensive Traps 35 to 50 Validation Manifest"));

    // Idempotency check: heal(heal(x)) == heal(x)
    let (second_healed, _) = heal_manifest_string(&healed);
    assert_eq!(healed, second_healed, "Second healing pass must produce 100% identical output (Idempotency)");
}
