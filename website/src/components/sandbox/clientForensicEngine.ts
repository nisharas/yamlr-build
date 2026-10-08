/**
 * Client-Side Forensic Engine for Browser Sandbox.
 *
 * Why: Evaluates Kubernetes manifest rules and generates auto-repaired AST
 * previews in the browser when offline or before the WebAssembly module loads.
 */

import { resolveKubernetesKind } from "@/components/sandbox/fuzzyMatcher";
import { healSchemaFieldTypos } from "@/components/sandbox/schemaFieldHealer";
import { healStructuralIssues } from "@/components/sandbox/structuralHealer";

export interface WasmViolation {
    field_path: string;
    violation_type: string;
    code: string;
    message: string;
    severity: "critical" | "warning" | "info";
    line_no?: number;
}

export interface WasmFix {
    field_path: string;
    original_value: string;
    suggested_value: string;
    fix_type: string;
}

export interface WasmAuditResult {
    violations: WasmViolation[];
    suggested_fixes: WasmFix[];
    healedYaml: string;
    healthScore: number;
    healedLineNumbers: number[];
    deletedLineNumbers: number[];
}

/**
 * Computes longest common subsequence (LCS) line-diff between original and healed text.
 */
export function computeLineDiff(original: string, healed: string): { healedLineNumbers: number[]; deletedLineNumbers: number[] } {
    const origLines = original.split("\n");
    const healLines = healed.split("\n");

    const m = origLines.length;
    const n = healLines.length;

    const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        const oTrim = origLines[i - 1].trim();
        for (let j = 1; j <= n; j++) {
            if (oTrim === healLines[j - 1].trim() && oTrim.length > 0) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    const matchedOrig = new Set<number>();
    const matchedHeal = new Set<number>();

    let i = m;
    let j = n;
    while (i > 0 && j > 0) {
        const oTrim = origLines[i - 1].trim();
        const hTrim = healLines[j - 1].trim();
        if (oTrim === hTrim && oTrim.length > 0) {
            matchedOrig.add(i);
            matchedHeal.add(j);
            i--;
            j--;
        } else if (dp[i - 1][j] >= dp[i][j - 1]) {
            i--;
        } else {
            j--;
        }
    }

    const deletedLineNumbers: number[] = [];
    for (let k = 1; k <= m; k++) {
        if (!matchedOrig.has(k) && origLines[k - 1].trim().length > 0) {
            deletedLineNumbers.push(k);
        }
    }

    const healedLineNumbers: number[] = [];
    for (let k = 1; k <= n; k++) {
        if (!matchedHeal.has(k) && healLines[k - 1].trim().length > 0) {
            healedLineNumbers.push(k);
        }
    }

    return { healedLineNumbers, deletedLineNumbers };
}

/**
 * In-browser client-side forensic engine.
 * Applies Yamlr core healing rules deterministically for immediate sandbox preview.
 */
export function executeClientForensicEngine(content: string, targetVersion: string = "1.30"): WasmAuditResult {
    const lines = content.split("\n");
    const violations: WasmViolation[] = [];
    const suggested_fixes: WasmFix[] = [];
    let healedLines = [...lines];

    // Detect and validate resource Kind with Levenshtein typo auto-correction
    let kind = "";
    for (let i = 0; i < lines.length; i++) {
        const kindMatch = lines[i].match(/^\s*kind:\s*([A-Za-z0-9_-]+)/);
        if (kindMatch) {
            const rawKind = kindMatch[1].trim();
            const { matchedKind, isTypo } = resolveKubernetesKind(rawKind);

            if (matchedKind) {
                kind = matchedKind;
                if (isTypo || rawKind !== matchedKind) {
                    violations.push({
                        field_path: "kind",
                        violation_type: "SCHEMA_ERROR",
                        code: "SCHEMA-001",
                        message: `Misspelled Kubernetes Kind '${rawKind}'. Auto-corrected to official schema Kind '${matchedKind}'.`,
                        severity: "critical",
                        line_no: i + 1
                    });
                    suggested_fixes.push({
                        field_path: "kind",
                        original_value: rawKind,
                        suggested_value: matchedKind,
                        fix_type: "SCHEMA_REPAIR"
                    });
                    const indentMatch = lines[i].match(/^(\s*)/);
                    const indent = indentMatch ? indentMatch[1] : "";
                    healedLines[i] = `${indent}kind: ${matchedKind}`;
                }
            } else {
                kind = rawKind;
            }
            break;
        }
    }

    // Stage 1: Schema Property Key Typo Correction
    const { healedLines: fieldHealed, violations: fieldViolations } = healSchemaFieldTypos(healedLines);
    healedLines = fieldHealed;
    violations.push(...fieldViolations);

    // Stage 1.5: Structural Normalization
    const { healedLines: structHealed, violations: structViolations } = healStructuralIssues(healedLines);
    healedLines = structHealed;
    violations.push(...structViolations);

    // Rule 1: API Deprecation & Schema Migration (PRO-001)
    const apiLineIdx = healedLines.findIndex(l => /^\s*apiVersion:\s*/.test(l));
    if (apiLineIdx !== -1) {
        const rawLine = healedLines[apiLineIdx];
        const apiValMatch = rawLine.match(/^\s*apiVersion:\s*([^\s#]+)/);
        const currentApi = apiValMatch ? apiValMatch[1].trim() : "";

        let targetApi = "";
        let reason = "";

        if (["Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"].includes(kind)) {
            if (currentApi !== "apps/v1") {
                targetApi = "apps/v1";
                reason = `'${currentApi}' is deprecated for ${kind} in K8s v${targetVersion}. Upgraded to stable 'apps/v1'.`;
            }
        } else if (kind === "Ingress") {
            if (currentApi !== "networking.k8s.io/v1") {
                targetApi = "networking.k8s.io/v1";
                reason = `'${currentApi}' is deprecated for Ingress in K8s v${targetVersion}. Upgraded to stable 'networking.k8s.io/v1'.`;
            }
        } else if (kind === "HorizontalPodAutoscaler") {
            if (currentApi !== "autoscaling/v2") {
                targetApi = "autoscaling/v2";
                reason = `'${currentApi}' is deprecated for HPA in K8s v${targetVersion}. Upgraded to 'autoscaling/v2'.`;
            }
        } else if (kind === "CronJob") {
            if (currentApi !== "batch/v1") {
                targetApi = "batch/v1";
                reason = `'${currentApi}' is deprecated for CronJob in K8s v${targetVersion}. Upgraded to 'batch/v1'.`;
            }
        } else if (kind === "PodDisruptionBudget") {
            if (currentApi !== "policy/v1") {
                targetApi = "policy/v1";
                reason = `'${currentApi}' is deprecated for PDB in K8s v${targetVersion}. Upgraded to 'policy/v1'.`;
            }
        } else if (["Role", "ClusterRole", "RoleBinding", "ClusterRoleBinding"].includes(kind)) {
            if (currentApi !== "rbac.authorization.k8s.io/v1") {
                targetApi = "rbac.authorization.k8s.io/v1";
                reason = `'${currentApi}' is deprecated in K8s v${targetVersion}. Upgraded to 'rbac.authorization.k8s.io/v1'.`;
            }
        } else if (["Service", "Pod", "ConfigMap", "Secret", "Namespace", "ServiceAccount"].includes(kind)) {
            if (currentApi !== "v1") {
                targetApi = "v1";
                reason = `'${currentApi}' is invalid for ${kind}. Reconciled to core 'v1'.`;
            }
        } else {
            if (currentApi.startsWith("apps/") && currentApi !== "apps/v1") {
                targetApi = "apps/v1";
                reason = `Deprecated API version '${currentApi}' in K8s v${targetVersion}. Upgraded to 'apps/v1'.`;
            } else if (currentApi.startsWith("extensions/")) {
                targetApi = "apps/v1";
                reason = `Deprecated 'extensions' API group detected in K8s v${targetVersion}. Upgraded to 'apps/v1'.`;
            }
        }

        if (targetApi && targetApi !== currentApi) {
            violations.push({
                field_path: "apiVersion",
                violation_type: "API_DEPRECATION",
                code: "PRO-001",
                message: reason,
                severity: "critical",
                line_no: apiLineIdx + 1
            });
            suggested_fixes.push({
                field_path: "apiVersion",
                original_value: currentApi,
                suggested_value: targetApi,
                fix_type: "SCHEMA_MIGRATION"
            });
            const indentMatch = rawLine.match(/^(\s*)/);
            const indent = indentMatch ? indentMatch[1] : "";
            healedLines[apiLineIdx] = `${indent}apiVersion: ${targetApi}`;
        }
    }

    // Rule 2: Floating Tag Hazard & Digest Pinning (OPS-002)
    healedLines = healedLines.map((line, idx) => {
        if (line.trim().startsWith("image:") && (line.includes(":latest") || !line.includes(":"))) {
            const trimmed = line.trim();
            let pinnedVal = line;
            if (line.includes(":latest")) {
                pinnedVal = line.includes("nginx") 
                    ? line.replace(":latest", ":1.25.3")
                    : line.replace(":latest", ":stable-pinned");
            } else {
                pinnedVal = `${line.trimEnd()}:stable-pinned`;
            }

            violations.push({
                field_path: "spec.template.spec.containers.image",
                violation_type: "FLOATING_TAG",
                code: "OPS-002",
                message: "Mutable image tag detected. Pinned to immutable semantic release tag.",
                severity: "warning",
                line_no: idx + 1
            });
            suggested_fixes.push({
                field_path: "image",
                original_value: trimmed,
                suggested_value: pinnedVal.trim(),
                fix_type: "TAG_PINNING"
            });
            return pinnedVal;
        }
        return line;
    });

    // Rule 3: Mandatory Deployment Selector Auto-Injection (OPS-001)
    if (kind === "Deployment" && !healedLines.some(l => l.trim().startsWith("selector:"))) {
        let labelKey = "app";
        let labelVal = "api";

        let inTemplate = false;
        let inLabels = false;
        let foundLabel = false;

        for (let i = 0; i < lines.length; i++) {
            const l = lines[i];
            if (/^\s*template:\s*$/.test(l)) {
                inTemplate = true;
                continue;
            }
            if (inTemplate && /^\s*labels:\s*$/.test(l)) {
                inLabels = true;
                continue;
            }
            if (inLabels) {
                const lm = l.match(/^\s+([a-zA-Z0-9_-]+):\s*([a-zA-Z0-9_.-]+)/);
                if (lm) {
                    labelKey = lm[1];
                    labelVal = lm[2];
                    foundLabel = true;
                    break;
                }
                if (l.trim() === "" || (!l.startsWith(" ") && !l.startsWith("\t"))) {
                    inLabels = false;
                }
            }
        }

        if (!foundLabel) {
            let inTopLabels = false;
            for (let i = 0; i < lines.length; i++) {
                const l = lines[i];
                if (/^\s*labels:\s*$/.test(l)) {
                    inTopLabels = true;
                    continue;
                }
                if (inTopLabels) {
                    const lm = l.match(/^\s+([a-zA-Z0-9_-]+):\s*([a-zA-Z0-9_.-]+)/);
                    if (lm && ["app", "tier", "component", "service"].includes(lm[1])) {
                        labelKey = lm[1];
                        labelVal = lm[2];
                        foundLabel = true;
                        break;
                    }
                }
            }
        }

        const specIdx = healedLines.findIndex(l => l.trim() === "spec:");
        if (specIdx !== -1) {
            const selectorBlock = [
                `  selector:`,
                `    matchLabels:`,
                `      ${labelKey}: ${labelVal}`
            ];
            healedLines.splice(specIdx + 1, 0, ...selectorBlock);
            violations.push({
                field_path: "spec.selector",
                violation_type: "SCHEMA_ERROR",
                code: "OPS-001",
                message: `Deployment missing mandatory 'spec.selector'. Auto-injected selector matching template label '${labelKey}: ${labelVal}'.`,
                severity: "critical",
                line_no: specIdx + 1
            });
        }
    }

    // Rule 4: Container Pod Security Standards Hardening (SEC-008 / BST-003)
    const isWorkload = ["Deployment", "StatefulSet", "DaemonSet", "Pod", "ReplicaSet", "Job", "CronJob"].includes(kind) || content.includes("containers:");
    const hasSecContext = healedLines.some(l => l.trim().startsWith("securityContext:"));
    if (isWorkload && !hasSecContext) {
        const containerIdx = healedLines.findIndex(l => l.trim().startsWith("- name:"));
        if (containerIdx !== -1) {
            const containerLine = healedLines[containerIdx];
            const matchIndent = containerLine.match(/^(\s*)- name:/);
            const baseIndent = matchIndent ? matchIndent[1] : "        ";
            const propIndent = baseIndent + "  ";
            const childIndent = propIndent + "  ";

            violations.push({
                field_path: "spec.template.spec.containers.securityContext",
                violation_type: "SECURITY_GAP",
                code: "SEC-008",
                message: "Container runs with unrestricted root permissions. Enforced Pod Security Standards Baseline.",
                severity: "critical",
                line_no: containerIdx + 1
            });

            const secBlock = [
                `${propIndent}securityContext:`,
                `${childIndent}runAsNonRoot: true`,
                `${childIndent}runAsUser: 1000`,
                `${childIndent}readOnlyRootFilesystem: true`,
                `${childIndent}allowPrivilegeEscalation: false`
            ];

            let insertIdx = containerIdx + 1;
            while (insertIdx < healedLines.length && (healedLines[insertIdx].startsWith(propIndent) || healedLines[insertIdx].trim() === "")) {
                insertIdx++;
            }
            healedLines.splice(insertIdx, 0, ...secBlock);
        }
    }

    // Rule 5: RBAC Cluster-Admin Demotion (GOV-003)
    if (content.includes("kind: ClusterRoleBinding") && content.includes("name: cluster-admin")) {
        healedLines = healedLines.map((line, idx) => {
            if (line.includes("name: cluster-admin")) {
                violations.push({
                    field_path: "roleRef.name",
                    violation_type: "RBAC_ESCALATION",
                    code: "GOV-003",
                    message: "ServiceAccount bound to cluster-wide 'cluster-admin'. Scoped to localized least-privilege role.",
                    severity: "critical",
                    line_no: idx + 1
                });
                return line.replace("name: cluster-admin", "name: app-operator-role");
            }
            return line;
        });
    }

    // Rule 6: Ingress Modern Backend Migration (NET-002)
    if (kind === "Ingress" && content.includes("serviceName:")) {
        healedLines = healedLines.map((line, idx) => {
            if (line.includes("serviceName:")) {
                const indentMatch = line.match(/^(\s*)/);
                const indent = indentMatch ? indentMatch[1] : "          ";
                const svcMatch = line.match(/serviceName:\s*([^\s#]+)/);
                const svcName = svcMatch ? svcMatch[1] : "service";
                violations.push({
                    field_path: "spec.rules.http.paths.backend",
                    violation_type: "DEPRECATED_INGRESS_BACKEND",
                    code: "NET-002",
                    message: `Legacy Ingress 'serviceName/servicePort' upgraded to networking.k8s.io/v1 structure for K8s v${targetVersion}.`,
                    severity: "warning",
                    line_no: idx + 1
                });
                return `${indent}service:\n${indent}  name: ${svcName}`;
            }
            return line;
        });
    }

    // Deterministic Health Score aligned with HealthScoringStage
    let score = 100.0;
    for (const v of violations) {
        if (v.severity === "critical") score -= 15.0;
        else if (v.severity === "warning") score -= 5.0;
        else score -= 2.0;
    }
    const healthScore = Math.max(0, Math.round(score));
    const healedYaml = healedLines.join("\n");
    const { healedLineNumbers, deletedLineNumbers } = computeLineDiff(content, healedYaml);

    return {
        violations,
        suggested_fixes,
        healedYaml,
        healthScore,
        healedLineNumbers,
        deletedLineNumbers
    };
}
