"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, ShieldCheck, Globe, Activity, Lock, Shield, LayoutGrid, Terminal, Zap } from "lucide-react";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { RevealAnimation } from "@/components/Hero";
import { motion } from "framer-motion";

export default function EnterprisePortal() {
    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] flex flex-col selection:bg-[#4285F4] selection:text-white">
            <Navigation />

            <main className="flex-1 flex flex-col items-center justify-center pt-24 sm:pt-28 pb-20 px-6 sm:px-8">
                <div className="max-w-4xl w-full text-center space-y-12">
                    <RevealAnimation>
                        <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-full border border-[#4285F4]/20 bg-[#4285F4]/5 text-[#4285F4] text-xs font-bold font-outfit uppercase tracking-widest">
                            <Lock size={12} />
                            Team &amp; Pro Governance
                        </div>
                    </RevealAnimation>

                    <RevealAnimation delay={100}>
                        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white leading-[1.12]">
                            yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span> <span className="text-[#4285F4]">Team &amp; Pro</span>
                        </h1>
                    </RevealAnimation>

                    <RevealAnimation delay={200}>
                        <p className="text-slate-600 dark:text-slate-400 text-lg sm:text-xl font-medium max-w-2xl mx-auto leading-relaxed">
                            CI/CD automated healing, SARIF reporting, and multi-repo GitOps governance for Kubernetes fleets.
                        </p>
                    </RevealAnimation>

                    <div className="grid md:grid-cols-3 gap-6 py-8">
                        {[
                            { 
                                title: "Fleet PR Batching", 
                                desc: "Automated multi-repo healing and branch creation across Git fleets.", 
                                icon: <LayoutGrid className="text-violet-500" size={24} /> 
                            },
                            { 
                                title: "Atomic Audits", 
                                desc: "Signed proof of configuration integrity for compliance.", 
                                icon: <Terminal className="text-emerald-500" size={24} /> 
                            },
                            { 
                                title: "Compliance Vault", 
                                desc: "HMAC-signed proof of configuration integrity and pre/post DNA receipts.", 
                                icon: <ShieldCheck className="text-sky-500" size={24} /> 
                            }
                        ].map((benefit, i) => (
                            <div key={i} className="p-8 border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#161B22] text-left space-y-4 rounded-2xl shadow-sm">
                                {benefit.icon}
                                <h2 className="text-sm font-bold font-outfit text-slate-900 dark:text-white uppercase tracking-widest">{benefit.title}</h2>
                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-medium">{benefit.desc}</p>
                            </div>
                        ))}
                    </div>

                    <RevealAnimation delay={300}>
                        <div className="flex flex-col items-center gap-8">
                            <div className="flex flex-col sm:flex-row gap-4 items-center justify-center">
                                <Link 
                                    href="/checkout?tier=team"
                                    className="inline-flex items-center justify-center gap-2 px-8 min-h-[48px] py-3.5 rounded-full bg-[#4285F4] hover:bg-[#3367D6] text-white text-sm font-bold tracking-normal transition-all shadow-md shadow-blue-500/20 active:scale-95 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117]"
                                >
                                    Get Started with Team
                                    <Zap size={16} />
                                </Link>
                                <a 
                                    href="mailto:contact@yamlr.dev"
                                    className="inline-flex items-center justify-center gap-2 px-8 min-h-[48px] py-3.5 rounded-full border border-slate-300 dark:border-slate-700 bg-transparent hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-bold tracking-normal transition-all active:scale-95 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117]"
                                >
                                    Contact Enterprise Sales
                                    <ArrowRight size={16} />
                                </a>
                            </div>
                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                Private Deployments • Custom Policy • Design Partnerships
                            </p>
                        </div>
                    </RevealAnimation>
                </div>
            </main>

            <Footer />
        </div>
    );
}
