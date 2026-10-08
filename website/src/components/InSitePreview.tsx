"use client";

import { useState, useEffect } from "react";
import { FileCode, ShieldCheck, FileText, ChevronRight, AlertTriangle, CheckCircle2, Play } from "lucide-react";

const PRESETS = [
    {
        id: "opa",
        label: "Scenario: OPA Violation",
        yaml: "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-frontend\nspec:\n  template:\n    spec:\n      containers:\n      - name: nginx\n        image: nginx:latest",
        report: "# Evidence Report: web-frontend\n**Status:** ⚠️ OPA POLICY VIOLATION\n\n## Findings\n- **rule/no-latest-tag**: Container uses 'nginx:latest'.\n- **rule/run-as-non-root**: Pod securityContext missing.\n\n## Remediation Plan\nYamlr will pin 'nginx:latest' to 'stable' and inject CIS-compliant securityContext.",
        diff: "  containers:\n  - name: nginx\n-   image: nginx:latest\n+   image: nginx:stable\n+   securityContext:\n+     runAsNonRoot: true\n+     runAsUser: 1000\n+     readOnlyRootFilesystem: true"
    },
    {
        id: "structural",
        label: "Scenario: Structural Error",
        yaml: "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-service\nspec:\n  ports:\n    port: 80\n    targetPort: 8080",
        report: "# Evidence Report: my-service\n**Status:** ⚠️ SCHEMA VALIDATION FAILED\n\n## Findings\n- **schema/type-error**: 'spec.ports' must be an array, but found object.\n\n## Remediation Plan\nYamlr will cast 'spec.ports' to a list according to K8s v1.31 OpenAPI spec.",
        diff: "  spec:\n-   ports:\n-     port: 80\n-     targetPort: 8080\n+   ports:\n+     - port: 80\n+       targetPort: 8080"
    },
    {
        id: "ghost",
        label: "Scenario: Dependency Ghost",
        yaml: "apiVersion: v1\nkind: Pod\nmetadata:\n  name: app-pod\nspec:\n  containers:\n  - name: app\n    image: myapp:1.0\n    envFrom:\n    - configMapRef:\n        name: legacy-config",
        report: "# Evidence Report: app-pod\n**Status:** ⚠️ BROKEN DEPENDENCY\n\n## Findings\n- **graph/ghost-reference**: Pod references ConfigMap 'legacy-config' which does not exist in the repository.\n\n## Remediation Plan\nYamlr detected a renamed ConfigMap ('app-config-v2'). Applying relational surgery to fix broken reference.",
        diff: "  containers:\n  - name: app\n    image: myapp:1.0\n    envFrom:\n    - configMapRef:\n-         name: legacy-config\n+         name: app-config-v2"
    }
];

export default function InSitePreview() {
    const [tab, setTab] = useState<"yaml" | "report" | "diff">("yaml");
    const [activePresetId, setActivePresetId] = useState("opa");

    const activePreset = PRESETS.find(p => p.id === activePresetId) || PRESETS[0];

    useEffect(() => {
        // Auto-run first scenario on land to prevent blank screen
        const timer1 = setTimeout(() => setTab("report"), 1000);
        const timer2 = setTimeout(() => setTab("diff"), 2000);
        return () => { clearTimeout(timer1); clearTimeout(timer2); };
    }, []);

    const handleLoadPreset = (id: string) => {
        setActivePresetId(id);
        setTab("yaml"); // Reset to YAML view to let them "run" it again

        // Auto-switch to report then diff to simulate animation
        setTimeout(() => setTab("report"), 800);
        setTimeout(() => setTab("diff"), 1600);
    };

    return (
        <section id="preview" className="py-24 relative overflow-hidden bg-slate-50">
            <div className="container mx-auto px-6 max-w-6xl">
                <div className="text-center mb-10">
                    <h2 className="text-3xl md:text-5xl font-bold font-outfit tracking-tight text-slate-900 mb-4">
                        Simulate the Engine
                    </h2>
                    <p className="text-slate-600 max-w-2xl mx-auto text-lg">
                        Select a realistic failure scenario below to see how Yamlr heals it.
                    </p>
                </div>

                {/* Preset Controls */}
                <div className="flex flex-wrap justify-center gap-3 mb-10">
                    {PRESETS.map((preset) => (
                        <button
                            key={preset.id}
                            onClick={() => handleLoadPreset(preset.id)}
                            className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-bold text-sm transition-all focus:outline-none focus:ring-2 focus:ring-[#4285F4] focus:ring-offset-2 ${activePresetId === preset.id
                                ? "bg-[#4285F4] text-white shadow-lg shadow-blue-500/20"
                                : "bg-white text-slate-600 border border-slate-200 hover:border-[#4285F4]/30 hover:text-[#4285F4] hover:shadow-sm"
                                }`}
                        >
                            <Play size={12} className={activePresetId === preset.id ? "fill-white" : "fill-transparent"} />
                            {preset.label}
                        </button>
                    ))}
                </div>

                <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl shadow-sky-900/5 overflow-hidden flex flex-col md:flex-row h-[600px] transition-all">
                    {/* Sidebar Nav */}
                    <div className="w-full md:w-64 bg-slate-50 border-r border-slate-200 p-4 space-y-2">
                        <button
                            onClick={() => setTab("yaml")}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${tab === "yaml" ? "bg-white text-[#4285F4] shadow-sm border border-slate-200" : "text-slate-500 hover:text-slate-900"}`}
                        >
                            <FileCode size={18} />
                            <span className="font-bold text-sm">Source YAML</span>
                            {tab === "yaml" && <ChevronRight size={14} className="ml-auto" />}
                        </button>
                        <button
                            onClick={() => setTab("report")}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${tab === "report" ? "bg-white text-[#4285F4] shadow-sm border border-slate-200" : "text-slate-500 hover:text-slate-900"}`}
                        >
                            <FileText size={18} />
                            <span className="font-bold text-sm">Audit Report</span>
                            {tab === "report" && <ChevronRight size={14} className="ml-auto" />}
                        </button>
                        <button
                            onClick={() => setTab("diff")}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${tab === "diff" ? "bg-white text-emerald-600 shadow-sm border border-emerald-100" : "text-slate-500 hover:text-slate-900"}`}
                        >
                            <ShieldCheck size={18} />
                            <span className="font-bold text-sm">Healed Diff</span>
                            {tab === "diff" && <ChevronRight size={14} className="ml-auto" />}
                        </button>

                        <div className="mt-auto pt-8 px-4 hidden md:block">
                            <div className="p-4 rounded-2xl bg-sky-50 border border-sky-100 text-[11px] text-sky-800 leading-relaxed">
                                Built against the official K8s v1.31 OpenAPI specification.
                            </div>
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 bg-white relative flex flex-col">
                        {/* Status Header */}
                        <div className="px-8 py-4 bg-slate-50/50 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4">
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${tab === "diff" ? "bg-emerald-500" : tab === "report" ? "bg-amber-500" : "bg-sky-500"}`} />
                                <span className="text-[11px] uppercase font-bold tracking-widest text-slate-500">
                                    {tab === "yaml" ? "Input Mode" : tab === "report" ? "Evidence Generated" : "Repair Validated"}
                                </span>
                            </div>

                            {/* Instant Result Summary (DevTool Reviewer Feedback) */}
                            {tab !== "yaml" && (
                                <div className="flex gap-4 text-xs font-bold text-slate-700 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <span className="flex items-center gap-1.5"><ShieldCheck size={14} className="text-emerald-500" /> 1 Auto Fix</span>
                                    <span className="flex items-center gap-1.5"><AlertTriangle size={14} className="text-rose-500" /> 1 Policy Issue</span>
                                </div>
                            )}

                            <div className="text-[11px] text-slate-400 font-mono hidden sm:block">target.yaml</div>
                        </div>

                        {/* Scrolling Content */}
                        <div className="flex-1 overflow-auto p-8 font-mono text-sm leading-relaxed">
                            {tab === "yaml" && (
                                <div className="relative h-full animate-in fade-in duration-300">
                                    <textarea
                                        readOnly
                                        className="w-full h-full resize-none outline-none text-slate-700 bg-transparent selection:bg-sky-100 selection:text-sky-900"
                                        value={activePreset.yaml}
                                    />
                                </div>
                            )}
                            {tab === "report" && (
                                <div className="space-y-6 animate-in fade-in slide-in-from-right-2 duration-300">
                                    <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-100 rounded-xl text-amber-900">
                                        <AlertTriangle size={20} />
                                        <span className="font-bold">Misconfiguration Detected</span>
                                    </div>
                                    <pre className="text-slate-700 whitespace-pre-wrap">{activePreset.report}</pre>
                                </div>
                            )}
                            {tab === "diff" && (
                                <div className="space-y-6 animate-in fade-in slide-in-from-right-2 duration-300">
                                    <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-100 rounded-xl text-emerald-900">
                                        <CheckCircle2 size={20} />
                                        <span className="font-bold">Fix Applied — Preview Below</span>
                                    </div>
                                    <div className="bg-slate-900 rounded-xl p-6 text-slate-300">
                                        <pre>
                                            {activePreset.diff.split('\\n').map((line, i) => (
                                                <div key={i} className={line.startsWith('+') ? "text-emerald-400 bg-emerald-400/10" : line.startsWith('-') ? "text-rose-400 bg-rose-400/10" : ""}>
                                                    {line}
                                                </div>
                                            ))}
                                        </pre>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Interactive Hint */}
                        <div className="px-8 py-4 border-t border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-2">
                            <span className="text-[11px] text-slate-500">In production, Yamlr runs 100% locally on your machine with zero data egress.</span>
                            <div className="flex gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                                <div className="w-1.5 h-1.5 rounded-full bg-slate-300 shadow-[0_0_8px_rgba(0,0,0,0.1)]" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
