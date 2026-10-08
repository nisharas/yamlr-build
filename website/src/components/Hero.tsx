"use client";

import React from "react";
import { ShieldCheck, ArrowRight, Zap, FlaskConical, Check, Terminal } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

export const RevealAnimation = ({ children, delay = 0, className = "" }: { children: React.ReactNode; delay?: number; className?: string }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className={className}
            transition={{ duration: 0.6, delay: delay / 1000, ease: [0.16, 1, 0.3, 1] }}
        >
            {children}
        </motion.div>
    );
};

export const HeroSection = () => {
    return (
        <section className="relative pt-28 sm:pt-32 pb-8 sm:pb-10 overflow-hidden bg-white dark:bg-[#0D1117] dot-grid">
            <div className="max-w-7xl mx-auto px-6 sm:px-8 w-full relative z-10 text-center">

                {/* Badges */}
                <RevealAnimation>
                    <div className="inline-flex flex-wrap items-center justify-center gap-2.5 mb-6">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 rounded-full">
                            <Zap size={11} className="text-[#4285F4]" />
                            <span className="text-[11px] sm:text-xs font-semibold text-[#4285F4] tracking-wide">
                                Native Rust Core · Standalone CLI &amp; MCP Protocol
                            </span>
                        </div>
                        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-100 dark:border-emerald-500/20 rounded-full">
                            <ShieldCheck size={11} className="text-emerald-500" />
                            <span className="text-[11px] sm:text-xs font-semibold text-emerald-600 dark:text-emerald-400 tracking-wide">
                                100% Local &amp; Air-Gapped
                            </span>
                        </div>
                    </div>
                </RevealAnimation>

                {/* Hero Headline */}
                <RevealAnimation delay={100}>
                    <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold font-outfit tracking-tight leading-[1.14] mb-6 max-w-5xl mx-auto text-balance px-4">
                        <span className="text-slate-500 dark:text-slate-400 font-medium">Scanners find K8s </span>
                        <span className="text-[#E05252] dark:text-[#FB7185] font-medium tracking-tight">problems</span>
                        <br />
                        <span className="text-slate-950 dark:text-white font-extrabold">yamlr</span>
                        <span className="text-[#059669] dark:text-[#10B981] font-extrabold">.</span>{" "}
                        <span className="text-[#059669] dark:text-[#10B981] font-extrabold tracking-tight">fixes them</span>
                    </h1>
                </RevealAnimation>

                {/* Subheadline */}
                <RevealAnimation delay={200}>
                    <div className="max-w-3xl mx-auto mb-10 space-y-4">
                        <p className="text-base sm:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed font-medium text-balance px-4">
                            The deterministic, comment-preserving{" "}
                            <span className="text-slate-900 dark:text-slate-100 font-semibold">
                                auto-healing engine
                            </span>{" "}
                            for Kubernetes.
                        </p>
                    </div>
                </RevealAnimation>

                {/* CTAs */}
                <RevealAnimation delay={300}>
                    <div className="flex flex-col items-center">

                        {/* Buttons */}
                        <div className="flex flex-col sm:flex-row gap-3 items-center justify-center w-full mb-6">
                            <Link
                                href="#install"
                                aria-label="Install the yamlr. CLI"
                                className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-8 min-h-[48px] py-3 rounded-full bg-[#4285F4] hover:bg-[#3367D6] active:bg-[#2a56c6] text-white text-sm font-bold tracking-normal transition-all duration-150 shadow-md shadow-blue-500/20 active:scale-[0.98] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117]"
                            >
                                Install now — it's free
                                <ArrowRight size={16} />
                            </Link>

                            <Link
                                href="/sandbox"
                                aria-label="Try the sandbox — interactive preview"
                                className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-8 min-h-[48px] py-3 rounded-full border border-slate-300 dark:border-slate-700 bg-transparent hover:bg-slate-50 dark:hover:bg-slate-800/60 text-slate-700 dark:text-slate-300 text-sm font-bold tracking-normal transition-all duration-150 active:scale-[0.98] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117]"
                            >
                                <FlaskConical size={16} className="text-[#4285F4] dark:text-[#5B8BF0]" />
                                Try the sandbox
                            </Link>
                        </div>

                        {/* Trust anchors */}
                        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs font-medium text-slate-500 dark:text-slate-400 tracking-wide mb-0">
                            <span className="flex items-center gap-1.5">
                                <Terminal size={13} className="text-emerald-500" />
                                Workflow: scan · diff · heal
                            </span>
                            <div className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700 hidden sm:block" />
                            <span className="flex items-center gap-1.5">
                                <FlaskConical size={13} className="text-[#4285F4]" />
                                K8s v1.21 → v1.37 schemas
                            </span>
                            <div className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700 hidden sm:block" />
                            <span className="flex items-center gap-1.5">
                                <ShieldCheck size={13} className="text-sky-500" />
                                100% local · zero data egress
                            </span>
                            <div className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700 hidden sm:block" />
                            <span className="flex items-center gap-1.5">
                                <Check size={13} className="text-indigo-500" />
                                Every comment preserved
                            </span>
                        </div>

                    </div>
                </RevealAnimation>

            </div>
        </section>
    );
};