/**
 * Kubernetes Schema Field & Enum Typo Healer (Features 1 & 2 Parity for Browser Sandbox).
 * Uses scoped Levenshtein edit-distance matching against official Kubernetes
 * OpenAPI properties and enum values to auto-correct typos like:
 * - Property keys: `continers:` -> `containers:`, `replica:` -> `replicas:`, `label:` -> `labels:`
 * - Enum values: `imagePullPolicy: Alway` -> `Always`, `type: clusterip` -> `ClusterIP`
 */

import { levenshtein } from "./fuzzyMatcher";
import { WasmViolation } from "../WasmBridge";

export const ROOT_PROPERTIES = [
    "apiVersion", "kind", "metadata", "spec", "status", "data", "stringData"
];

export const METADATA_PROPERTIES = [
    "name", "namespace", "labels", "annotations", "generation", "uid",
    "resourceVersion", "creationTimestamp", "deletionTimestamp",
    "ownerReferences", "finalizers"
];

export const WORKLOAD_SPEC_PROPERTIES = [
    "replicas", "selector", "template", "strategy", "minReadySeconds",
    "revisionHistoryLimit", "paused", "progressDeadlineSeconds"
];

export const POD_SPEC_PROPERTIES = [
    "containers", "initContainers", "ephemeralContainers", "volumes",
    "restartPolicy", "terminationGracePeriodSeconds", "dnsPolicy",
    "nodeSelector", "serviceAccountName", "serviceAccount", "hostNetwork",
    "hostPID", "hostIPC", "securityContext", "imagePullSecrets", "affinity",
    "tolerations", "priorityClassName"
];

export const CONTAINER_PROPERTIES = [
    "name", "image", "command", "args", "workingDir", "ports", "env",
    "envFrom", "resources", "volumeMounts", "volumeDevices", "livenessProbe",
    "readinessProbe", "startupProbe", "lifecycle", "terminationMessagePath",
    "terminationMessagePolicy", "imagePullPolicy", "securityContext"
];

export const ENUM_DEFINITIONS: Record<string, string[]> = {
    imagePullPolicy: ["Always", "IfNotPresent", "Never"],
    restartPolicy: ["Always", "OnFailure", "Never"],
    type: ["ClusterIP", "NodePort", "LoadBalancer", "ExternalName"],
    dnsPolicy: ["ClusterFirst", "Default", "ClusterFirstWithHostNet", "None"],
    sessionAffinity: ["None", "ClientIP"],
    protocol: ["TCP", "UDP", "SCTP"],
    pathType: ["Prefix", "Exact", "ImplementationSpecific"],
    concurrencyPolicy: ["Allow", "Forbid", "Replace"],
    accessModes: ["ReadWriteOnce", "ReadOnlyMany", "ReadWriteMany", "ReadWriteOncePod"],
    reclaimPolicy: ["Retain", "Recycle", "Delete"],
};

export const BOOLEAN_KEYS = [
    "hostNetwork", "hostPID", "hostIPC", "automountServiceAccountToken",
    "readOnly", "privileged", "allowPrivilegeEscalation", "runAsNonRoot",
    "stdin", "tty"
];

/**
 * Finds the closest matching official property name if input is a typo (distance <= 2).
 */
export function fuzzyMatchProperty(input: string, candidateKeys: string[]): string | null {
    if (input.length < 4) return null;

    // Exact match
    if (candidateKeys.includes(input)) return null;

    const inputLower = input.toLowerCase();

    // Case-insensitive exact match
    for (const cand of candidateKeys) {
        if (cand.toLowerCase() === inputLower) return cand;
    }

    // Levenshtein distance <= 2
    let bestMatch: string | null = null;
    let minDist = 3;

    for (const cand of candidateKeys) {
        const dist = levenshtein(inputLower, cand.toLowerCase());
        if (dist < minDist) {
            minDist = dist;
            bestMatch = cand;
        }
    }

    return bestMatch;
}

/**
 * Matches an enum value against allowed enum definitions.
 */
export function fuzzyMatchEnum(input: string, candidates: string[]): string | null {
    const cleaned = input.trim().replace(/^['"]|['"]$/g, "");
    if (!cleaned) return null;
    if (candidates.includes(cleaned)) return null;

    const lower = cleaned.toLowerCase();
    for (const cand of candidates) {
        if (cand.toLowerCase() === lower) return cand;
    }

    if (cleaned.length >= 3) {
        let best: string | null = null;
        let minDist = 3;
        for (const cand of candidates) {
            const dist = levenshtein(lower, cand.toLowerCase());
            const maxAllowed = cleaned.length <= 5 ? 1 : 2;
            if (dist <= maxAllowed && dist < minDist) {
                const maxLen = Math.max(cleaned.length, cand.length);
                if ((maxLen - dist) / maxLen >= 0.65) {
                    minDist = dist;
                    best = cand;
                }
            }
        }
        return best;
    }
    return null;
}

/**
 * Scans manifest lines and corrects schema property and enum typos in-place.
 */
export function healSchemaFieldTypos(lines: string[]): {
    healedLines: string[];
    violations: WasmViolation[];
} {
    const healedLines = [...lines];
    const violations: WasmViolation[] = [];
    const indentStack: { indent: number; key: string }[] = [];

    for (let i = 0; i < healedLines.length; i++) {
        const line = healedLines[i];
        if (!line.trim() || line.trim().startsWith("#") || line.trim().startsWith("---")) {
            continue;
        }

        const matchIndent = line.match(/^(\s*)/);
        const indent = matchIndent ? matchIndent[1].length : 0;
        const leadingSpaces = " ".repeat(indent);

        // Maintain path stack based on indentation
        while (indentStack.length > 0 && indentStack[indentStack.length - 1].indent >= indent) {
            indentStack.pop();
        }

        const parentPath = indentStack.map(s => s.key).join(".");

        // List item handling (e.g. `  - ReadWriteOnce`)
        const listItemMatch = line.trim().match(/^-\s+([a-zA-Z0-9_-]+)/);
        if (listItemMatch && parentPath.endsWith("accessModes")) {
            const rawVal = listItemMatch[1];
            const cand = ENUM_DEFINITIONS.accessModes;
            const corrected = fuzzyMatchEnum(rawVal, cand);
            if (corrected && corrected !== rawVal) {
                violations.push({
                    field_path: `${parentPath}[*]`,
                    violation_type: "SCHEMA_ERROR",
                    code: "SCHEMA-003",
                    message: `Invalid enum value '${rawVal}'. Auto-corrected to official OpenAPI value '${corrected}'.`,
                    severity: "critical",
                    line_no: i + 1
                });
                healedLines[i] = `${leadingSpaces}- ${corrected}`;
            }
            continue;
        }

        const keyMatch = line.trim().match(/^([a-zA-Z0-9_-]+):(.*)$/);
        if (!keyMatch) continue;

        let rawKey = keyMatch[1];
        let rest = keyMatch[2];

        // Determine candidate keys based on parent context
        let candidates: string[] | null = null;
        if (indentStack.length === 0) {
            candidates = ROOT_PROPERTIES;
        } else if (parentPath === "metadata" || parentPath.endsWith(".metadata")) {
            candidates = METADATA_PROPERTIES;
        } else if (parentPath === "spec") {
            candidates = WORKLOAD_SPEC_PROPERTIES;
        } else if (parentPath === "spec.template.spec" || parentPath === "template.spec") {
            candidates = POD_SPEC_PROPERTIES;
        } else if (parentPath.includes("containers")) {
            candidates = CONTAINER_PROPERTIES;
        }

        // 1. Property Key Typo Correction (Feature 1)
        if (candidates) {
            const correctedKey = fuzzyMatchProperty(rawKey, candidates);
            if (correctedKey && correctedKey !== rawKey) {
                const fullLoc = parentPath ? `${parentPath}.${rawKey}` : rawKey;
                violations.push({
                    field_path: fullLoc,
                    violation_type: "SCHEMA_ERROR",
                    code: "SCHEMA-002",
                    message: `Misspelled schema property '${rawKey}'. Auto-corrected to official OpenAPI property '${correctedKey}'.`,
                    severity: "critical",
                    line_no: i + 1
                });
                rawKey = correctedKey;
                healedLines[i] = `${leadingSpaces}${rawKey}:${rest}`;
            }
        }

        // 2. Enum Value Typo & Case Correction (Feature 2)
        const enumCandidates = ENUM_DEFINITIONS[rawKey];
        if (enumCandidates && rest.trim()) {
            const rawVal = rest.trim();
            const correctedEnum = fuzzyMatchEnum(rawVal, enumCandidates);
            if (correctedEnum && correctedEnum !== rawVal.replace(/^['"]|['"]$/g, "")) {
                const fullLoc = parentPath ? `${parentPath}.${rawKey}` : rawKey;
                violations.push({
                    field_path: fullLoc,
                    violation_type: "SCHEMA_ERROR",
                    code: "SCHEMA-003",
                    message: `Invalid enum value '${rawVal}'. Auto-corrected to official OpenAPI value '${correctedEnum}'.`,
                    severity: "critical",
                    line_no: i + 1
                });
                rest = ` ${correctedEnum}`;
                healedLines[i] = `${leadingSpaces}${rawKey}:${rest}`;
            }
        }

        // 3. Boolean Coercion
        if (BOOLEAN_KEYS.includes(rawKey) && rest.trim()) {
            const rawVal = rest.trim().toLowerCase().replace(/^['"]|['"]$/g, "");
            if (rawVal === "yes" || rawVal === "on" || rawVal === "true") {
                if (rest.trim() !== "true") {
                    healedLines[i] = `${leadingSpaces}${rawKey}: true`;
                }
            } else if (rawVal === "no" || rawVal === "off" || rawVal === "false") {
                if (rest.trim() !== "false") {
                    healedLines[i] = `${leadingSpaces}${rawKey}: false`;
                }
            }
        }

        indentStack.push({ indent, key: rawKey });
    }

    return { healedLines, violations };
}
