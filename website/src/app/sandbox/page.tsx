"use client";

import { Activity, ArrowRight, ShieldCheck } from "lucide-react";
import Playground from "@/components/Playground";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import Link from "next/link";

export default function PreviewPage() {
    return (
        <div className="min-h-screen bg-[#F8F9FA] dark:bg-[#0D1117] flex flex-col font-sans">
            <Navigation />

            <main className="flex-1">
                {/* Google-Style Header Block */}
                <div className="bg-white dark:bg-[#0D1117] pt-20 pb-10 md:pt-24 md:pb-12 text-center relative overflow-hidden border-b border-slate-200 dark:border-slate-800">
                    {/* Subtle Grid Pattern */}
                    <div className="absolute inset-0 opacity-[0.04] bg-[radial-gradient(#4285F4_1.5px,transparent_1.5px)] bg-[size:32px_32px]" />
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent to-slate-50/50 dark:to-[#0D1117]" />
                    
                    <div className="relative z-10 max-w-5xl mx-auto px-6">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#4285F4]/10 border border-[#4285F4]/20 text-[#4285F4] text-xs font-bold uppercase tracking-wider mb-5">
                            <Activity size={14} />
                            State Restoration Environment
                        </div>
                        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold font-outfit text-slate-950 dark:text-white mb-5 tracking-tight leading-tight">
                            The Interactive <span className="text-[#4285F4]">Sandbox</span>
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto text-base md:text-lg leading-relaxed font-normal">
                            Test deterministic, comment-preserving infrastructure auto-healing in your browser. Explore production Kubernetes failure modes or paste your manifests to inspect live repairs before running <span className="font-extrabold tracking-tight font-outfit text-slate-950 dark:text-white inline-block">yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span></span> locally.
                        </p>
                    </div>
                </div>

                <Playground />

                {/* Bottom Call to Action */}
                <section className="py-16 md:py-20 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0D1117]">
                    <div className="max-w-4xl mx-auto px-6 text-center">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold mb-4">
                            <ShieldCheck size={14} />
                            Zero Network Latency • 100% Local CLI Execution
                        </div>
                        <h2 className="text-2xl sm:text-4xl font-extrabold font-outfit text-slate-900 dark:text-white mb-4 tracking-tight">
                            Ready to heal manifests in your local terminal?
                        </h2>
                        <p className="text-slate-600 dark:text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mb-8">
                            Integrate <span className="font-extrabold tracking-tight font-outfit text-slate-950 dark:text-white inline-block">yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span></span> into your Git pre-commit hooks, CI/CD pipelines, or local IDE to auto-heal manifests in under 15ms.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link
                                href="/#install"
                                className="bg-[#4285F4] hover:bg-[#3367D6] text-white px-8 py-3.5 rounded-full font-bold transition-all active:scale-95 shadow-md shadow-blue-500/20 text-sm inline-flex items-center justify-center gap-2"
                            >
                                Install CLI &amp; Get Started <ArrowRight size={15} />
                            </Link>
                            <Link
                                href="/docs"
                                className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 px-8 py-3.5 rounded-full font-bold transition-all active:scale-95 text-sm inline-flex items-center justify-center"
                            >
                                Explore Documentation
                            </Link>
                        </div>
                    </div>
                </section>
            </main>

            <Footer />
        </div>
    );
}
