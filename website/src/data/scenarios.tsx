import { 
    ShieldCheck, 
    History, 
    Wand2, 
    Terminal, 
    AlertCircle, 
    CheckCircle2, 
    Zap, 
    Coins, 
    Unplug,
    Layers,
    Activity,
    Search
} from "lucide-react";
import { ReactNode } from "react";

export interface AnalysisFinding {
    id: string;
    code: string;
    title: string;
    description: string;
    severity: "critical" | "warning" | "info";
    icon: ReactNode;
}

export interface Scenario {
    id: string;
    label: string;
    icon: ReactNode;
    description: string;
    cliCommand: string;
    original: string;
    healed: string;
    highlights: number[];
    deletions: number[];
    findings: AnalysisFinding[];
}

export const SCENARIOS: Scenario[] = [
    {
        id: "security",
        label: "Security Hardening",
        icon: <ShieldCheck size={16} />,
        description: "Enforces Kubernetes Pod Security Standards (PSS) Baseline by injecting non-root execution, read-only root filesystems, and immutable image digests.",
        cliCommand: "yamlr heal ./k8s/deployment.yaml --apply",
        original: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  labels:
    app: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80`,
        healed: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  labels:
    app: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.3
        ports:
        - containerPort: 80
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false`,
        highlights: [20, 24, 25, 26, 27, 28],
        deletions: [20],
        findings: [
            {
                id: "root-exec",
                code: "SEC-008",
                title: "Root User Hazard",
                description: "Container runs as root (UID 0) by default. Enforced 'runAsNonRoot: true' and 'runAsUser: 1000'.",
                severity: "critical",
                icon: <AlertCircle size={14} className="text-rose-500" />
            },
            {
                id: "writable-fs",
                code: "BST-003",
                title: "Read-Only Root FS",
                description: "Root filesystem is writable. Switched to 'readOnlyRootFilesystem: true' to prevent persistent malware payloads.",
                severity: "warning",
                icon: <Terminal size={14} className="text-amber-500" />
            },
            {
                id: "immutable-tag",
                code: "OPS-002",
                title: "Floating Tag Hazard",
                description: "Mutable ':latest' tag detected. Pinned to immutable release tag ':1.25.3'.",
                severity: "info",
                icon: <CheckCircle2 size={14} className="text-emerald-500" />
            }
        ]
    },
    {
        id: "traffic",
        label: "Link Safety",
        icon: <Unplug size={16} />,
        description: "Reconciles cross-resource routing mismatches between Ingress backends and Service ports to prevent silent traffic drops.",
        cliCommand: "yamlr heal ./k8s/ --apply",
        original: `apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-gateway
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80`,
        healed: `apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-gateway
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080`,
        highlights: [27],
        deletions: [27],
        findings: [
            {
                id: "port-mismatch",
                code: "NET-001",
                title: "Invisible Outage & Port Collision",
                description: "Ingress backend points to port 80, but target Service 'api-service' listens on 8080. Traffic would return 502 Bad Gateway.",
                severity: "critical",
                icon: <AlertCircle size={14} className="text-rose-500" />
            },
            {
                id: "link-healing",
                code: "NET-002",
                title: "Cross-Resource Synthesis",
                description: "Reconciled Ingress port to 8080 from the verified Service definition.",
                severity: "info",
                icon: <Wand2 size={14} className="text-sky-500" />
            }
        ]
    },
    {
        id: "api-migration",
        label: "API Modernization",
        icon: <Zap size={16} />,
        description: "Migrates deprecated Kubernetes APIs to stable versions ahead of cluster upgrades without breaking resource attributes.",
        cliCommand: "yamlr upgrade ./k8s/ --k8s-version 1.30 --apply",
        original: `apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: web-frontend
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50`,
        healed: `apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: web-frontend
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50`,
        highlights: [1],
        deletions: [1],
        findings: [
            {
                id: "api-obsolete",
                code: "PRO-001",
                title: "API Deprecation Prediction",
                description: "'autoscaling/v2beta2' was deprecated in v1.23 and removed in v1.26. Upgraded to official 'autoscaling/v2' schema.",
                severity: "warning",
                icon: <History size={14} className="text-amber-500" />
            }
        ]
    },
    {
        id: "resilience",
        label: "Fault Tolerance",
        icon: <Layers size={16} />,
        description: "Guarantees high availability during rolling updates by injecting Pod Anti-Affinity rules with topology spread.",
        cliCommand: "yamlr heal ./k8s/redis.yaml --apply",
        original: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-cache
  labels:
    app: redis-cache
spec:
  replicas: 3
  selector:
    matchLabels:
      app: redis-cache
  template:
    metadata:
      labels:
        app: redis-cache
    spec:
      containers:
      - name: redis
        image: redis:7.2-alpine`,
        healed: `apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-cache
  labels:
    app: redis-cache
spec:
  replicas: 3
  selector:
    matchLabels:
      app: redis-cache
  template:
    metadata:
      labels:
        app: redis-cache
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: redis-cache
              topologyKey: "kubernetes.io/hostname"
      containers:
      - name: redis
        image: redis:7.2-alpine`,
        highlights: [18, 19, 20, 21, 22, 23, 24, 25, 26, 27],
        deletions: [],
        findings: [
            {
                id: "single-point-failure",
                code: "REL-004",
                title: "Affinity Deadlock & HA Hazard",
                description: "Replicas could land on the same node. Injected soft podAntiAffinity to spread pods across hostnames.",
                severity: "warning",
                icon: <Activity size={14} className="text-amber-500" />
            }
        ]
    },
    {
        id: "forensic-audit",
        label: "RBAC Governance",
        icon: <Search size={16} />,
        description: "Audits privilege escalation paths, eliminates cluster-admin blast radiuses, and enforces service account token boundaries.",
        cliCommand: "yamlr check ./k8s/rbac/ --strict",
        original: `apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-operator
  namespace: default
automountServiceAccountToken: true
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: app-operator-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: app-operator
  namespace: default`,
        healed: `apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-operator
  namespace: default
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-operator-binding
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: app-operator-role
subjects:
- kind: ServiceAccount
  name: app-operator
  namespace: default`,
        highlights: [6, 10, 15, 16],
        deletions: [6, 10, 15, 16],
        findings: [
            {
                id: "rbac-escalation",
                code: "GOV-003",
                title: "Cluster-Scope Safety Hazard",
                description: "Namespace-scoped workload bound to cluster-wide 'cluster-admin'. Scoped to localized RoleBinding with least-privilege role.",
                severity: "critical",
                icon: <AlertCircle size={14} className="text-rose-500" />
            },
            {
                id: "token-automount",
                code: "BST-004",
                title: "ServiceAccount Auto-Mount Risk",
                description: "Auto-mount for ServiceAccount tokens enabled by default. Disabled 'automountServiceAccountToken' to prevent credential leakage.",
                severity: "info",
                icon: <ShieldCheck size={14} className="text-emerald-500" />
            }
        ]
    }
];
