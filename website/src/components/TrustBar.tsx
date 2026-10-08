"use client";

import React from "react";
import { CheckCircle2, ShieldCheck, GitMerge, FileCheck } from "lucide-react";
import { RevealAnimation } from "./Hero";

const metrics = [
    {
        icon: <FileCheck className="text-[#326ce5]" size={24} />,
        value: "38",
        label: "CLI Commands & 42 Rules",
    },
    {
        icon: <ShieldCheck className="text-emerald-500" size={24} />,
        value: "Atomic Writes",
        label: "Zero Data Loss — fsync guaranteed",
    },
    {
        icon: <CheckCircle2 className="text-sky-500" size={24} />,
        value: "v1.21–v1.37+",
        label: "K8s Schema Coverage",
    },
    {
        icon: <GitMerge className="text-indigo-500" size={24} />,
        value: "Deterministic",
        label: "Same input = identical output",
    }
];

export const TrustBar = () => {
    return (
        <section className="py-8 bg-white dark:bg-[#0D1117] border-b border-slate-100 dark:border-slate-800 z-10 relative transition-colors duration-300">
            <div className="max-w-6xl mx-auto px-8">
                <RevealAnimation delay={500}>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 md:gap-4 outline-none">
                        {metrics.map((metric, idx) => (
                            <div key={idx} className="flex flex-col items-center justify-center text-center px-4 relative group">
                                {/* Optional subtle divider effect */}
                                {idx !== metrics.length - 1 && (
                                    <div className="hidden lg:block absolute right-0 top-1/2 -translate-y-1/2 h-12 w-px bg-slate-100 dark:bg-slate-800" />
                                )}
                                <div className="mb-4 p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/50 shadow-sm group-hover:bg-slate-100 dark:group-hover:bg-slate-700/50 group-hover:border-slate-200 dark:group-hover:border-slate-600 transition-colors">
                                    {metric.icon}
                                </div>
                                <div className="text-2xl font-outfit font-bold text-slate-900 dark:text-slate-50 tracking-tight mb-1">
                                    {metric.value}
                                </div>
                                <div className="text-[13px] font-bold tracking-wide uppercase text-slate-400 dark:text-slate-500">
                                    {metric.label}
                                </div>
                            </div>
                        ))}
                    </div>
                </RevealAnimation>
            </div>
        </section>
    );
};
