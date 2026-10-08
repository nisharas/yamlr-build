"use client";

import React, { useState } from "react";
import { Check, Copy, AlertTriangle, CheckCircle2, SplitSquareVertical } from "lucide-react";

interface InteractiveDiffCardProps {
    ruleId: string;
    beforeExample: string;
    afterExample: string;
}

export default function InteractiveDiffCard({
    ruleId,
    beforeExample,
    afterExample
}: InteractiveDiffCardProps) {
    const [activeTab, setActiveTab] = useState<"split" | "before" | "after">("split");
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(afterExample);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden backdrop-blur-xl">
            {/* Top Toolbar */}
            <div className="flex flex-wrap items-center justify-between px-4 py-3 border-b border-slate-800/80 bg-slate-950/60 gap-3">
                <div className="flex items-center gap-1.5 p-1 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium">
                    <button
                        onClick={() => setActiveTab("split")}
                        className={`px-3 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                            activeTab === "split"
                                ? "bg-cyan-500/20 text-cyan-300 font-semibold"
                                : "text-slate-400 hover:text-slate-200"
                        }`}
                    >
                        <SplitSquareVertical className="w-3.5 h-3.5" />
                        Side-by-Side
                    </button>
                    <button
                        onClick={() => setActiveTab("before")}
                        className={`px-3 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                            activeTab === "before"
                                ? "bg-rose-500/20 text-rose-300 font-semibold"
                                : "text-slate-400 hover:text-slate-200"
                        }`}
                    >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Broken
                    </button>
                    <button
                        onClick={() => setActiveTab("after")}
                        className={`px-3 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                            activeTab === "after"
                                ? "bg-emerald-500/20 text-emerald-300 font-semibold"
                                : "text-slate-400 hover:text-slate-200"
                        }`}
                    >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Healed
                    </button>
                </div>

                <button
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-medium transition-colors border border-slate-700"
                >
                    {copied ? (
                        <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400 font-semibold">Copied Healed YAML</span>
                        </>
                    ) : (
                        <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy Healed YAML</span>
                        </>
                    )}
                </button>
            </div>

            {/* Content Area */}
            <div className="p-4">
                {activeTab === "split" && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="rounded-lg border border-rose-500/20 bg-rose-950/10 p-4">
                            <div className="text-xs font-semibold text-rose-400 flex items-center gap-1.5 mb-2.5">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                Detected Violation (Broken)
                            </div>
                            <pre className="text-xs font-mono text-slate-300 overflow-x-auto p-3 rounded bg-slate-950/90 border border-slate-800/80 leading-relaxed">
                                <code>{beforeExample}</code>
                            </pre>
                        </div>
                        <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 p-4">
                            <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5 mb-2.5">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Healed with Yamlr
                            </div>
                            <pre className="text-xs font-mono text-slate-200 overflow-x-auto p-3 rounded bg-slate-950/90 border border-slate-800/80 leading-relaxed">
                                <code>{afterExample}</code>
                            </pre>
                        </div>
                    </div>
                )}

                {activeTab === "before" && (
                    <div className="rounded-lg border border-rose-500/20 bg-rose-950/10 p-4">
                        <div className="text-xs font-semibold text-rose-400 flex items-center gap-1.5 mb-2.5">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            Detected Violation
                        </div>
                        <pre className="text-xs font-mono text-slate-300 overflow-x-auto p-4 rounded bg-slate-950/90 border border-slate-800/80 leading-relaxed">
                            <code>{beforeExample}</code>
                        </pre>
                    </div>
                )}

                {activeTab === "after" && (
                    <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 p-4">
                        <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5 mb-2.5">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Healed Manifest (Comment Preserving)
                        </div>
                        <pre className="text-xs font-mono text-slate-200 overflow-x-auto p-4 rounded bg-slate-950/90 border border-slate-800/80 leading-relaxed">
                            <code>{afterExample}</code>
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
}
