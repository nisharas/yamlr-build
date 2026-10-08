"use client";

import React from "react";
import { RevealAnimation } from "./Hero";
import { Zap, Check, X, Shield, Cpu, Clock, Terminal } from "lucide-react";

const BENCHMARKS = [
    {
        metric: "Execution Latency (1,000 files)",
        yamlr: "< 0.85s (Sub-10ms Native Core)",
        linters: "2.40s – 5.00s",
        cloudpolicy: "8.00s – 15.00s",
        iacscanners: "14.00s – 35.00s",
        winner: true
    },
    {
        metric: "Lossless Auto-Healing",
        yamlr: "✓ Yes (42 AST Remediations)",
        linters: "✗ No (Detection only)",
        cloudpolicy: "✗ No (Rejection only)",
        iacscanners: "✗ No (Detection only)",
        winner: true
    },
    {
        metric: "Comment & Formatting Preservation",
        yamlr: "100% Guaranteed",
        linters: "N/A (Read-only)",
        cloudpolicy: "N/A (Read-only)",
        iacscanners: "N/A (Read-only)",
        winner: true
    },
    {
        metric: "Model Context Protocol (MCP) AI Support",
        yamlr: "✓ Native ('yamlr mcp')",
        linters: "✗ No",
        cloudpolicy: "✗ No",
        iacscanners: "✗ No",
        winner: true
    },
    {
        metric: "Memory Footprint",
        yamlr: "< 18 MB",
        linters: "~45 MB – 80 MB",
        cloudpolicy: "~100 MB – 250 MB",
        iacscanners: "> 400 MB",
        winner: true
    },
    {
        metric: "Data Privacy & Air-Gapped Guarantee",
        yamlr: "100% Local / Zero Egress",
        linters: "Local",
        cloudpolicy: "Cloud Policy API",
        iacscanners: "Local / Heavy Runtime",
        winner: true
    }
];

export default function BenchmarkMatrix() {
    return (
        <section className="py-16 sm:py-20 lg:py-24 bg-slate-50 dark:bg-[#0D1117] border-t border-slate-200 dark:border-slate-800">
            <div className="max-w-6xl mx-auto px-6 sm:px-8">

                <div className="text-center max-w-3xl mx-auto mb-14 space-y-4">
                    <RevealAnimation>
                        <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3.5 py-1.5 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20">
                            Empirical Performance
                        </span>
                    </RevealAnimation>

                    <RevealAnimation delay={100}>
                        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight leading-tight">
                            Scientific Speed.{" "}
                            <span className="text-[#4285F4]">Uncompromising Healing.</span>
                        </h2>
                    </RevealAnimation>

                    <RevealAnimation delay={200}>
                        <p className="text-slate-600 dark:text-slate-400 text-base md:text-lg leading-relaxed">
                            Traditional linters only report failures. Yamlr repairs them in-memory before CI pipelines break—powered by an ultra-low latency native Rust fast-path.
                        </p>
                    </RevealAnimation>
                </div>

                {/* Benchmark Table */}
                <RevealAnimation delay={250}>
                    <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161B22] shadow-sm CustomScrollbar">
                        <table className="w-full min-w-[620px] text-left border-collapse">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-[#0D1117]/70">
                                    <th className="p-4 sm:p-5 text-xs font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                        Capability / Benchmark
                                    </th>
                                    <th className="p-4 sm:p-5 text-xs font-mono font-bold uppercase tracking-wider text-[#4285F4] bg-blue-500/5 dark:bg-blue-500/10 border-x border-blue-500/20">
                                        <div className="flex items-center gap-1.5">
                                            <Zap size={13} className="text-[#4285F4]" />
                                            Yamlr Engine
                                        </div>
                                    </th>
                                    <th className="p-4 sm:p-5 text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                                        Static Linters
                                    </th>
                                    <th className="p-4 sm:p-5 text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                                        Policy Gateways
                                    </th>
                                    <th className="p-4 sm:p-5 text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                                        Multi-IaC Scanners
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs sm:text-sm font-medium">
                                {BENCHMARKS.map((b, i) => (
                                    <tr key={i} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="p-4 sm:p-5 text-slate-800 dark:text-slate-200 font-semibold">
                                            {b.metric}
                                        </td>
                                        <td className="p-4 sm:p-5 text-[#4285F4] font-bold font-mono bg-blue-500/5 dark:bg-blue-500/10 border-x border-blue-500/20">
                                            {b.yamlr}
                                        </td>
                                        <td className="p-4 sm:p-5 text-slate-500 dark:text-slate-400 font-mono">
                                            {b.linters}
                                        </td>
                                        <td className="p-4 sm:p-5 text-slate-500 dark:text-slate-400 font-mono">
                                            {b.cloudpolicy}
                                        </td>
                                        <td className="p-4 sm:p-5 text-slate-500 dark:text-slate-400 font-mono">
                                            {b.iacscanners}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </RevealAnimation>

                {/* Footnote */}
                <div className="text-center mt-6">
                    <p className="text-xs text-slate-400 dark:text-slate-500 font-mono">
                        * Empirical evaluation conducted on 1,000 multi-document production manifests in local non-cached execution. Methodology reproducible via `yamlr roi`. Yamlr complements existing CI validation by automating manifest remediation.
                    </p>
                </div>

            </div>
        </section>
    );
}
