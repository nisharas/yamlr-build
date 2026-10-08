"use client";

import { useState } from "react";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { RevealAnimation } from "@/components/Hero";
import { Layers, Copy, Check, Terminal, Shield, ArrowRight, Zap, CheckCircle2, FileCode } from "lucide-react";
import Link from "next/link";

export default function HelmPage() {
    const [copied, setCopied] = useState<string | null>(null);

    const copyCode = (id: string, text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
    };

    const helmCmd = "yamlr scan --helm ./charts/api-service";
    const kustomizeCmd = "yamlr scan --kustomize ./overlays/production";

    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-[#4285F4]/10 selection:text-[#4285F4]">
            <Navigation />

            <main className="flex-1 pt-20 sm:pt-24 pb-20">
                <div className="max-w-5xl mx-auto px-6">
                    {/* Header */}
                    <div className="text-center mb-16">
                        <RevealAnimation>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 rounded-full mb-6">
                                <Layers size={13} className="text-[#4285F4]" />
                                <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-wider">
                                    Enterprise Helm & Kustomize Auditing
                                </span>
                            </div>
                        </RevealAnimation>

                        <RevealAnimation delay={100}>
                            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white mb-6">
                                In-Memory Helm & Kustomize{" "}
                                <span className="text-[#4285F4]">Auto-Healing</span>
                            </h1>
                        </RevealAnimation>

                        <RevealAnimation delay={200}>
                            <p className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
                                Over 70% of enterprise manifests are packaged as Helm charts or Kustomize overlays. 
                                Yamlr renders charts in-memory to audit composite resources and safely auto-heal source <code className="text-xs font-mono text-[#4285F4]">values.yaml</code> files.
                            </p>
                        </RevealAnimation>
                    </div>

                    {/* Feature Cards */}
                    <div className="grid md:grid-cols-2 gap-8 mb-16">
                        <div className="p-8 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-[#4285F4] mb-6">
                                <FileCode size={24} />
                            </div>
                            <h2 className="text-xl font-bold font-outfit text-slate-900 dark:text-white mb-3">Helm Chart Template Scanning</h2>
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
                                Executes in-memory template rendering without writing disk artifacts. Audits rendered manifests against official OpenAPI schemas and maps fixes directly to values.yaml.
                            </p>
                            <div className="p-4 rounded-xl bg-[#0D1117] border border-slate-800 flex items-center justify-between text-white font-mono text-xs">
                                <span className="text-slate-300">$ {helmCmd}</span>
                                <button onClick={() => copyCode("helm", helmCmd)} aria-label="Copy Helm scan command" className="text-slate-500 hover:text-white">
                                    {copied === "helm" ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                                </button>
                            </div>
                        </div>

                        <div className="p-8 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center text-purple-500 mb-6">
                                <Layers size={24} />
                            </div>
                            <h2 className="text-xl font-bold font-outfit text-slate-900 dark:text-white mb-3">Kustomize Overlay Verification</h2>
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
                                Validates composite overlays across base and environment patches to detect topology collisions, selector mismatches, and floating image tags.
                            </p>
                            <div className="p-4 rounded-xl bg-[#0D1117] border border-slate-800 flex items-center justify-between text-white font-mono text-xs">
                                <span className="text-slate-300">$ {kustomizeCmd}</span>
                                <button onClick={() => copyCode("kustomize", kustomizeCmd)} aria-label="Copy Kustomize scan command" className="text-slate-500 hover:text-white">
                                    {copied === "kustomize" ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* CTA */}
                    <div className="text-center p-8 sm:p-12 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 shadow-sm">
                        <h2 className="text-3xl sm:text-4xl font-extrabold font-outfit text-slate-950 dark:text-white mb-4">
                            Start Auditing in Sub-10ms
                        </h2>
                        <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-md mx-auto">
                            Install the zero-dependency native binary and run your first scan in seconds.
                        </p>
                        <Link
                            href="/#install"
                            className="inline-flex items-center gap-2 bg-[#4285F4] hover:bg-[#3367D6] text-white px-8 py-3.5 min-h-[48px] rounded-full font-bold transition-all shadow-md shadow-blue-500/20 active:scale-95 text-sm"
                        >
                            Get Standalone Binary
                            <ArrowRight size={16} />
                        </Link>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
