"use client";

import React, { useRef, useState } from 'react';
import { motion, useScroll, useSpring } from 'framer-motion';
import { Share2, Activity as ActivityIcon, ShieldCheck, Zap as ZapIcon, ArrowRight } from "lucide-react";
import { RevealAnimation } from "./Hero";

const STAGES = [
    {
        id: "01",
        title: "Ingest",
        subtitle: "Parse & Discover",
        description: "Parse your manifests and reconstruct resource identities — even from malformed YAML.",
        icon: <Share2 size={24} />,
        color: "text-blue-500",
        bg: "bg-blue-50 dark:bg-blue-500/10"
    },
    {
        id: "02",
        title: "Contextualize",
        subtitle: "Map Relationships",
        description: "Map cross-resource relationships — Services to Deployments, ConfigMaps to Pods — to surface orphaned references and broken links.",
        icon: <ActivityIcon size={24} />,
        color: "text-indigo-500",
        bg: "bg-indigo-50 dark:bg-indigo-500/10"
    },
    {
        id: "03",
        title: "Verify",
        subtitle: "Check Against K8s Schema",
        description: "Validate structural integrity against the official Kubernetes OpenAPI schema for your target cluster version.",
        icon: <ShieldCheck size={24} />,
        color: "text-[#4285F4]", // Yamlr Blue
        bg: "bg-[#4285F4]/5 dark:bg-[#4285F4]/10"
    },
    {
        id: "04",
        title: "Heal",
        subtitle: "Schema-Based Auto-Fix",
        description: "Apply precise, comment-preserving corrections backed by the Kubernetes OpenAPI specification.",
        icon: <ZapIcon size={24} />,
        color: "text-amber-500",
        bg: "bg-amber-50 dark:bg-amber-500/10"
    }
];

export default function Workflow() {
    const containerRef = useRef<HTMLDivElement>(null);
    const { scrollYProgress } = useScroll({
        target: containerRef,
        offset: ["start center", "end center"]
    });

    const scaleX = useSpring(scrollYProgress, {
        stiffness: 100,
        damping: 30,
        restDelta: 0.001
    });

    return (
        <section 
            ref={containerRef} 
            className="py-14 bg-white dark:bg-[#0D1117] relative overflow-hidden"
            role="region"
            aria-label="yamlr. Analysis and Repair Workflow"
        >
            <div className="max-w-7xl mx-auto px-6 sm:px-8">
                <div className="text-center mb-8 sm:mb-10">
                    <RevealAnimation>
                        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 mb-3">
                            <ActivityIcon size={12} />
                            Execution Lifecycle
                        </span>
                    </RevealAnimation>
                    <RevealAnimation delay={100}>
                        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white">
                            Build. Dry-run. <span className="text-[#4285F4]">Heal.</span>
                        </h2>
                    </RevealAnimation>
                </div>

                <div className="relative pt-8">
                    {/* Horizontal Connector Line (Mobile: Hidden, Desktop: Visible) */}
                    <div className="hidden lg:block absolute top-[20px] left-[32px] right-[calc(25%-32px)] h-0.5 bg-slate-200 dark:bg-slate-800 z-0 overflow-hidden">
                        <motion.div
                            style={{ scaleX }}
                            className="absolute inset-0 bg-[#4285F4]/50 origin-left"
                        />
                        <div className="absolute top-0 h-full w-32 bg-gradient-to-r from-transparent via-[#4285F4] to-transparent animate-[shimmer-line_3s_ease-in-out_infinite]" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 relative z-10">
                        {STAGES.map((stage, i) => (
                            <div key={stage.id} className="relative group">
                                {/* Desktop Indicator Node aligned with connector track and icon */}
                                <div className="hidden lg:flex absolute -top-[20px] left-8 -translate-x-1/2 -translate-y-1/2 w-6 h-6 items-center justify-center z-10">
                                    <div className="w-3.5 h-3.5 rounded-full bg-white dark:bg-[#161B22] border-2 border-slate-300 dark:border-slate-700 group-hover:border-[#4285F4] dark:group-hover:border-[#4285F4] group-hover:scale-125 transition-all duration-300 z-10 shadow-xs" />
                                    <div className="absolute inset-0 bg-[#4285F4]/20 rounded-full scale-0 group-hover:scale-125 transition-transform duration-300" />
                                </div>

                                <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
                                    <div className={`w-16 h-16 rounded-2xl ${stage.bg} ${stage.color} flex items-center justify-center mb-8 group-hover:scale-110 transition-transform duration-500 shadow-sm border border-slate-100/50 dark:border-slate-700/50`}>
                                        {stage.icon}
                                    </div>

                                    <div className="flex items-center gap-3 mb-2">
                                        <span className="text-[11px] font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest leading-none">
                                            Step<span className="sr-only"> </span> {stage.id}
                                        </span>
                                        <div className="h-px w-4 bg-slate-200 dark:bg-slate-700" />
                                    </div>

                                    <h3 className="text-xl font-bold font-outfit text-slate-900 dark:text-slate-50 mb-1">
                                        {stage.title}
                                    </h3>
                                    <p className="text-sm font-bold text-[#4285F4]/80 uppercase tracking-wider mb-4">
                                        {stage.subtitle}
                                    </p>
                                    <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                                        {stage.description}
                                    </p>
                                </div>

                                {i < STAGES.length - 1 && (
                                    <div className="md:hidden flex justify-center py-8">
                                        <ArrowRight className="text-slate-200 dark:text-slate-800" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="mt-8 sm:mt-10 p-8 md:p-10 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 overflow-hidden relative">
                    {/* Decorative Background Glow */}
                    <div className="absolute top-0 right-0 w-64 h-64 bg-[#4285F4]/5 blur-[80px] rounded-full translate-x-1/2 -translate-y-1/2" />

                    <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-8 lg:gap-12">
                        <div className="max-w-lg">
                            <h3 className="text-2xl font-bold font-outfit text-slate-900 dark:text-slate-50 mb-4">
                                Every Fix is Schema-Backed
                            </h3>

                            <div className="space-y-4">
                                {/* Impactful Hook Line */}
                                <p className="text-lg font-medium text-slate-900 dark:text-slate-100">
                                    Other tools guess. <span className="font-bold font-outfit tracking-normal">yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span></span> knows.
                                </p>

                                {/* Core Body Text */}
                                <p className="text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                                    Every correction is derived from the official Kubernetes OpenAPI specification — not heuristics, not AI hallucinations.
                                </p>

                                {/* S-Level Safety Legend */}
                                <div className="flex flex-wrap gap-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                                    <div className="flex items-center gap-2">
                                        <span className="h-6 px-2.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-[11px] font-bold font-mono text-slate-400 dark:text-slate-300 uppercase tracking-widest whitespace-nowrap">S0</span>
                                        <span className="sr-only">: Detect</span>
                                        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight" aria-hidden="true">Detect</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="h-6 px-2.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-[11px] font-bold font-mono text-[#4285F4] uppercase tracking-widest whitespace-nowrap">S1</span>
                                        <span className="sr-only">: Preview</span>
                                        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight" aria-hidden="true">Preview</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="h-6 px-2.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-[11px] font-bold font-mono text-emerald-500 uppercase tracking-widest whitespace-nowrap">S2</span>
                                        <span className="sr-only">: Apply</span>
                                        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight" aria-hidden="true">Apply</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right Side Verified Badge */}
                        <div className="flex flex-col items-center lg:items-end gap-2 shrink-0">
                            <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-xs">
                                <ShieldCheck size={18} className="text-emerald-500 shrink-0" />
                                <span className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200">
                                    k8s.io/api · v1.21 → v1.37
                                </span>
                            </div>
                            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                                OpenAPI v3 Schema Certified
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
