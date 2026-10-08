/**
 * Kubernetes Kind Fuzzy Matcher & Typo Resolver.
 * Uses Levenshtein edit-distance and alias dictionaries to auto-correct
 * misspelled Kubernetes resource kinds according to official OpenAPI schemas.
 */

export const CANONICAL_KINDS = [
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "ReplicaSet",
    "Pod",
    "Job",
    "CronJob",
    "Service",
    "Ingress",
    "ConfigMap",
    "Secret",
    "ServiceAccount",
    "HorizontalPodAutoscaler",
    "PodDisruptionBudget",
    "NetworkPolicy",
    "Role",
    "ClusterRole",
    "RoleBinding",
    "ClusterRoleBinding",
    "Namespace",
    "PersistentVolume",
    "PersistentVolumeClaim"
] as const;

export type CanonicalKind = typeof CANONICAL_KINDS[number];

const KIND_ALIASES: Record<string, CanonicalKind> = {
    // Deployment typos & aliases
    "deploy": "Deployment",
    "deploymen": "Deployment",
    "deployments": "Deployment",
    "deploment": "Deployment",
    "deploymnt": "Deployment",
    "deployement": "Deployment",

    // Service typos & aliases
    "svc": "Service",
    "servic": "Service",
    "services": "Service",
    "serivce": "Service",

    // Ingress typos & aliases
    "ing": "Ingress",
    "ingres": "Ingress",
    "ingresses": "Ingress",
    "ingrss": "Ingress",

    // Pod typos & aliases
    "po": "Pod",
    "podd": "Pod",
    "pods": "Pod",

    // StatefulSet & DaemonSet
    "sts": "StatefulSet",
    "statefulset": "StatefulSet",
    "statefulsets": "StatefulSet",
    "ds": "DaemonSet",
    "daemonset": "DaemonSet",
    "daemonsets": "DaemonSet",

    // ConfigMap & Secret
    "cm": "ConfigMap",
    "configmap": "ConfigMap",
    "configmaps": "ConfigMap",
    "secrets": "Secret",

    // Workload & Scaling
    "hpa": "HorizontalPodAutoscaler",
    "horizontalpodautoscaler": "HorizontalPodAutoscaler",
    "pdb": "PodDisruptionBudget",
    "poddisruptionbudget": "PodDisruptionBudget",
    "cj": "CronJob",
    "cronjob": "CronJob",
    "cronjobs": "CronJob",
    "jobs": "Job",

    // Auth & RBAC
    "sa": "ServiceAccount",
    "serviceaccount": "ServiceAccount",
    "serviceaccounts": "ServiceAccount",
    "ns": "Namespace",
    "namespace": "Namespace",
    "namespaces": "Namespace",
    "role": "Role",
    "clusterrole": "ClusterRole",
    "rolebinding": "RoleBinding",
    "clusterrolebinding": "ClusterRoleBinding"
};

/**
 * Calculates standard Levenshtein distance between two strings.
 */
export function levenshtein(a: string, b: string): number {
    const matrix: number[][] = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1, // substitution
                    matrix[i][j - 1] + 1,     // insertion
                    matrix[i - 1][j] + 1      // deletion
                );
            }
        }
    }
    return matrix[b.length][a.length];
}

/**
 * Resolves an input kind string to its canonical Kubernetes Kind.
 * Detects typos with edit distance <= 2 or prefix matches.
 */
export function resolveKubernetesKind(rawKind: string): { matchedKind: CanonicalKind | null; isTypo: boolean } {
    const trimmed = rawKind.trim();
    if (!trimmed) return { matchedKind: null, isTypo: false };

    // 1. Exact canonical match
    const exactMatch = CANONICAL_KINDS.find(k => k === trimmed);
    if (exactMatch) {
        return { matchedKind: exactMatch, isTypo: false };
    }

    const lower = trimmed.toLowerCase();

    // 2. Case mismatch to canonical kind
    const caseMatch = CANONICAL_KINDS.find(k => k.toLowerCase() === lower);
    if (caseMatch) {
        return { matchedKind: caseMatch, isTypo: true };
    }

    // 3. Known alias or typo table
    if (KIND_ALIASES[lower]) {
        return { matchedKind: KIND_ALIASES[lower], isTypo: true };
    }

    // 4. Fuzzy Levenshtein match (distance <= 2)
    let bestMatch: CanonicalKind | null = null;
    let minDistance = 3;

    for (const canonical of CANONICAL_KINDS) {
        const dist = levenshtein(lower, canonical.toLowerCase());
        if (dist < minDistance) {
            minDistance = dist;
            bestMatch = canonical;
        }
    }

    if (bestMatch && minDistance <= 2) {
        return { matchedKind: bestMatch, isTypo: true };
    }

    // 5. Prefix match (for strings with 4+ characters)
    if (lower.length >= 4) {
        const prefixMatch = CANONICAL_KINDS.find(k => k.toLowerCase().startsWith(lower));
        if (prefixMatch) {
            return { matchedKind: prefixMatch, isTypo: true };
        }
    }

    return { matchedKind: null, isTypo: false };
}
