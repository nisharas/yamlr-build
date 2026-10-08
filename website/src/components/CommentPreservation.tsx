"use client";

import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Code2 } from "lucide-react";

// Diff lines for before panel (broken YAML with comments)
const BEFORE_LINES = [
    { text: "# !! DO NOT CHANGE — required for payment gateway", type: "comment" },
    { text: "# Last verified: 2026-09-15 by @platform-team", type: "comment" },
    { text: "spec:", type: "code" },
    { text: "  containers:", type: "code" },
    { text: "  - name: api-server", type: "code" },
    { text: "    image: api-server:latest", type: "broken", label: "broken" },
    { text: "    # TODO: pin this before prod deploy", type: "comment" },
    { text: "    resources: {}", type: "broken", label: "missing limits" },
    { text: "    # CPU limit enforced by SRE — do not remove", type: "comment" },
    { text: "  restartPolicy: allways", type: "broken", label: "typo" },
];

// Diff lines for after panel (healed YAML, all comments intact)
const AFTER_LINES = [
    { text: "# !! DO NOT CHANGE — required for payment gateway", type: "comment", preserved: true },
    { text: "# Last verified: 2026-09-15 by @platform-team", type: "comment", preserved: true },
    { text: "spec:", type: "code" },
    { text: "  containers:", type: "code" },
    { text: "  - name: api-server", type: "code" },
    { text: "    image: api-server:1.4.2-alpine", type: "healed", label: "pinned" },
    { text: "    # TODO: pin this before prod deploy", type: "comment", preserved: true },
    { text: "    resources:", type: "healed" },
    { text: "      limits: {cpu: 500m, memory: 256Mi}", type: "healed", label: "added" },
    { text: "    # CPU limit enforced by SRE — do not remove", type: "comment", preserved: true },
    { text: "  restartPolicy: Always", type: "healed", label: "fixed" },
];

const lineColor = (type: string) => {
    if (type === "comment") return "text-slate-500 dark:text-slate-500 italic";
    if (type === "broken") return "text-rose-400";
    if (type === "healed") return "text-emerald-400";
    return "text-slate-300";
};

const PanelLine = ({ line, side }: { line: typeof BEFORE_LINES[0] & { preserved?: boolean }, side: "before" | "after" }) => (
    <div className="flex items-center gap-2 group min-h-[1.6rem]">
        <span className={`font-mono text-[12px] leading-relaxed whitespace-pre ${lineColor(line.type)}`}>
            {line.text}
        </span>
        {side === "before" && "label" in line && line.label && (
            <span className="text-[11px] font-bold text-rose-400/70 bg-rose-500/10 px-1.5 py-0.5 rounded shrink-0">
                {line.label}
            </span>
        )}
        {side === "after" && "preserved" in line && line.preserved && (
            <span className="text-[11px] font-bold text-emerald-400/70 shrink-0">
                ✓ preserved
            </span>
        )}
        {side === "after" && "label" in line && line.label && !("preserved" in line && line.preserved) && (
            <span className="text-[11px] font-bold text-emerald-400/70 bg-emerald-500/10 px-1.5 py-0.5 rounded shrink-0">
                {line.label}
            </span>
        )}
    </div>
);

export default function CommentPreservation() {
    return (
        <section className="py-14 bg-white dark:bg-[#0D1117] relative overflow-hidden">
            {/* Background glow */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[100px]" />
                <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[500px] h-[500px] bg-[#4285F4]/5 rounded-full blur-[100px]" />
            </div>

            <div className="max-w-7xl mx-auto px-6 sm:px-8 relative z-10">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                    className="text-center mb-6 sm:mb-8 space-y-2.5"
                >
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-100 dark:border-emerald-500/20">
                        <ShieldCheck size={11} />
                        Comment Preservation
                    </span>
                    <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white max-w-3xl mx-auto">
                        Your comments survive.{" "}
                        <span className="text-emerald-500">Always.</span>
                    </h2>
                    <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
                        Team annotations, compliance markers, operational warnings — <span className="font-bold font-outfit tracking-normal">yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span></span> preserves every comment 
                        and formatting detail automatically. No exceptions.
                    </p>
                </motion.div>

                {/* Diff panels */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                    className="grid md:grid-cols-2 gap-4 max-w-5xl mx-auto"
                >
                    {/* Before */}
                    <div className="rounded-2xl overflow-hidden border border-rose-500/20 bg-[#161B22] shadow-2xl shadow-slate-900/20 dark:shadow-black/50">
                        <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5 bg-slate-900/50">
                            <span className="text-xs font-mono font-medium text-rose-400/80 tracking-normal">
                                deploy.yaml — broken
                            </span>
                        </div>
                        <div className="p-4 sm:p-6 space-y-0.5 min-h-[280px] overflow-x-auto CustomScrollbar">
                            {BEFORE_LINES.map((line, i) => (
                                <PanelLine key={i} line={line} side="before" />
                            ))}
                        </div>
                        <div className="px-5 py-2.5 border-t border-white/5 bg-slate-900/30">
                            <span className="text-[11px] font-mono text-rose-400/60 font-bold uppercase tracking-widest">
                                Issues detected · comments at risk
                            </span>
                        </div>
                    </div>

                    {/* After */}
                    <div className="rounded-2xl overflow-hidden border border-emerald-500/20 bg-[#161B22] shadow-2xl shadow-slate-900/20 dark:shadow-black/50">
                        <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5 bg-slate-900/50">
                            <span className="text-xs font-mono font-medium text-emerald-400/80 tracking-normal">
                                deploy.yaml — healed ✓
                            </span>
                        </div>
                        <div className="p-4 sm:p-6 space-y-0.5 min-h-[280px] overflow-x-auto CustomScrollbar">
                            {AFTER_LINES.map((line, i) => (
                                <PanelLine key={i} line={line} side="after" />
                            ))}
                        </div>
                        <div className="px-5 py-2.5 border-t border-white/5 bg-slate-900/30">
                            <span className="text-[11px] font-mono text-emerald-400/60 font-bold uppercase tracking-widest">
                                Zero issues · comments preserved ✓
                            </span>
                        </div>
                    </div>
                </motion.div>



            </div>
        </section>
    );
}
