"use client";

import { RevealAnimation } from "./Hero";
import { Check, ArrowRight, Download, ShieldCheck } from "lucide-react";
import Link from "next/link";

const FREE_FEATURES = [
    "Unlimited scanning & forensic detection",
    "Unlimited surgical healing (Free Forever)",
    "Instant dry-run diffs & atomic apply",
    "Native Rust execution engine (local-first)",
    "Model Context Protocol (MCP Server)",
    "Single-file & local repo topology graph",
    "Air-gapped compatible (zero telemetry)",
];

const TEAM_FEATURES = [
    "Everything in Individual",
    "CI/CD SARIF reports with yamlr-action",
    "Fleet-wide multi-repo governance",
    "OPA Gatekeeper & Kyverno policy auto-repair",
    "Priority schema updates (48h SLA)",
    "Priority email support",
];

const ENTERPRISE_FEATURES = [
    "Everything in Team",
    "Cryptographic compliance receipts (SOC2 / HIPAA)",
    "Air-gapped binary distribution",
    "Cryptographic manifest signing",
    "Custom CRD policy vault",
    "Dedicated SLA & onboarding",
];

export default function Pricing() {
    return (
        <section id="pricing" className="py-14 bg-white dark:bg-[#0D1117]">
            <div className="max-w-7xl mx-auto px-6 sm:px-8">

                {/* Section Header */}
                <div className="text-center mb-6 sm:mb-8">
                    <RevealAnimation>
                        <div className="space-y-2.5">
                            <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 mb-3 inline-block">
                                Pricing &amp; Plans
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white max-w-3xl mx-auto">
                                Free for individuals.{" "}
                                <span className="text-[#4285F4]">Built for teams.</span>
                            </h2>
                            <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed font-medium">
                                Unlimited scanning and surgical healing for individual engineers — free forever. Upgrade for CI/CD integration, fleet governance, and dedicated support.
                            </p>
                        </div>
                    </RevealAnimation>
                </div>

                {/* Pricing Cards */}
                <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">

                    {/* Free Tier */}
                    <RevealAnimation delay={100}>
                        <div className="h-full p-8 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 flex flex-col">
                            <div className="mb-8">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="space-y-1">
                                        <h3 className="text-lg font-extrabold font-outfit text-slate-900 dark:text-white tracking-tight">
                                            Individual
                                        </h3>
                                        <div className="flex items-end gap-1">
                                            <span className="text-3xl font-extrabold font-outfit text-slate-950 dark:text-white">
                                                $0
                                            </span>
                                            <span className="text-xs text-slate-400 mb-1.5">
                                                / forever
                                            </span>
                                        </div>
                                    </div>
                                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                        Free
                                    </span>
                                </div>
                                <p className="text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed min-h-[40px]">
                                    Full detection and healing engine for individual engineers.
                                </p>
                            </div>

                            <ul className="space-y-3 mb-8 flex-1">
                                {FREE_FEATURES.map((item, i) => (
                                    <li key={i} className="flex items-start gap-3 text-[13px] text-slate-700 dark:text-slate-300 leading-tight">
                                        <Check size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                                        {item}
                                    </li>
                                ))}
                            </ul>

                            <Link
                                href="/#install"
                                className="inline-flex items-center justify-center gap-2 w-full px-6 py-2.5 rounded-full border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 text-[13px] font-bold tracking-normal transition-all duration-150 active:scale-[0.98] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#161B22]"
                            >
                                <Download size={14} />
                                Install CLI
                            </Link>
                        </div>
                    </RevealAnimation>

                    {/* Team Tier */}
                    <RevealAnimation delay={200}>
                        <div className="h-full p-8 rounded-2xl bg-white dark:bg-slate-900 border-2 border-[#4285F4] flex flex-col relative overflow-hidden shadow-xl shadow-blue-500/10">
                            <div className="absolute top-0 inset-x-0 h-1 bg-[#4285F4]"></div>
                            <div className="mb-8">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="space-y-1">
                                        <h3 className="text-lg font-extrabold font-outfit text-slate-900 dark:text-white tracking-tight">
                                            Team
                                        </h3>
                                        <div className="flex items-end gap-1">
                                            <span className="text-3xl font-extrabold font-outfit text-slate-950 dark:text-white">
                                                $29
                                            </span>
                                            <span className="text-xs text-slate-400 mb-1.5">
                                                / dev / mo
                                            </span>
                                        </div>
                                    </div>
                                    <span className="text-[10px] font-bold text-[#4285F4] uppercase tracking-widest px-2.5 py-1 rounded-full bg-[#4285F4]/10 border border-[#4285F4]/20">
                                        Recommended
                                    </span>
                                </div>
                                <p className="text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed min-h-[40px]">
                                    For teams that ship to Kubernetes daily. Billed annually at $25/dev/mo.
                                </p>
                            </div>

                            <ul className="space-y-3 mb-8 flex-1">
                                {TEAM_FEATURES.map((item, i) => (
                                    <li key={i} className="flex items-start gap-3 text-[13px] text-slate-700 dark:text-slate-300 leading-tight">
                                        <Check size={14} className="text-[#4285F4] mt-0.5 shrink-0" />
                                        {i === 0 ? <span className="font-semibold">{item}</span> : item}
                                    </li>
                                ))}
                            </ul>

                            <Link
                                href="/checkout?tier=team"
                                className="inline-flex items-center justify-center gap-2 w-full px-6 py-2.5 rounded-full bg-[#4285F4] hover:bg-[#3367D6] active:bg-[#2a56c6] text-white text-[13px] font-bold tracking-normal transition-all duration-150 active:scale-[0.98] shadow-md shadow-blue-500/20 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900"
                            >
                                Buy Now
                            </Link>
                        </div>
                    </RevealAnimation>

                    {/* Enterprise Tier */}
                    <RevealAnimation delay={300}>
                        <div className="h-full p-8 rounded-2xl bg-emerald-50/40 dark:bg-[#0E1A16] border border-emerald-200/80 dark:border-emerald-800/50 flex flex-col relative overflow-hidden shadow-sm">
                            <div className="absolute top-0 inset-x-0 h-1 bg-[#059669]"></div>
                            <div className="mb-8">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="space-y-1">
                                        <h3 className="text-lg font-extrabold font-outfit text-slate-900 dark:text-white tracking-tight">
                                            Enterprise
                                        </h3>
                                        <div className="flex items-end gap-1">
                                            <span className="text-xl mt-1 font-extrabold font-outfit text-slate-950 dark:text-white">
                                                Contact Sales
                                            </span>
                                        </div>
                                    </div>
                                    <span className="text-[10px] font-bold text-[#059669] dark:text-emerald-400 uppercase tracking-widest px-2.5 py-1 rounded-full bg-emerald-100/80 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800">
                                        Scale
                                    </span>
                                </div>
                                <p className="text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed min-h-[40px]">
                                    For organizations with 50+ engineers requiring advanced security and scale.
                                </p>
                            </div>

                            <ul className="space-y-3 mb-8 flex-1">
                                {ENTERPRISE_FEATURES.map((item, i) => (
                                    <li key={i} className="flex items-start gap-3 text-[13px] text-slate-700 dark:text-slate-300 leading-tight">
                                        <Check size={14} className="text-[#059669] dark:text-emerald-400 mt-0.5 shrink-0" />
                                        {i === 0 ? <span className="font-semibold text-slate-900 dark:text-white">{item}</span> : item}
                                    </li>
                                ))}
                            </ul>

                            <a
                                href="mailto:contact@yamlr.dev"
                                className="inline-flex items-center justify-center gap-2 w-full px-6 py-2.5 rounded-full border-2 border-[#059669] hover:bg-[#059669] hover:text-white text-[#059669] dark:text-emerald-400 dark:border-emerald-500 dark:hover:bg-[#059669] dark:hover:text-white text-[13px] font-bold tracking-normal transition-all duration-150 active:scale-[0.98] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#059669] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900"
                            >
                                Contact Sales
                            </a>
                        </div>
                    </RevealAnimation>

                </div>

                {/* Bottom trust line */}
                <RevealAnimation delay={400}>
                    <p className="text-center text-xs text-slate-500 dark:text-slate-400 mt-6 tracking-wide">
                        No credit card required · Runs 100% locally · Air-gapped compatible
                    </p>
                </RevealAnimation>

            </div>
        </section>
    );
}