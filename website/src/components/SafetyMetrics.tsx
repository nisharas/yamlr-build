"use client";

import { RevealAnimation } from "./Hero";
import { ShieldCheck, Cpu, GitBranch, RefreshCw, Layout as LayoutIcon, Database as DatabaseIcon, Activity as ActivityIcon, Layers } from "lucide-react";

export default function SafetyMetrics() {
    const specs = [
        {
            label: "Version-Aware Schema Targeting",
            desc: "Validation compiled against the official Kubernetes OpenAPI specification for your selected cluster version (1.31 default).",
            icon: <Cpu size={18} />
        },
        {
            label: "20,000+ Manifest Stress-Test",
            desc: "Verified performance across simulated high-scale environments and cross-resource dependency graphs.",
            icon: <GitBranch size={18} />
        },
        {
            label: "Production-Grade Governance",
            desc: "Engineered for platform teams managing 100+ production clusters where configuration drift compounds risk.",
            icon: <RefreshCw size={18} />
        }
    ];

    const nodes = [
        { label: "Manifest", icon: <LayoutIcon size={14} />, angle: 0 },
        { label: "Graph", icon: <ActivityIcon size={14} />, angle: 72 },
        { label: "Schema", icon: <DatabaseIcon size={14} />, angle: 144 },
        { label: "Policy", icon: <ShieldCheck size={14} />, angle: 216 },
        { label: "Diff", icon: <Layers size={14} />, angle: 288 },
    ];

    return (
        <section className="relative py-24 bg-white border-y border-slate-100 overflow-hidden">
            {/* Background Tech Grid */}
            <div className="absolute inset-0 opacity-[0.05] pointer-events-none"
                style={{ backgroundImage: 'radial-gradient(#326ce5 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

            <div className="relative z-10 max-w-7xl mx-auto px-8">
                <div className="grid lg:grid-cols-2 gap-20 items-center">

                    {/* Left Content */}
                    <div>
                        <RevealAnimation>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 mb-6 shadow-sm">
                                <ShieldCheck size={14} className="text-[#326ce5]" />
                                <span className="text-[11px] font-bold tracking-[0.1em] text-slate-700 uppercase font-mono">
                                    Technical Specification
                                </span>
                            </div>
                        </RevealAnimation>

                        <RevealAnimation delay={100}>
                            <h3 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
                                Strict Schema <span className="text-[#326ce5]">Enforcement.</span>
                            </h3>
                        </RevealAnimation>

                        <RevealAnimation delay={200}>
                            <p className="text-lg text-slate-500 mb-10 leading-relaxed max-w-xl">
                                Every correction is derived from the official Kubernetes OpenAPI specification — version-locked, field-accurate, and structurally validated before it touches your manifests.
                            </p>
                        </RevealAnimation>

                        <div className="grid gap-4">
                            {specs.map((spec, i) => (
                                <RevealAnimation key={i} delay={300 + i * 100}>
                                    <div className="group p-5 rounded-2xl border border-slate-200 bg-slate-50/40 hover:bg-white hover:border-[#326ce5]/30 hover:shadow-xl hover:shadow-blue-500/5 transition-all duration-300 flex items-start gap-4">
                                        <div className="p-2.5 rounded-xl bg-white border border-slate-300 text-slate-500 group-hover:text-[#326ce5] group-hover:border-[#326ce5]/50 transition-colors shadow-sm">
                                            {spec.icon}
                                        </div>
                                        <div>
                                            <p className="font-bold text-slate-900 text-sm mb-1">{spec.label}</p>
                                            <p className="text-xs text-slate-600 leading-relaxed font-medium">{spec.desc}</p>
                                        </div>
                                    </div>
                                </RevealAnimation>
                            ))}
                        </div>
                    </div>

                    {/* Right Visual (High-Visibility Orbit) */}
                    <RevealAnimation delay={400}>
                        <div className="relative h-[500px] w-full flex items-center justify-center overflow-hidden">
                            {/* Orbital Path */}
                            <div className="absolute w-[85%] h-[85%] border-2 border-slate-200 rounded-full" />
                            <div className="absolute w-[62%] h-[62%] border border-blue-200 border-dashed animate-[spin_120s_linear_infinite] rounded-full" />

                            {/* Center Node */}
                            <div className="relative z-10 w-24 h-24 rounded-[2rem] bg-slate-950 flex items-center justify-center shadow-2xl border border-[#326ce5]/50 group cursor-default transition-all duration-500 hover:scale-110">
                                <ShieldCheck className="text-[#326ce5]" size={40} />
                                <div className="absolute -inset-1 bg-[#326ce5]/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>

                            {/* Satellites */}
                            {nodes.map((node, i) => (
                                <div
                                    key={i}
                                    className="absolute group z-20"
                                    style={{
                                        top: `${50 + 42 * Math.sin(node.angle * Math.PI / 180)}%`,
                                        left: `${50 + 42 * Math.cos(node.angle * Math.PI / 180)}%`,
                                        transform: 'translate(-50%, -50%)'
                                    }}
                                >
                                    <div className="relative flex flex-col items-center">
                                        <div className="p-3 rounded-2xl bg-white border border-slate-200 shadow-sm transition-all duration-300 group-hover:scale-110 group-hover:border-[#326ce5] group-hover:shadow-lg">
                                            {node.icon}
                                        </div>
                                        <span className="absolute -bottom-6 text-[11px] font-bold text-slate-400 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all duration-300">
                                            {node.label}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </RevealAnimation>
                </div>
            </div>
        </section>
    );
}
