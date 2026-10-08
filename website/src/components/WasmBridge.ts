/**
 * Client-Side WebAssembly Bridge for Yamlr Sandbox.
 *
 * Why: Loads the compiled Rust WASM binary (yamlr_native.wasm) directly in
 * the browser for zero-latency, private manifest validation and healing.
 * Falls back gracefully to the deterministic client forensic engine if WASM
 * is unavailable or disabled.
 */

import {
    WasmViolation,
    WasmFix,
    WasmAuditResult,
    computeLineDiff,
    executeClientForensicEngine
} from "@/components/sandbox/clientForensicEngine";

export type { WasmViolation, WasmFix, WasmAuditResult };
export { computeLineDiff };

let wasmInitPromise: Promise<boolean> | null = null;
let isWasmLoaded = false;

/**
 * Initializes the WebAssembly module from public assets if available.
 */
export async function initWasm(): Promise<boolean> {
    if (typeof window === "undefined") return false;
    // @ts-ignore
    if (window.__yamlr_wasm || isWasmLoaded) return true;

    if (!wasmInitPromise) {
        wasmInitPromise = (async () => {
            try {
                // Dynamically import the compiled WASM package from /wasm/yamlr_native.js
                // @ts-ignore
                const wasmPath = "/wasm/yamlr_native.js";
                // @ts-ignore
                const wasm = await import(/* webpackIgnore: true */ wasmPath);
                if (wasm && typeof wasm.default === "function") {
                    await wasm.default();
                    // @ts-ignore
                    window.__yamlr_wasm = wasm;
                    isWasmLoaded = true;
                    return true;
                }
                return false;
            } catch {
                return false;
            }
        })();
    }

    return wasmInitPromise;
}

/**
 * Returns whether the WebAssembly native engine is currently initialized.
 */
export function isWasmReady(): boolean {
    // @ts-ignore
    return Boolean(typeof window !== "undefined" && (window.__yamlr_wasm || isWasmLoaded));
}

/**
 * Executes manifest audit and auto-repair using native Rust WASM when available,
 * falling back to client-side forensic evaluator.
 */
export async function runAudit(content: string, targetVersion: string = "1.30"): Promise<WasmAuditResult> {
    try {
        await initWasm();

        // @ts-ignore
        const wasm = typeof window !== "undefined" ? window.__yamlr_wasm : null;
        if (wasm && typeof wasm.wasm_heal === "function" && typeof wasm.wasm_scan === "function") {
            // Lazy load schema if supported and not yet loaded
            if (typeof wasm.wasm_has_schema === "function" && typeof wasm.wasm_load_schema === "function") {
                if (!wasm.wasm_has_schema(targetVersion)) {
                    try {
                        const schemaRes = await fetch(`/schemas/k8s_v${targetVersion}.json`);
                        if (schemaRes.ok) {
                            const schemaJson = await schemaRes.text();
                            wasm.wasm_load_schema(targetVersion, schemaJson);
                        }
                    } catch {
                        // Continue even if remote schema fetch fails
                    }
                }
            }

            const scanJson = wasm.wasm_scan(content);
            const healJson = wasm.wasm_heal(content);

            const scanResult = JSON.parse(scanJson);
            const healResult = JSON.parse(healJson);

            const violations: WasmViolation[] = (scanResult || []).map((v: any) => ({
                field_path: "",
                violation_type: v.check_name || "WasmScanViolation",
                code: v.rule_id || "WASM-001",
                message: v.message || "",
                severity: v.severity?.toLowerCase() === "error" || v.severity?.toLowerCase() === "critical" ? "critical" : "warning",
                line_no: v.line_no || 1,
            }));

            const suggested_fixes: WasmFix[] = (healResult.changes || []).map((c: string) => ({
                field_path: "",
                original_value: "",
                suggested_value: c,
                fix_type: "AutoRepair",
            }));

            const healedYaml = healResult.healed_yaml || content;
            const { healedLineNumbers, deletedLineNumbers } = computeLineDiff(content, healedYaml);
            const healthScore = Math.max(0, 100 - violations.length * 15);

            return {
                violations,
                suggested_fixes,
                healedYaml,
                healthScore,
                healedLineNumbers,
                deletedLineNumbers,
            };
        }
    } catch {
        // Fallback gracefully on any WASM execution or parse error
    }

    return executeClientForensicEngine(content, targetVersion);
}
