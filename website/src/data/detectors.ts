export interface Detector {
    id: string;
    category: string;
    name: string;
    severity: 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO';
    rationale: string;
    fixGuide?: string;
    beforeExample?: string;
    afterExample?: string;
    failureModeExplainer?: string;
    k8sVersionImpact?: string;
}

export const DETECTORS: Detector[] = [
    {
        id: "NET-001",
        category: "Networking",
        name: "Invisible Outage & Port Collision",
        severity: "CRITICAL",
        rationale: "Mismatched Service port/targetPort and containerPort cause silent traffic drops where pods run but receive no traffic.",
        failureModeExplainer: "In Kubernetes networking, kube-proxy configures iptables or IPVS routing tables on every node, forwarding traffic from the Service virtual IP and port to the backend pod IP at targetPort. When targetPort differs from the application container's listening socket, TCP SYN handshakes are sent to an unlistened port. Pods report Running and pass basic liveness checks, but all client traffic receives immediate ECONNREFUSED resets or upstream 502/504 Bad Gateway timeouts.",
        k8sVersionImpact: "All Kubernetes versions (v1.20 - v1.37+)",
        fixGuide: "Align the Service targetPort with containerPort, or use yamlr heal to automatically resolve port mismatches.",
        beforeExample: `apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  ports:
  - port: 80
    targetPort: 8080 # Container listens on 3000!`,
        afterExample: `apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  ports:
  - port: 80
    targetPort: 3000 # Aligned by Yamlr`
    },
    {
        id: "NET-002",
        category: "Networking",
        name: "Orphaned Backend",
        severity: "CRITICAL",
        rationale: "Ingress backend references a Service name that does not exist in the manifest set or target namespace.",
        fixGuide: "Verify the Service name in ingress.spec.rules.http.paths.backend.service.name matches an existing Service.",
    },
    {
        id: "NET-003",
        category: "Networking",
        name: "Localhost Trap",
        severity: "ERROR",
        rationale: "Service targeting 127.0.0.1 or localhost fails to route across container and node boundaries in Kubernetes.",
        fixGuide: "Change host from 127.0.0.1 to 0.0.0.0 or a cluster-resolvable service DNS name.",
    },
    {
        id: "NET-004",
        category: "Networking",
        name: "Service Shadowing",
        severity: "WARNING",
        rationale: "Multiple Services sharing identical selector labels cause traffic to split unpredictably between workloads.",
        fixGuide: "Differentiate service selectors using role or app.kubernetes.io/instance labels.",
    },
    {
        id: "NET-005",
        category: "Networking",
        name: "Shadowing Endpoint",
        severity: "ERROR",
        rationale: "Manually declared Endpoints for a Service with an active selector will be continuously overwritten by kube-controller-manager.",
        fixGuide: "Remove the manual Endpoints resource, or remove the selector from the Service to make it headless/external.",
    },
    {
        id: "NET-006",
        category: "Networking",
        name: "Circular Service Ref / ExternalName Loop",
        severity: "CRITICAL",
        rationale: "ExternalName or Service selector referencing itself triggers endless DNS resolution loops that can saturate CoreDNS.",
        fixGuide: "Ensure externalName points to a fully qualified external domain name outside the cluster.",
    },
    {
        id: "NET-007",
        category: "Networking",
        name: "Missing Ingress pathType Specification",
        severity: "CRITICAL",
        rationale: "Ingress resources in networking.k8s.io/v1 require an explicit pathType (Prefix, Exact, or ImplementationSpecific). Without pathType, ingress controllers reject or drop routes.",
        failureModeExplainer: "In Kubernetes v1.18+, the Ingress specification graduated from extensions/v1beta1 to networking.k8s.io/v1. In the v1 API, pathType became a required field with no default value. When clusters upgrade to Kubernetes v1.22+, extensions/v1beta1 is completely removed. Ingress manifests lacking pathType fail API admission validation with 'spec.rules[0].http.paths[0].pathType: Required value'. Ingress-NGINX and AWS Load Balancer Controller also ignore routes without pathType, causing 100% silent traffic loss for ingress host endpoints.",
        k8sVersionImpact: "Kubernetes v1.22+ (Mandatory API Rejection)",
        fixGuide: "Add 'pathType: Prefix' to all path definitions under ingress.spec.rules.http.paths, or execute 'yamlr heal --apply' for automatic non-destructive repair.",
        beforeExample: `apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
spec:
  rules:
  - http:
      paths:
      - path: /
        # pathType is MISSING!
        backend:
          service:
            name: api-service
            port:
              number: 80`,
        afterExample: `apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix # Injected by Yamlr
        backend:
          service:
            name: api-service
            port:
              number: 80`
    },
    {
        id: "SEC-001",
        category: "Security",
        name: "Identity Context Gap",
        severity: "WARNING",
        rationale: "Missing securityContext allows containers to run with root privileges and unconstrained capabilities.",
        fixGuide: "Add securityContext with runAsNonRoot: true and allowPrivilegeEscalation: false.",
        beforeExample: `spec:
  containers:
  - name: app
    image: alpine:latest`,
        afterExample: `spec:
  containers:
  - name: app
    image: alpine:3.19
    securityContext:
      runAsNonRoot: true
      allowPrivilegeEscalation: false`
    },
    {
        id: "SEC-002",
        category: "Security",
        name: "Pull-Safe Hazard",
        severity: "ERROR",
        rationale: "Using ':latest' image tags without imagePullPolicy: Always can deploy stale or contaminated container layers.",
        failureModeExplainer: "When containers declare mutable ':latest' image tags, Kubelet caches the downloaded layers on worker nodes. When a deployment rolls out or a pod is rescheduled to a different node, one node may run the newly pushed build while another node continues running cached older image layers. This causes non-deterministic split-brain behavior across cluster nodes, broken session affinities, and makes incident root-cause analysis nearly impossible.",
        k8sVersionImpact: "All Kubernetes versions",
        fixGuide: "Pin image tags to explicit semantic version tags or sha256 digests, and set imagePullPolicy: IfNotPresent.",
        beforeExample: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-worker
spec:
  template:
    spec:
      containers:
      - name: worker
        image: billing/worker:latest`,
        afterExample: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-worker
spec:
  template:
    spec:
      containers:
      - name: worker
        image: billing/worker:v1.8.2
        imagePullPolicy: IfNotPresent`
    },
    {
        id: "SEC-003",
        category: "Security",
        name: "Namespace Pollution",
        severity: "WARNING",
        rationale: "Manifests without metadata.namespace default to 'default', creating cross-tenant collision risks.",
        fixGuide: "Explicitly declare metadata.namespace or pass --namespace in your GitOps overlay.",
    },
    {
        id: "SEC-004",
        category: "Security",
        name: "Binding Conflict",
        severity: "ERROR",
        rationale: "RoleBinding and ClusterRoleBinding sharing subjects and permissions create ambiguous access boundaries.",
        fixGuide: "Consolidate role bindings into least-privilege role references.",
    },
    {
        id: "SEC-005",
        category: "Security",
        name: "Role/RBAC Collision",
        severity: "WARNING",
        rationale: "Duplicate Roles granting identical permissions inside the same namespace create policy maintenance debt.",
        fixGuide: "Deduplicate redundant Role definitions into a single shared Role.",
    },
    {
        id: "SEC-006",
        category: "Security",
        name: "StringData Leakage",
        severity: "ERROR",
        rationale: "Unencoded plain text in Secret 'data' field causes Kubernetes admission rejection.",
        fixGuide: "Move plaintext strings to the 'stringData' map or base64-encode values into 'data'.",
    },
    {
        id: "SEC-007",
        category: "Security",
        name: "Privilege Escalation",
        severity: "ERROR",
        rationale: "allowPrivilegeEscalation: true allows child processes to inherit setuid/setgid elevated rights.",
        fixGuide: "Set securityContext.allowPrivilegeEscalation: false on all container specs.",
    },
    {
        id: "SEC-008",
        category: "Security",
        name: "Root User Hazard",
        severity: "ERROR",
        rationale: "Containers running with UID 0 (root) violate Pod Security Standards Baseline and Restricted profiles.",
        fixGuide: "Set runAsUser: 10001 and runAsNonRoot: true in securityContext.",
    },
    {
        id: "SEC-009",
        category: "Security",
        name: "Host Network Exposure",
        severity: "CRITICAL",
        rationale: "hostNetwork: true allows pods to sniff loopback traffic and access node-level services directly.",
        fixGuide: "Remove hostNetwork: true unless deploying node-level CNI plugins.",
    },
    {
        id: "SEC-010",
        category: "Security",
        name: "Host Path Exposure",
        severity: "CRITICAL",
        rationale: "hostPath mounts expose node filesystem directories to container compromise.",
        fixGuide: "Use persistentVolumeClaim or emptyDir instead of raw hostPath mounts.",
    },
    {
        id: "REL-001",
        category: "Reliability",
        name: "Webhook Brownout",
        severity: "WARNING",
        rationale: "ValidatingWebhookConfiguration with failurePolicy: Fail and no timeoutSeconds can block all cluster mutations during network blips.",
        fixGuide: "Set timeoutSeconds: 3 and use failurePolicy: Ignore where acceptable.",
    },
    {
        id: "REL-002",
        category: "Reliability",
        name: "Webhook Target Collision",
        severity: "ERROR",
        rationale: "Multiple admission webhooks intercepting the same resource path cause non-deterministic mutation ordering.",
        fixGuide: "Sequence webhooks using distinct matchRules and avoid overlapping mutators.",
    },
    {
        id: "REL-003",
        category: "Reliability",
        name: "Scaling War (HPA vs Replicas)",
        severity: "ERROR",
        rationale: "Hardcoding spec.replicas on a Deployment while a HorizontalPodAutoscaler targets it creates flapping replicas on each deploy.",
        fixGuide: "Remove spec.replicas from the Deployment manifest when an HPA is present. Yamlr heal handles this automatically.",
        beforeExample: `apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3 # Fights HPA target 1-10!`,
        afterExample: `apiVersion: apps/v1
kind: Deployment
spec:
  # Replicas removed: governed by HPA`
    },
    {
        id: "REL-004",
        category: "Reliability",
        name: "Affinity Deadlock",
        severity: "ERROR",
        rationale: "requiredDuringSchedulingIgnoredDuringExecution anti-affinity with matching topologyKey prevents scheduling when replicas exceed available nodes.",
        fixGuide: "Switch to preferredDuringSchedulingIgnoredDuringExecution or ensure node count accommodates replicas.",
    },
    {
        id: "REL-005",
        category: "Reliability",
        name: "PDB Overlap & Eviction Block",
        severity: "WARNING",
        rationale: "Multiple PodDisruptionBudgets targeting identical selectors can permanently freeze node drains during upgrades.",
        fixGuide: "Ensure each pod is covered by at most one PDB.",
    },
    {
        id: "REL-006",
        category: "Reliability",
        name: "Resource Logic Error",
        severity: "ERROR",
        rationale: "Container resource requests exceed limits (e.g. requests.memory > limits.memory), which Kubernetes immediately rejects.",
        fixGuide: "Ensure requests <= limits for both cpu and memory.",
    },
    {
        id: "REL-007",
        category: "Reliability",
        name: "Liveness Aggression",
        severity: "WARNING",
        rationale: "Liveness probes with initialDelaySeconds: 0 or low failureThreshold can kill slowly initializing pods in a boot loop.",
        fixGuide: "Add startupProbe for slow initializations or increase initialDelaySeconds.",
    },
    {
        id: "REL-008",
        category: "Reliability",
        name: "Sidecar Race Condition",
        severity: "WARNING",
        rationale: "Sidecars terminating before main workload containers lose access to logging or service mesh proxies.",
        fixGuide: "Add preStop lifecycle hooks with sleep delays or adopt native sidecar containers (K8s 1.28+).",
    },
    {
        id: "REL-009",
        category: "Reliability",
        name: "Grace Period Mismatch",
        severity: "WARNING",
        rationale: "terminationGracePeriodSeconds shorter than application shutdown hooks leads to abrupt SIGKILL before buffer flushes.",
        fixGuide: "Increase terminationGracePeriodSeconds to accommodate drain scripts.",
    },
    {
        id: "REL-010",
        category: "Reliability",
        name: "Proportional Resource Hazard (Burst OOM)",
        severity: "WARNING",
        rationale: "High CPU allocation with disproportionately tiny memory limits causes containers to OOM-kill under multi-threaded spikes.",
        fixGuide: "Balance CPU and memory allocations proportionally to expected workload characteristics.",
    },
    {
        id: "TOP-001",
        category: "Topology",
        name: "Topology Deadlock",
        severity: "ERROR",
        rationale: "topologySpreadConstraints with maxSkew: 1 and whenUnsatisfiable: DoNotSchedule prevents pod rollouts on heterogeneous clusters.",
        fixGuide: "Use whenUnsatisfiable: ScheduleAnyway or increase maxSkew.",
    },
    {
        id: "OPS-001",
        category: "Operations",
        name: "Immutable Field Drift",
        severity: "ERROR",
        rationale: "Modifying immutable fields like spec.selector on Deployments causes kubectl apply failures.",
        fixGuide: "Create a new Deployment or recreate the existing one; selector fields cannot be updated in-place.",
    },
    {
        id: "OPS-002",
        category: "Operations",
        name: "Floating Tag Hazard",
        severity: "WARNING",
        rationale: "Tags like ':latest', ':main', or ':v1' change non-deterministically, breaking rollback guarantees.",
        fixGuide: "Pin container images to immutable git commit SHA tags or SHA256 image digests.",
    },
    {
        id: "OPS-003",
        category: "Operations",
        name: "Mount-Path Collision",
        severity: "ERROR",
        rationale: "Mounting two volumes to the exact same mountPath in a single container obscures the underlying volume data.",
        fixGuide: "Use distinct mount paths or subPath mounts.",
    },
    {
        id: "STO-001",
        category: "Storage",
        name: "Orphaned StorageClass",
        severity: "INFO",
        rationale: "StorageClass definitions not referenced by any PVC or marked default introduce configuration ambiguity.",
        fixGuide: "Remove obsolete StorageClasses or annotate one as storageclass.kubernetes.io/is-default-class: 'true'.",
    },
    {
        id: "STO-002",
        category: "Storage",
        name: "Dangling PersistentVolume",
        severity: "WARNING",
        rationale: "PersistentVolumes without a corresponding PVC remain unbound and incur infrastructure costs without usage.",
        fixGuide: "Bind or reclaim unused PersistentVolumes.",
    },
    {
        id: "HYG-001",
        category: "Hygiene",
        name: "Dangling CRD",
        severity: "INFO",
        rationale: "CustomResourceDefinitions with no active instances add unneeded schema validation overhead.",
        fixGuide: "Clean up unused CRDs from GitOps repository manifests.",
    },
    {
        id: "HYG-002",
        category: "Hygiene",
        name: "Dangling Identity",
        severity: "INFO",
        rationale: "ServiceAccounts with no associated RoleBindings or workload references unnecessarily expand identity attack surfaces.",
        fixGuide: "Prune unused ServiceAccount declarations.",
    },
    {
        id: "GOV-001",
        category: "Governance",
        name: "Reserved Label Pollution",
        severity: "WARNING",
        rationale: "Custom labels under 'kubernetes.io/' or 'k8s.io/' prefix conflict with core Kubernetes system components.",
        fixGuide: "Use custom prefixes like 'app.example.com/' or standard 'app.kubernetes.io/' labels.",
    },
    {
        id: "GOV-002",
        category: "Governance",
        name: "PriorityClass Collision",
        severity: "WARNING",
        rationale: "Multiple PriorityClasses assigned identical integer values make preemption ordering non-deterministic.",
        fixGuide: "Assign unique, separated priority integers across PriorityClass resources.",
    },
    {
        id: "GOV-003",
        category: "Governance",
        name: "Cluster-Scope Safety Hazard",
        severity: "ERROR",
        rationale: "ClusterRoles referencing namespace-scoped resources improperly grant cluster-wide read/write permissions.",
        fixGuide: "Scope permissions using RoleBinding within specific namespaces.",
    },
    {
        id: "PRO-001",
        category: "Prophetic",
        name: "API Deprecation Prediction",
        severity: "WARNING",
        rationale: "Manifests using deprecated APIs will fail admission when target clusters upgrade to newer Kubernetes releases.",
        fixGuide: "Run yamlr upgrade or yamlr heal to auto-migrate to current stable API versions.",
    },
    {
        id: "BST-001",
        category: "Best Practices",
        name: "Missing Resource Limits",
        severity: "WARNING",
        rationale: "Unconstrained containers can consume all node memory, causing OOM-killer crashes across critical neighbors.",
        failureModeExplainer: "When container specs omit memory and CPU limits, a memory leak or sudden traffic spike inside a single pod allows it to monopolize the entire worker node's physical RAM. When node memory is exhausted, the Linux Kernel Out-Of-Memory (OOM) Killer triggers indiscriminately. Because container processes run without cgroup caps, the Kernel OOM killer frequently kills essential Kubernetes daemons (such as kubelet, container runtime, or CoreDNS pods), cascading into node-not-ready cluster outages.",
        k8sVersionImpact: "All Kubernetes versions",
        fixGuide: "Define resources.limits.cpu, resources.limits.memory, and corresponding requests on all container specs.",
        beforeExample: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: backend:2.0.1`,
        afterExample: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: backend:2.0.1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi`
    },
    {
        id: "BST-002",
        category: "Best Practices",
        name: "Missing Health Probes",
        severity: "WARNING",
        rationale: "Workloads without readinessProbe can receive user traffic before they are ready, causing 502/504 errors.",
        fixGuide: "Add readinessProbe and livenessProbe specifications to workloads.",
    },
    {
        id: "BST-003",
        category: "Best Practices",
        name: "Read-Only Root Filesystem",
        severity: "INFO",
        rationale: "Writable container root filesystems allow malicious binaries or shell scripts to persist on compromise.",
        fixGuide: "Set securityContext.readOnlyRootFilesystem: true and use emptyDir volumes for scratch directories.",
    },
    {
        id: "BST-004",
        category: "Best Practices",
        name: "ServiceAccount Auto-Mount",
        severity: "INFO",
        rationale: "Pods that do not communicate with the Kubernetes API server should not mount default API credentials.",
        fixGuide: "Set automountServiceAccountToken: false on the Pod spec.",
    },
    {
        id: "BST-005",
        category: "Best Practices",
        name: "Privileged Capabilities Hazard",
        severity: "WARNING",
        rationale: "Granting CAP_SYS_ADMIN, CAP_NET_ADMIN, or ALL capabilities exposes nodes to container escape.",
        fixGuide: "Drop all capabilities (capabilities: { drop: ['ALL'] }) and selectively add only what is strictly required.",
    }
];

export const DETECTOR_MAP = new Map<string, Detector>(
    DETECTORS.map(d => [d.id.toUpperCase(), d])
);
