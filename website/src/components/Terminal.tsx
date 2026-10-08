"use client";

import { useState, useEffect, useRef } from "react";
import { RotateCcw } from "lucide-react";

const SCAN_STEPS = [
    { line: "yamlr scan ./manifests/ --k8s-version 1.31", type: "command" },
    { line: "[SCAN] Target K8s: v1.31 | Rust Native Core Engine", color: "text-sky-400" },
    { line: "[SCAN] Parallel scanning 12 files across ./manifests/", color: "text-emerald-400" },
    { line: "--------------------------------------------------------------------------------", color: "text-slate-600" },
    { line: "  [!] DAN-001 | ./manifests/frontend-svc.yaml:12 | Dangling selector 'app=frontend' matches 0 Pods", color: "text-rose-400" },
    { line: "      Target: Aligned selector to match Deployment spec.template.labels", color: "text-slate-500" },
    { line: "  [!] REF-001 | ./manifests/api-server.yaml:34 | Unresolved reference to Secret 'db-creds'", color: "text-rose-400" },
    { line: "      Target: Inject synthetic Secret stub or rectify credential binding", color: "text-slate-500" },
    { line: "  [!] PRO-001 | ./manifests/ingress.yaml:18 | Deprecated apiVersion 'extensions/v1beta1'", color: "text-amber-400" },
    { line: "      Target: Migrated to 'networking.k8s.io/v1' schema specification", color: "text-slate-500" },
    { line: "  [!] SEC-008 | ./manifests/deploy.yaml:28 | Root container execution without securityContext", color: "text-amber-400" },
    { line: "--------------------------------------------------------------------------------", color: "text-slate-600" },
    { line: "Summary: 12 files scanned | 4 violations detected | 0 critical errors | 4.8ms", color: "text-sky-400" },
    { line: "Next step: Run 'yamlr heal ./manifests/ --diff' to preview surgical auto-fixes", color: "text-slate-400" },
];

const DIFF_STEPS = [
    { line: "yamlr heal deploy.yaml --diff", type: "command" },
    { line: "[DIFF] Target K8s: v1.31 | AST Layout-Preserving Diff Preview", color: "text-sky-400" },
    { line: "--- deploy.yaml (original)", color: "text-slate-500" },
    { line: "+++ deploy.yaml (healed)", color: "text-slate-500" },
    { line: "@@ -26,6 +26,10 @@", color: "text-cyan-400" },
    { line: "     spec:", color: "text-slate-500" },
    { line: "       containers:", color: "text-slate-500" },
    { line: "       - name: nginx", color: "text-slate-500" },
    { line: " -       image: nginx:latest", color: "text-rose-400 bg-rose-400/10" },
    { line: " +       image: nginx:1.25.3 # Healed: pinned immutable semantic release tag", color: "text-emerald-400 bg-emerald-400/10" },
    { line: " +       securityContext:", color: "text-emerald-400 bg-emerald-400/10" },
    { line: " +         runAsNonRoot: true", color: "text-emerald-400 bg-emerald-400/10" },
    { line: " +         readOnlyRootFilesystem: true", color: "text-emerald-400 bg-emerald-400/10" },
    { line: "--------------------------------------------------------------------------------", color: "text-slate-600" },
    { line: "[DIFF] 1 file analyzed | 2 proposed mutations | 0 files written (safe dry-run)", color: "text-sky-400" },
];

const HEAL_STEPS = [
    { line: "yamlr heal deploy.yaml --apply", type: "command" },
    { line: "[HEAL] Target K8s: v1.31 | Applying atomic remediation with comment preservation", color: "text-sky-400" },
    { line: "[PROPOSED FIX] Pinned floating image tag 'nginx:latest' -> 'nginx:1.25.3'", color: "text-emerald-400" },
    { line: "[PROPOSED FIX] Injected hardened Pod Security Standards securityContext", color: "text-emerald-400" },
    { line: "[JOURNAL] Remediation audit transaction logged to .yamlr/journal.log", color: "text-slate-500" },
    { line: "--------------------------------------------------------------------------------", color: "text-slate-600" },
    { line: "  ✓ deploy.yaml healed successfully in 2.1ms (100% human comments & formatting preserved)", color: "text-emerald-400" },
    { line: "[EVIDENCE] Attestation signed and stored in .yamlr/vault/", color: "text-sky-400" },
];

type TabKey = "scan" | "diff" | "heal";

export default function TerminalDisplay() {
    const [activeTab, setActiveTab] = useState<TabKey>("scan");
    const [visibleLines, setVisibleLines] = useState<number>(0);
    const [typingText, setTypingText] = useState("");
    const [isDone, setIsDone] = useState(false);
    const [userInteracted, setUserInteracted] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    const steps = activeTab === "heal" ? HEAL_STEPS : activeTab === "diff" ? DIFF_STEPS : SCAN_STEPS;
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-cycle tabs logic (pauses if user interacted or is hovering)
    useEffect(() => {
        if (userInteracted || isHovered) return;
        const tabs: TabKey[] = ["scan", "diff", "heal"];
        const interval = setInterval(() => {
            setActiveTab(prev => {
                const nextIdx = (tabs.indexOf(prev) + 1) % tabs.length;
                return tabs[nextIdx];
            });
        }, 5000);
        return () => clearInterval(interval);
    }, [userInteracted, isHovered]);

    useEffect(() => {
        setVisibleLines(0);
        setTypingText("");
        setIsDone(false);
    }, [activeTab]);

    useEffect(() => {
        if (visibleLines < steps.length) {
            const step = steps[visibleLines];

            if (step.type === "command" && typingText.length < step.line.length) {
                const timer = setTimeout(() => {
                    setTypingText(step.line.slice(0, typingText.length + 1));
                }, 40);
                return () => clearTimeout(timer);
            } else {
                const timer = setTimeout(() => {
                    setVisibleLines(v => v + 1);
                    if (step.type === "command") setTypingText("");
                }, step.type === "command" ? 200 : 80);
                return () => clearTimeout(timer);
            }
        } else {
            setIsDone(true);
        }
    }, [visibleLines, typingText, steps]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [visibleLines, typingText]);

    return (
        <div 
            className="max-w-4xl mx-auto rounded-2xl overflow-hidden shadow-2xl shadow-slate-900/20 dark:shadow-black/80 border border-slate-200 dark:border-white/10 bg-[#09090b] relative"
            role="region"
            aria-label="yamlr. CLI Interactive Demo"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >

            {/* Tab bar */}
            <div className="h-14 bg-[#09090b] border-b border-white/5 flex items-center justify-between px-6">
                <div className="flex items-center gap-8">
                    {/* Traffic lights removed for a sleek dev aesthetic */}

                    <div className="flex bg-slate-900/50 p-1.5 rounded-xl border border-white/5">
                        {(["scan", "diff", "heal"] as TabKey[]).map((tab) => (
                            <button
                                key={tab}
                                onClick={() => {
                                    setActiveTab(tab);
                                    setUserInteracted(true);
                                }}
                                className={`px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold uppercase tracking-widest transition-all focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] ${
                                    activeTab === tab
                                        ? "bg-[#4285F4] text-white shadow-lg shadow-blue-500/20"
                                        : "text-slate-300 hover:text-white hover:bg-white/10"
                                }`}
                            >
                                <span className={activeTab === tab ? "opacity-90 font-medium" : "text-slate-400 font-medium"}>yamlr</span>{" "}
                                <span className={activeTab === tab ? "font-bold" : "text-slate-100 font-bold"}>{tab}</span>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {isDone && (
                        <button
                            onClick={() => { setVisibleLines(0); setTypingText(""); setIsDone(false); }}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold text-slate-500 hover:text-white hover:bg-white/5 transition-all"
                        >
                            <RotateCcw size={14} />
                            Replay
                        </button>
                    )}
                </div>
            </div>

            {/* Terminal body */}
            <div
                ref={scrollRef}
                className="p-5 sm:p-8 font-mono text-[12px] sm:text-[13px] leading-relaxed h-[380px] sm:h-[440px] overflow-y-auto bg-[#09090b] CustomScrollbar"
            >
                {steps.slice(0, visibleLines).map((step, i) => (
                    <div
                        key={`${activeTab}-${i}`}
                        className="group flex gap-5 mb-2 transition-opacity duration-300"
                    >
                        <span className="w-6 text-right text-slate-500 select-none shrink-0 font-bold border-r border-slate-800 pr-3">
                            {(i + 1)}
                        </span>
                        <span className="sr-only">. </span>
                        <div className={`flex gap-2 ${step.color || "text-slate-300"}`}>
                            {step.type === "command" && (
                                <span className="text-[#4285F4] font-bold shrink-0">➜</span>
                            )}
                            <span className="whitespace-pre">{step.line}</span>
                        </div>
                    </div>
                ))}

                {visibleLines < steps.length && (
                    <div className="flex gap-5 mb-2">
                        <span className="w-6 text-right text-slate-500 select-none shrink-0 font-bold border-r border-slate-800 pr-3">
                            {(visibleLines + 1)}
                        </span>
                        <div className="flex items-center gap-2 text-slate-300">
                            {steps[visibleLines].type === "command" && (
                                <span className="text-[#4285F4] font-bold shrink-0">➜</span>
                            )}
                            <span className="whitespace-pre">{typingText}</span>
                            <span className="w-2 h-4 bg-[#4285F4] animate-pulse" />
                        </div>
                    </div>
                )}
            </div>

            {/* Forensic Status Bar */}
            <div className="h-12 bg-[#09090b] border-t border-white/5 px-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    {activeTab === "heal" && isDone ? (
                        <div className="flex items-center gap-3 text-[11px] font-bold">
                            <span className="text-amber-400">Manifest Health: 58</span>
                            <span className="text-slate-600">→</span>
                            <span className="text-emerald-400">100/100</span>
                            <span className="mx-1 text-slate-800">|</span>
                            <span className="text-sky-400">4 fixes applied (100% comments preserved)</span>
                        </div>
                    ) : activeTab === "diff" && isDone ? (
                        <div className="flex items-center gap-3 text-[11px] font-bold">
                            <span className="text-emerald-400">4 mutations predicted</span>
                            <span className="mx-1 text-slate-800">|</span>
                            <span className="text-sky-400">0 files modified (non-destructive AST)</span>
                        </div>
                    ) : activeTab === "scan" && isDone ? (
                        <div className="flex items-center gap-3 text-[11px] font-bold">
                            <span className="text-rose-400">4 issues detected</span>
                            <span className="mx-1 text-slate-800">|</span>
                            <span className="text-sky-400">12 files scanned (Rust fast-path)</span>
                        </div>
                    ) : (
                        <div className="text-[11px] text-slate-600 font-bold uppercase tracking-widest flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 animate-pulse"></span>
                            Engine Active
                        </div>
                    )}
                </div>
                <div className="text-[11px] text-slate-500 font-mono font-bold">
                    v0.1.0
                </div>
            </div>

            {/* Simulation Note */}
            <p className="mt-2 text-center text-[11px] text-slate-500 font-mono">
                Interactive CLI preview — deterministic output matching native Linux, macOS &amp; Windows binaries.
            </p>
        </div>
    );
}