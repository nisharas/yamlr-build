"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { History, FileCode2, ShieldAlert, CheckCircle2, RotateCcw, Copy } from 'lucide-react';
import { RevealAnimation } from './Hero';

export default function RestoreVisualizer() {
    const [phase, setPhase] = useState<0 | 1 | 2 | 3 | 4>(0);

    // Animation Loop
    useEffect(() => {
        const timings = {
            0: 2000, // Wait on original state
            1: 1500, // Backup created
            2: 2500, // Mutate file
            3: 2000, // Run command
            4: 2500, // Revert finished
        };

        const timer = setTimeout(() => {
            setPhase((prev) => (prev >= 4 ? 0 : (prev + 1) as any));
        }, timings[phase]);

        return () => clearTimeout(timer);
    }, [phase]);

    return (
        <section className="py-12 bg-slate-50 dark:bg-slate-900/50 border-b border-t border-slate-200 dark:border-slate-800 transition-colors duration-300 overflow-hidden">
            <div className="max-w-6xl mx-auto px-8">
                <div className="grid lg:grid-cols-2 gap-16 items-center">

                    {/* Left: Copy & Value Prop */}
                    <div className="space-y-8">
                        <RevealAnimation>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-xs font-bold uppercase tracking-widest mb-2 border border-emerald-200 dark:border-emerald-500/20">
                                <History size={14} />
                                Zero-Risk Surgery
                            </div>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit tracking-tight text-slate-900 dark:text-white mb-6 leading-[1.1]">
                                Absolute Safety.<br />
                                <span className="text-[#4285F4]">100% Reversible.</span>
                            </h2>
                            <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed mb-8">
                                Fear of breaking production stops developers from adopting auto-healing tools. Yamlr eliminates this by automatically generating a cryptographic snapshot into `<code className="text-sm bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-amber-600 dark:text-amber-500 font-mono">.yamlr/backups</code>` before any file is touched. Audits run 100% locally; only anonymized technical pulses are shared to improve the engine.
                            </p>
                        </RevealAnimation>

                        <RevealAnimation delay={200}>
                            <div className="space-y-6">
                                <div className="flex gap-4">
                                    <div className={`mt-1 h-8 w-8 rounded-full flex items-center justify-center shrink-0 transition-colors duration-500 ${phase >= 1 ? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                                        1
                                    </div>
                                    <div>
                                        <h4 className={`text-xl font-bold font-outfit mb-1 transition-colors duration-500 ${phase >= 1 ? 'text-slate-900 dark:text-slate-50' : 'text-slate-400 dark:text-slate-600'}`}>Automatic Snapshot</h4>
                                        <p className="text-slate-500 dark:text-slate-400 text-sm">Every time you run a heal command, Yamlr quietly backups your precise local state first.</p>
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className={`mt-1 h-8 w-8 rounded-full flex items-center justify-center shrink-0 transition-colors duration-500 ${phase >= 2 ? 'bg-sky-100 dark:bg-sky-500/20 text-sky-600 dark:text-sky-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                                        2
                                    </div>
                                    <div>
                                        <h4 className={`text-xl font-bold font-outfit mb-1 transition-colors duration-500 ${phase >= 2 ? 'text-slate-900 dark:text-slate-50' : 'text-slate-400 dark:text-slate-600'}`}>Semantic Healing</h4>
                                        <p className="text-slate-500 dark:text-slate-400 text-sm">Yamlr restructures your YAML to match OpenAPI specifications while preserving human comments.</p>
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className={`mt-1 h-8 w-8 rounded-full flex items-center justify-center shrink-0 transition-colors duration-500 ${phase >= 3 ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                                        3
                                    </div>
                                    <div>
                                        <h4 className={`text-xl font-bold font-outfit mb-1 transition-colors duration-500 ${phase >= 3 ? 'text-slate-900 dark:text-slate-50' : 'text-slate-400 dark:text-slate-600'}`}>Instant Rewind</h4>
                                        <p className="text-slate-500 dark:text-slate-400 text-sm">Don't like the mutations? A single command overwrites the changes with the exact prior state.</p>
                                    </div>
                                </div>
                            </div>
                        </RevealAnimation>
                    </div>

                    {/* Right: Visualization Canvas */}
                    <RevealAnimation delay={300}>
                        <div className="relative h-[480px] bg-slate-900 dark:bg-slate-950 rounded-[2.5rem] border border-slate-800 p-8 shadow-2xl flex flex-col justify-between">

                            {/* Terminal Top Bar */}
                            <div className="flex items-center gap-2 absolute top-6 left-6">
                                <div className="w-3 h-3 rounded-full bg-rose-500/80"></div>
                                <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
                                <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
                            </div>

                            {/* Active Command Overlay */}
                            <div className="absolute top-6 right-6 font-mono text-sm">
                                <AnimatePresence mode="wait">
                                    {phase === 0 && <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-slate-500">$ waiting...</motion.div>}
                                    {(phase === 1 || phase === 2) && <motion.div key="heal" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[#4285F4] font-bold">$ yamlr heal deployment.yaml</motion.div>}
                                    {(phase === 3 || phase === 4) && <motion.div key="restore" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-emerald-400 font-bold">$ yamlr restore</motion.div>}
                                </AnimatePresence>
                            </div>

                            {/* Center Graph / File Layout */}
                            <div className="flex-1 flex items-center justify-center relative mt-8">

                                {/* The Original/Mutated File */}
                                <motion.div
                                    className={`relative w-48 h-56 rounded-xl border flex flex-col items-center justify-center z-20 ${phase === 2 ? 'bg-[#4285F4]/10 border-[#4285F4]/50' : 'bg-slate-800 border-slate-700'} shadow-2xl transition-colors duration-700`}
                                    animate={phase === 4 ? { x: [-10, 10, -5, 5, 0], transition: { duration: 0.5 } } : {}}
                                >
                                    {phase < 2 || phase >= 4 ? (
                                        <ShieldAlert size={48} className="text-rose-400 mb-4 opacity-70" />
                                    ) : (
                                        <CheckCircle2 size={48} className="text-[#4285F4] mb-4" />
                                    )}
                                    <span className="font-mono text-xs text-slate-300">deployment.yaml</span>

                                    {/* Code lines visual */}
                                    <div className="w-32 mt-4 space-y-2 opacity-50">
                                        <div className="h-1.5 bg-slate-500 rounded w-full"></div>
                                        <div className="h-1.5 bg-slate-500 rounded w-5/6"></div>
                                        <div className={`h-1.5 rounded w-4/6 transition-colors duration-700 ${phase === 2 ? 'bg-[#4285F4]' : 'bg-rose-500'}`}></div>
                                        <div className="h-1.5 bg-slate-500 rounded w-full"></div>
                                    </div>
                                </motion.div>

                                {/* The Backup Copy */}
                                <AnimatePresence>
                                    {(phase >= 1 && phase < 4) && (
                                        <motion.div
                                            initial={{ opacity: 0, scale: 0.8, x: 0, y: 0 }}
                                            animate={{
                                                opacity: phase === 3 ? 0.8 : 0.5,
                                                scale: 0.9,
                                                x: 120,
                                                y: -40,
                                                borderColor: phase === 3 ? '#10b981' : '#475569'
                                            }}
                                            exit={{ opacity: 0, scale: 1, x: 0, y: 0, transition: { duration: 0.5, ease: "backIn" } }}
                                            className="absolute w-40 h-48 rounded-xl bg-slate-800/80 border border-slate-700 flex flex-col items-center justify-center z-10 backdrop-blur-sm"
                                        >
                                            <div className="absolute -top-3 right-3 bg-amber-500 text-slate-900 text-[11px] font-bold px-2 py-0.5 rounded shadow w-max">
                                                BACKUP
                                            </div>
                                            <FileCode2 size={32} className="text-slate-400 mb-2" />
                                            <span className="font-mono text-xs text-slate-400 text-center px-4">
                                                .yamlr/backups/<br />170942_deploy.yaml
                                            </span>
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* Restore Connection Stream */}
                                <AnimatePresence>
                                    {phase === 3 && (
                                        <motion.svg
                                            className="absolute inset-0 w-full h-full z-15 pointer-events-none"
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                        >
                                            <motion.path
                                                d="M 280 120 Q 220 100 180 140"
                                                fill="transparent"
                                                stroke="#10b981"
                                                strokeWidth="3"
                                                strokeDasharray="6 6"
                                                animate={{ strokeDashoffset: [24, 0] }}
                                                transition={{ repeat: Infinity, duration: 0.5, ease: "linear" }}
                                            />
                                        </motion.svg>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Command Explain Bar */}
                            <div className="h-12 border-t border-slate-800/50 mt-6 flex items-center justify-center">
                                <motion.div
                                    className="text-xs font-mono font-bold uppercase tracking-widest"
                                    animate={{ color: phase === 4 ? '#10b981' : '#64748b' }}
                                >
                                    {phase === 0 && "System Idle"}
                                    {phase === 1 && "Generating Checksum & Snapshot..."}
                                    {phase === 2 && "Applying Deterministic Mutations"}
                                    {phase === 3 && "Executing Restore Command..."}
                                    {phase === 4 && <span className="flex items-center gap-2 text-emerald-500"><RotateCcw size={14} /> Full State Reverted</span>}
                                </motion.div>
                            </div>
                        </div>
                    </RevealAnimation>

                </div>
            </div>
        </section>
    );
}
