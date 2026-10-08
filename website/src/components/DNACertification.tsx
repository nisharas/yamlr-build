"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, AlertCircle, AlertTriangle, Info, Zap, ChevronRight } from 'lucide-react';
import { RevealAnimation } from './Hero';

export default function DNACertification() {
    const [score, setScore] = useState(100);
    const [stage, setStage] = useState(0); // 0: Pure, 1: Issues found, 2: Healed

    useEffect(() => {
        const timer = setInterval(() => {
            setStage((prev) => (prev + 1) % 3);
        }, 4000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        if (stage === 0) setScore(100);
        if (stage === 1) setScore(48); // 100 - 40 (Error) - 10 (Warning) - 2 (Info)
        if (stage === 2) setScore(95); // 100 - 10 (Warning) - 5 (Info) + 10 (Bonus)
    }, [stage]);

    const deductions = [
        { label: "Critical Schema Error", value: -40, active: stage === 1, icon: <AlertCircle size={14} className="text-rose-500" /> },
        { label: "OOM Risk (No Limits)", value: -10, active: stage >= 1, icon: <AlertTriangle size={14} className="text-amber-500" /> },
        { label: "Unpinned Image Tag", value: -5, active: stage >= 1, icon: <Info size={14} className="text-slate-400" /> },
    ];

    return (
        <section className="py-20 bg-white dark:bg-[#0D1117] overflow-hidden border-b border-slate-200 dark:border-slate-800">
            <div className="max-w-7xl mx-auto px-8">
                <div className="grid lg:grid-cols-2 gap-16 items-center">

                    {/* Left: Content */}
                    <div className="space-y-8">
                        <RevealAnimation>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 text-[#4285F4] text-xs font-bold uppercase tracking-widest border border-blue-100 dark:border-blue-500/20">
                                <ShieldCheck size={14} />
                                Technical Authority
                            </div>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit tracking-tight text-slate-900 dark:text-white mt-4 mb-6 leading-[1.1]">
                                DNA Trust Score.<br />
                                <span className="text-[#4285F4]">Mathematical certification.</span>
                            </h2>
                            <p className="text-xl text-slate-500 dark:text-slate-400 leading-relaxed max-w-xl">
                                Forget subjective linting results. Yamlr transforms every manifest audit into a deterministic, high-gravity health score (0-100) — the deterministic benchmark for production readiness and architectural integrity.
                            </p>
                        </RevealAnimation>

                        <RevealAnimation delay={200}>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                <div className="p-5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                                        <Zap size={14} className="text-amber-500" />
                                        Deterministic
                                    </h4>
                                    <p className="text-xs text-slate-500 dark:text-slate-300 leading-relaxed">
                                        Identical inputs always yield the same score. A stable anchor for CI/CD gates.
                                    </p>
                                </div>
                                <div className="p-5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                                        <ShieldCheck size={14} className="text-emerald-500" />
                                        Audit-Ready
                                    </h4>
                                    <p className="text-xs text-slate-500 dark:text-slate-300 leading-relaxed">
                                        Generate signed "DNA Receipts" to prove manifest compliance across every commit.
                                    </p>
                                </div>
                            </div>
                        </RevealAnimation>
                    </div>

                    {/* Right: Score Visualization */}
                    <RevealAnimation delay={300}>
                        <div className="relative p-1 bg-slate-100 dark:bg-slate-800 rounded-[2.5rem] shadow-xl overflow-hidden group">
                            <div className="bg-white dark:bg-[#0B1120] rounded-[2.2rem] p-10 md:p-12 relative overflow-hidden">

                                {/* Background Glow */}
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-[#4285F4]/10 rounded-full blur-[80px] pointer-events-none" />

                                <div className="relative z-10 flex flex-col items-center">

                                    {/* Score Counter */}
                                    <div className="relative mb-12">
                                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest text-center mb-2">DNA Integrity</div>
                                        <div className="flex items-baseline justify-center font-outfit">
                                            <motion.span
                                                className={`text-8xl md:text-9xl font-black ${score > 90 ? 'text-emerald-500' : score > 50 ? 'text-amber-500' : 'text-rose-500'} transition-colors duration-500`}
                                                initial={false}
                                                animate={{ scale: [1, 1.05, 1] }}
                                                transition={{ duration: 0.3 }}
                                            >
                                                {score}
                                            </motion.span>
                                            <span className="text-2xl font-bold text-slate-300 dark:text-slate-700 ml-2">/100</span>
                                        </div>
                                    </div>

                                    {/* Breakdown List */}
                                    <div className="w-full space-y-3 max-w-sm">
                                        <div className="flex justify-between items-center text-[11px] font-bold text-slate-400 uppercase tracking-widest pb-2 border-b border-slate-100 dark:border-slate-800 mb-4">
                                            <span>Factor</span>
                                            <span>Impact</span>
                                        </div>

                                        {deductions.map((d, i) => (
                                            <div key={i} className={`flex justify-between items-center transition-opacity duration-300 ${d.active ? 'opacity-100' : 'opacity-20'}`}>
                                                <div className="flex items-center gap-3">
                                                    {d.icon}
                                                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{d.label}</span>
                                                </div>
                                                <span className="text-xs font-mono font-bold text-rose-500">{d.value}</span>
                                            </div>
                                        ))}

                                        <div className={`flex justify-between items-center pt-4 border-t border-slate-100 dark:border-slate-800 transition-opacity duration-300 ${stage === 2 ? 'opacity-100' : 'opacity-20'}`}>
                                            <div className="flex items-center gap-3">
                                                <div className="w-3.5 h-3.5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                                    <Zap size={10} className="text-emerald-500" />
                                                </div>
                                                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 italic">Surgical Repair Bonus</span>
                                            </div>
                                            <span className="text-xs font-mono font-bold text-emerald-500">+10.0</span>
                                        </div>
                                    </div>

                                    {/* Status Indicator */}
                                    <div className="mt-12 flex items-center gap-2 px-4 py-2 rounded-full bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                                        <div className={`w-2 h-2 rounded-full animate-pulse ${score > 90 ? 'bg-emerald-500' : score > 50 ? 'bg-amber-500' : 'bg-rose-500'}`} />
                                        <span className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                                            {stage === 0 ? "Analyzing Clean Manifest" : stage === 1 ? "Issues Detected (Risk Found)" : "Self-Heal Applied (Ready)"}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </RevealAnimation>
                </div>
            </div>
        </section>
    );
}
