/**
 * Structural & Misnested Field Lifter (Feature 3 Parity for Browser Sandbox).
 * Lifts container fields (ports, resources, probes) out of envFrom items,
 * and fixes misplaced structures in browser preview.
 */

import { WasmViolation } from "../WasmBridge";

const MISNESTED_KEYS = [
    "ports", "resources", "livenessProbe", "readinessProbe",
    "startupProbe", "securityContext", "volumeMounts"
];

export function healStructuralIssues(lines: string[]): {
    healedLines: string[];
    violations: WasmViolation[];
} {
    const healedLines = [...lines];
    const violations: WasmViolation[] = [];
    let insideEnvFrom = false;
    let envFromIndent = -1;
    let containerIndent = -1;

    for (let i = 0; i < healedLines.length; i++) {
        const line = healedLines[i];
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("---")) continue;

        const indentMatch = line.match(/^(\s*)/);
        const indent = indentMatch ? indentMatch[1].length : 0;

        // Container tracking
        if (/^-\s+name:\s*/.test(trimmed)) {
            containerIndent = indent;
            insideEnvFrom = false;
        }

        if (/^envFrom:\s*$/.test(trimmed)) {
            insideEnvFrom = true;
            envFromIndent = indent;
            continue;
        }

        if (insideEnvFrom) {
            // If indent dropped below or equal to envFrom, we exited envFrom
            if (indent <= envFromIndent && !trimmed.startsWith("-")) {
                insideEnvFrom = false;
            } else {
                // Check if key is a misnested container field
                for (const key of MISNESTED_KEYS) {
                    const regex = new RegExp(`^${key}:`);
                    if (regex.test(trimmed)) {
                        // Lift to container indent + 2
                        const newIndent = containerIndent >= 0 ? containerIndent + 2 : envFromIndent;
                        healedLines[i] = `${" ".repeat(newIndent)}${trimmed}`;
                        violations.push({
                            field_path: `containers[].${key}`,
                            violation_type: "STRUCTURAL_ERROR",
                            code: "STRUCT-001",
                            message: `Misnested property '${key}' inside envFrom item. Lifted to container level.`,
                            severity: "critical",
                            line_no: i + 1
                        });
                        break;
                    }
                }
            }
        }
    }

    return { healedLines, violations };
}
