"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { Play, RotateCcw, Download, Trash2 } from "lucide-react";
import { SCENARIOS } from "@/data/scenarios";
import { runAudit, computeLineDiff, isWasmReady, WasmAuditResult } from "./WasmBridge";
import ScenarioTabs from "./sandbox/ScenarioTabs";
import EditorPane from "./sandbox/EditorPane";
import DiagnosticDashboard, { FindingItem } from "./sandbox/DiagnosticDashboard";

type SandboxStatus = "IDLE" | "ANALYZING" | "VERIFIED";
type SeverityFilter = "ALL" | "critical" | "warning" | "info";

const DEFAULT_SAMPLE_YAML = `# Kubernetes Production Deployment with Deprecations & Gaps
apiVersion: apps/v1beta1
kind: Deploymen
metadata:
  name: api-service
  labels:
    app: api
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: nginx:latest
        ports:
        - containerPort: 80
`;

const K8S_VERSIONS = ["1.28", "1.29", "1.30", "1.31", "1.32"];

export default function Playground() {
    // Default active scenario is the flagship Security Hardening scenario
    const [activeId, setActiveId] = useState<string>("security");
    const [status, setStatus] = useState<SandboxStatus>("IDLE");
    const [auditResult, setAuditResult] = useState<WasmAuditResult | null>(null);
    const [customYaml, setCustomYaml] = useState<string>(DEFAULT_SAMPLE_YAML);
    const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
    const [targetK8sVersion, setTargetK8sVersion] = useState<string>("1.30");
    const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
    const [copiedHealed, setCopiedHealed] = useState(false);
    const [copiedOriginal, setCopiedOriginal] = useState(false);
    const [isModifiedSinceRun, setIsModifiedSinceRun] = useState(false);
    const [isMac, setIsMac] = useState(false);
    const [wasmActive, setWasmActive] = useState(false);

    const sourceScrollRef = useRef<HTMLDivElement>(null);
    const healedScrollRef = useRef<HTMLDivElement>(null);
    const isSyncingScroll = useRef(false);

    const isCustom = activeId === "custom";
    const activeScenario = SCENARIOS.find((s) => s.id === activeId) || SCENARIOS[0];

    useEffect(() => {
        if (typeof window !== "undefined") {
            setIsMac(/(mac|iphone|ipad)/i.test(navigator.userAgent));
            setWasmActive(isWasmReady());
        }
    }, []);

    const modifierKey = isMac ? "⌘" : "Ctrl";

    // Reset state when switching scenario tabs
    useEffect(() => {
        setStatus("IDLE");
        setAuditResult(null);
        setIsModifiedSinceRun(false);
        setSeverityFilter("ALL");
    }, [activeId]);

    // Keyboard shortcut to run analysis
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                handleRunAnalysis();
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isCustom, customYaml, activeScenario, targetK8sVersion]);

    const handleRunAnalysis = async () => {
        setStatus("ANALYZING");
        setIsModifiedSinceRun(false);

        const targetContent = isCustom ? customYaml : activeScenario.original;
        const result = await runAudit(targetContent, targetK8sVersion);
        setAuditResult(result);
        setStatus("VERIFIED");
    };

    const handleScrollSync = (source: "source" | "healed") => {
        if (isSyncingScroll.current) return;
        isSyncingScroll.current = true;

        const srcEl = source === "source" ? sourceScrollRef.current : healedScrollRef.current;
        const dstEl = source === "source" ? healedScrollRef.current : sourceScrollRef.current;

        if (srcEl && dstEl) {
            dstEl.scrollTop = srcEl.scrollTop;
            dstEl.scrollLeft = srcEl.scrollLeft;
        }

        requestAnimationFrame(() => {
            isSyncingScroll.current = false;
        });
    };

    const handleDropFile = (text: string, name: string) => {
        setCustomYaml(text);
        setUploadedFileName(name);
        setActiveId("custom");
        setStatus("IDLE");
        setAuditResult(null);
        setIsModifiedSinceRun(false);
    };

    const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (event) => {
                const text = event.target?.result as string;
                if (text) handleDropFile(text, file.name);
            };
            reader.readAsText(file);
            e.target.value = "";
        }
    };

    const handleClear = () => {
        setCustomYaml("");
        setUploadedFileName(null);
        setStatus("IDLE");
        setAuditResult(null);
        setIsModifiedSinceRun(false);
    };

    const handleLoadSample = () => {
        setCustomYaml(DEFAULT_SAMPLE_YAML);
        setUploadedFileName(null);
        setStatus("IDLE");
        setAuditResult(null);
        setIsModifiedSinceRun(false);
    };

    const handleDownload = (filename: string, content: string) => {
        const element = document.createElement("a");
        const file = new Blob([content], { type: "text/yaml" });
        element.href = URL.createObjectURL(file);
        element.download = filename;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    };

    // Filename Parity: Left and Right panes show the exact same filename
    const currentFileName = isCustom
        ? uploadedFileName || "deployment.yaml"
        : `${activeScenario.id}.yaml`;

    const currentOriginalContent = isCustom ? customYaml : activeScenario.original;
    const currentHealedContent = isCustom
        ? auditResult?.healedYaml || ""
        : activeScenario.healed;

    // Diff line calculations
    const scenarioDiff = !isCustom ? computeLineDiff(activeScenario.original, activeScenario.healed) : null;
    const healedLinesSet = new Set<number>(
        isCustom
            ? auditResult?.healedLineNumbers ?? []
            : scenarioDiff?.healedLineNumbers ?? activeScenario.highlights
    );
    const deletedLinesSet = new Set<number>(
        isCustom
            ? auditResult?.deletedLineNumbers ?? []
            : scenarioDiff?.deletedLineNumbers ?? activeScenario.deletions
    );

    // Aggregate findings for scalable display (supporting 20-100+ violations)
    const findings: FindingItem[] = useMemo(() => {
        if (isCustom) {
            return (auditResult?.violations || []).map((v, idx) => ({
                id: `v-${idx}`,
                code: v.code,
                title: v.violation_type.replace(/_/g, " "),
                description: v.message,
                severity: v.severity,
                field_path: v.field_path
            }));
        }
        return activeScenario.findings.map((f) => ({
            id: f.id,
            code: f.code,
            title: f.title,
            description: f.description,
            severity: f.severity,
            field_path: "manifest"
        }));
    }, [isCustom, auditResult, activeScenario]);

    const computedScore = isCustom
        ? auditResult?.healthScore ?? 100
        : Math.max(20, 100 - activeScenario.findings.length * 15);

    return (
        <section className="py-8 md:py-10 bg-white dark:bg-[#0D1117] border-b border-slate-200 dark:border-slate-800">
            <h2 className="sr-only">Yamlr Live Manifest Sandbox</h2>
            <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
                {/* Scenario Tabs Strip */}
                <ScenarioTabs
                    scenarios={SCENARIOS}
                    activeId={activeId}
                    onSelectScenario={setActiveId}
                    targetK8sVersion={targetK8sVersion}
                    isCustom={isCustom}
                    activeScenario={activeScenario}
                />

                {/* Persistent Action Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 bg-slate-900 rounded-2xl border border-slate-800 text-white mb-4 shadow-md">
                    <div className="flex flex-wrap items-center gap-2.5">
                        <button
                            onClick={handleRunAnalysis}
                            disabled={status === "ANALYZING"}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#4285F4] hover:bg-[#3367D6] text-white text-xs font-bold transition-all shadow-md active:scale-95 disabled:opacity-50"
                        >
                            <Play size={14} fill="currentColor" />
                            <span>{status === "ANALYZING" ? "Healing Manifest..." : "Heal Manifest"}</span>
                            <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded bg-white/20 text-white/90 font-mono text-[10px] ml-1 font-semibold">
                                {modifierKey}+Enter
                            </span>
                        </button>

                        {isCustom && (
                            <>
                                <button
                                    onClick={handleLoadSample}
                                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-colors border border-slate-700"
                                    title="Load standard sample deployment"
                                >
                                    <RotateCcw size={13} />
                                    Load Sample
                                </button>
                                <button
                                    onClick={handleClear}
                                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-colors border border-slate-700"
                                    title="Clear editor canvas"
                                >
                                    <Trash2 size={13} />
                                    Clear
                                </button>
                            </>
                        )}

                        {status === "VERIFIED" && (
                            <button
                                onClick={() => handleDownload(currentFileName, currentHealedContent)}
                                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-colors border border-slate-700"
                                title="Download healed YAML file"
                            >
                                <Download size={13} />
                                Download Healed
                            </button>
                        )}

                        {isModifiedSinceRun && (
                            <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 rounded-lg animate-pulse">
                                Buffer modified — Click Heal Manifest to re-evaluate
                            </span>
                        )}
                    </div>

                    {/* Target K8s Version Selector & Live Score */}
                    <div className="flex items-center gap-3">
                        <div className="hidden sm:flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl px-2.5 py-1 text-[11px] text-slate-300">
                            <span className={`w-2 h-2 rounded-full ${wasmActive ? "bg-emerald-400 animate-pulse" : "bg-blue-400"}`} />
                            <span className="font-mono">{wasmActive ? "WASM: Native" : "AST Engine"}</span>
                        </div>

                        <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-xl px-2.5 py-1 text-xs text-slate-300">
                            <span className="text-[11px] text-slate-400 font-medium">Target K8s:</span>
                            <select
                                value={targetK8sVersion}
                                onChange={(e) => setTargetK8sVersion(e.target.value)}
                                className="bg-transparent text-white font-bold text-xs outline-none cursor-pointer"
                                title="Select Kubernetes target version for schema validation"
                            >
                                {K8S_VERSIONS.map((v) => (
                                    <option key={v} value={v} className="bg-slate-900 text-white">
                                        v{v}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div
                            className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                                status === "VERIFIED"
                                    ? "bg-emerald-500/15 border border-emerald-500/30 text-emerald-400"
                                    : "bg-slate-800 text-slate-400 border border-slate-700"
                            }`}
                        >
                            {status === "VERIFIED" ? `Score: ${computedScore}%` : "Awaiting Scan"}
                        </div>
                    </div>
                </div>

                {/* 50/50 Dual-Pane Code Canvas with Physical Gap Separation */}
                <div className="grid md:grid-cols-2 gap-6 lg:gap-8 mb-6">
                    {/* Left Pane: Original Source Buffer */}
                    <EditorPane
                        type="ORIGINAL"
                        fileName={currentFileName}
                        content={currentOriginalContent}
                        status={status}
                        isCustom={isCustom}
                        modifierKey={modifierKey}
                        targetK8sVersion={targetK8sVersion}
                        healedLinesSet={healedLinesSet}
                        deletedLinesSet={deletedLinesSet}
                        scrollRef={sourceScrollRef}
                        onScroll={() => handleScrollSync("source")}
                        customYaml={customYaml}
                        onCustomYamlChange={(val) => {
                            setCustomYaml(val);
                            setIsModifiedSinceRun(true);
                        }}
                        onLoadSample={handleLoadSample}
                        onFileInput={handleFileInput}
                        onDropFile={handleDropFile}
                        copied={copiedOriginal}
                        onCopy={() => {
                            navigator.clipboard.writeText(currentOriginalContent);
                            setCopiedOriginal(true);
                            setTimeout(() => setCopiedOriginal(false), 2000);
                        }}
                    />

                    {/* Right Pane: Healed CST State */}
                    <EditorPane
                        type="HEALED"
                        fileName={currentFileName}
                        content={currentHealedContent}
                        status={status}
                        isCustom={isCustom}
                        modifierKey={modifierKey}
                        targetK8sVersion={targetK8sVersion}
                        healedLinesSet={healedLinesSet}
                        deletedLinesSet={deletedLinesSet}
                        scrollRef={healedScrollRef}
                        onScroll={() => handleScrollSync("healed")}
                        onRunAnalysis={handleRunAnalysis}
                        copied={copiedHealed}
                        onCopy={() => {
                            navigator.clipboard.writeText(currentHealedContent);
                            setCopiedHealed(true);
                            setTimeout(() => setCopiedHealed(false), 2000);
                        }}
                    />
                </div>

                {/* Diagnostic Dashboard (Scalable to 100+ Violations) */}
                <DiagnosticDashboard
                    status={status}
                    findings={findings}
                    targetK8sVersion={targetK8sVersion}
                    severityFilter={severityFilter}
                    onSeverityFilterChange={setSeverityFilter}
                />
            </div>
        </section>
    );
}
