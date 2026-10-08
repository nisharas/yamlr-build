"use client";

import { useState } from "react";
import { 
    Cpu, 
    ShieldAlert, 
    ExternalLink, 
    TerminalSquare, 
    LayoutGrid, 
    Table as TableIcon,
    Copy, 
    Check,
    ArrowRight
} from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

export interface FindingItem {
    id: string;
    code: string;
    title: string;
    description: string;
    severity: "critical" | "warning" | "info";
    field_path: string;
}

interface DiagnosticDashboardProps {
    status: "IDLE" | "ANALYZING" | "VERIFIED";
    findings: FindingItem[];
    targetK8sVersion: string;
    severityFilter: "ALL" | "critical" | "warning" | "info";
    onSeverityFilterChange: (filter: "ALL" | "critical" | "warning" | "info") => void;
}

export default function DiagnosticDashboard({
    status,
    findings,
    targetK8sVersion,
    severityFilter,
    onSeverityFilterChange
}: DiagnosticDashboardProps) {
    const [viewMode, setViewMode] = useState<"CARDS" | "TABLE">("CARDS");
    const [copiedCli, setCopiedCli] = useState(false);

    const criticalCount = findings.filter((f) => f.severity === "critical").length;
    const warningCount = findings.filter((f) => f.severity === "warning").length;
    const infoCount = findings.filter((f) => f.severity === "info").length;

    const filteredFindings = severityFilter === "ALL"
        ? findings
        : findings.filter((f) => f.severity === severityFilter);

    const handleCopyCli = () => {
        navigator.clipboard.writeText("yamlr heal ./ --apply");
        setCopiedCli(true);
        setTimeout(() => setCopiedCli(false), 2000);
    };

    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-[#161B22] p-5 sm:p-6 shadow-xs">
            {/* Dashboard Header Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-5 mb-5 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-[#4285F4]">
                        <Cpu size={20} />
                    </div>
                    <div>
                        <h3 className="font-bold text-base text-slate-900 dark:text-white font-outfit flex items-center gap-2">
                            Engine Diagnostic Report
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            Continuous AST syntax verification, OpenAPI schema alignment, and relational link audits.
                        </p>
                    </div>
                </div>

                {/* Top Metrics & View Density Toggle */}
                <div className="flex flex-wrap items-center gap-2.5">
                    {/* View Density Switcher (for 20 to 100+ violations) */}
                    {status === "VERIFIED" && findings.length > 0 && (
                        <div className="flex items-center bg-white dark:bg-slate-950 rounded-xl p-1 border border-slate-200 dark:border-slate-800 text-xs">
                            <button
                                onClick={() => setViewMode("CARDS")}
                                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium transition-all ${
                                    viewMode === "CARDS"
                                        ? "bg-[#4285F4] text-white shadow-xs"
                                        : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                                }`}
                                title="Card Grid View"
                            >
                                <LayoutGrid size={12} />
                                Cards
                            </button>
                            <button
                                onClick={() => setViewMode("TABLE")}
                                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium transition-all ${
                                    viewMode === "TABLE"
                                        ? "bg-[#4285F4] text-white shadow-xs"
                                        : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                                }`}
                                title="Dense Table View (for 20+ issues)"
                            >
                                <TableIcon size={12} />
                                Table
                            </button>
                        </div>
                    )}

                    {/* Total Violations Badge */}
                    <div className="px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs">
                        <span className="text-slate-400 mr-1.5">Violations:</span>
                        <span className="font-extrabold text-slate-900 dark:text-white font-outfit">
                            {status === "VERIFIED" ? findings.length : "--"}
                        </span>
                    </div>

                    {/* Schema Target Badge */}
                    <div className="px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs">
                        <span className="text-slate-400 mr-1.5">OpenAPI:</span>
                        <span className="font-bold text-emerald-500 font-outfit">v{targetK8sVersion} Valid</span>
                    </div>
                </div>
            </div>

            {/* Filter Chips Bar (Supports fast filtering for 20 to 100+ Violations) */}
            {status === "VERIFIED" && findings.length > 0 && (
                <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1">
                        Filter:
                    </span>
                    <button
                        onClick={() => onSeverityFilterChange("ALL")}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                            severityFilter === "ALL"
                                ? "bg-[#4285F4] text-white"
                                : "bg-white dark:bg-slate-950 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800"
                        }`}
                    >
                        All ({findings.length})
                    </button>
                    {criticalCount > 0 && (
                        <button
                            onClick={() => onSeverityFilterChange("critical")}
                            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                                severityFilter === "critical"
                                    ? "bg-rose-500 text-white"
                                    : "bg-rose-500/10 text-rose-500 border border-rose-500/20 hover:bg-rose-500/20"
                            }`}
                        >
                            Critical ({criticalCount})
                        </button>
                    )}
                    {warningCount > 0 && (
                        <button
                            onClick={() => onSeverityFilterChange("warning")}
                            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                                severityFilter === "warning"
                                    ? "bg-amber-500 text-white"
                                    : "bg-amber-500/10 text-amber-500 border border-amber-500/20 hover:bg-amber-500/20"
                            }`}
                        >
                            Warning ({warningCount})
                        </button>
                    )}
                    {infoCount > 0 && (
                        <button
                            onClick={() => onSeverityFilterChange("info")}
                            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                                severityFilter === "info"
                                    ? "bg-blue-500 text-white"
                                    : "bg-blue-500/10 text-[#4285F4] border border-blue-500/20 hover:bg-blue-500/20"
                            }`}
                        >
                            Info ({infoCount})
                        </button>
                    )}
                </div>
            )}

            {/* Diagnostic Findings Display Container (Contained max-height with smooth scrolling) */}
            <div className="max-h-[460px] overflow-y-auto custom-scrollbar pr-1 mb-6">
                {status === "IDLE" ? (
                    <div className="p-8 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center space-y-2">
                        <ShieldAlert size={32} className="mx-auto text-slate-400 dark:text-slate-500" />
                        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 font-outfit">
                            Diagnostics Awaiting Execution
                        </h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
                            Click <span className="text-[#4285F4] font-semibold">Heal Manifest</span> to scan AST tokens, verify OpenAPI v{targetK8sVersion} schemas, and review automated fixes.
                        </p>
                    </div>
                ) : filteredFindings.length === 0 ? (
                    <div className="p-6 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold">
                        ✓ No violations found matching the selected filter criteria.
                    </div>
                ) : viewMode === "TABLE" ? (
                    /* Enterprise Dense Tabular View (Scales easily to 100+ findings) */
                    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
                        <table className="w-full text-left border-collapse text-xs">
                            <thead className="sticky top-0 bg-slate-100 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 z-10">
                                <tr>
                                    <th className="py-2.5 px-3 font-bold text-slate-600 dark:text-slate-300 font-outfit w-24">Severity</th>
                                    <th className="py-2.5 px-3 font-bold text-slate-600 dark:text-slate-300 font-outfit w-28">Rule</th>
                                    <th className="py-2.5 px-3 font-bold text-slate-600 dark:text-slate-300 font-outfit w-44">Target Path</th>
                                    <th className="py-2.5 px-3 font-bold text-slate-600 dark:text-slate-300 font-outfit">Remediation Details</th>
                                    <th className="py-2.5 px-3 font-bold text-slate-600 dark:text-slate-300 font-outfit text-right w-24">Docs</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                                {filteredFindings.map((f) => (
                                    <tr key={f.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/40 transition-colors">
                                        <td className="py-2 px-3">
                                            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full inline-block ${
                                                f.severity === "critical"
                                                    ? "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                                                    : f.severity === "warning"
                                                    ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                                                    : "bg-blue-500/10 text-[#4285F4] border border-blue-500/20"
                                            }`}>
                                                {f.severity}
                                            </span>
                                        </td>
                                        <td className="py-2 px-3 font-mono font-bold text-[#4285F4]">
                                            {f.code}
                                        </td>
                                        <td className="py-2 px-3 font-mono text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[170px]" title={f.field_path}>
                                            {f.field_path}
                                        </td>
                                        <td className="py-2 px-3 text-slate-700 dark:text-slate-300 leading-snug">
                                            <span className="font-semibold block">{f.title}</span>
                                            <span className="text-[11px] text-slate-500 dark:text-slate-400">{f.description}</span>
                                        </td>
                                        <td className="py-2 px-3 text-right">
                                            <Link
                                                href={`/errors/${f.code.toLowerCase()}`}
                                                className="inline-flex items-center gap-1 text-[11px] text-[#4285F4] hover:underline font-semibold"
                                            >
                                                View <ExternalLink size={10} />
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    /* Visual Card Grid View (Ideal for 1-6 findings) */
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
                        {filteredFindings.map((f) => (
                            <motion.div
                                key={f.id}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="p-4 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between"
                            >
                                <div>
                                    <div className="flex items-center justify-between gap-2 mb-2">
                                        <span className="text-xs font-bold text-[#4285F4] font-mono">
                                            {f.code}
                                        </span>
                                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                                            f.severity === "critical"
                                                ? "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                                                : f.severity === "warning"
                                                ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                                                : "bg-blue-500/10 text-[#4285F4] border border-blue-500/20"
                                        }`}>
                                            {f.severity}
                                        </span>
                                    </div>
                                    <h4 className="text-xs font-bold text-slate-900 dark:text-white mb-1">
                                        {f.title}
                                    </h4>
                                    <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300 font-normal">
                                        {f.description}
                                    </p>
                                </div>
                                <Link
                                    href={`/errors/${f.code.toLowerCase()}`}
                                    className="inline-flex items-center gap-1 text-[11px] text-[#4285F4] hover:underline mt-3 font-semibold"
                                >
                                    Rule Catalog &amp; Remediation <ExternalLink size={10} />
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>

            {/* Harmonized 2-Step Local Execution Path (Eliminates Conflicting Statements) */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3.5">
                <div>
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5 font-outfit">
                        <TerminalSquare size={13} className="text-[#4285F4]" /> Replicate in Your Local Terminal:
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Step 1: Install yamlr CLI &bull; Step 2: Run in your repository to auto-heal all manifests:
                    </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
                    <Link
                        href="/#install"
                        className="px-3 py-2 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-semibold transition-colors flex items-center gap-1.5 whitespace-nowrap"
                        title="View CLI installation instructions"
                    >
                        <span>1. Install CLI</span>
                        <ArrowRight size={12} />
                    </Link>

                    <div className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-mono text-xs flex-shrink-0">
                        <span className="text-slate-500 mr-2 select-none">2.</span>
                        <code className="text-emerald-400 mr-3">yamlr heal ./ --apply</code>
                        <button
                            onClick={handleCopyCli}
                            className="text-slate-400 hover:text-white transition-colors"
                            title="Copy command"
                        >
                            {copiedCli ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
