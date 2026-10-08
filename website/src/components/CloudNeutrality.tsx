"use client";

import React from "react";
import { RevealAnimation } from "./Hero";
import { Server, ShieldCheck, Cpu, Globe, CheckCircle2, Lock, ArrowRight, Layers } from "lucide-react";
import Link from "next/link";

const CLOUD_PLATFORMS = [
    {
        name: "Amazon EKS",
        category: "AWS Cloud",
        desc: "Validates IRSA ServiceAccount annotations, ALB Ingress target groups, and Secrets Store CSI references without requiring AWS IAM credentials.",
        specs: ["IRSA Verification", "ALB Ingress", "CSI Secrets"],
        badge: "EKS Ready"
    },
    {
        name: "Google Cloud GKE",
        category: "Google Cloud",
        desc: "Audits Gateway API HTTPRoutes, GKE Workload Identity bindings, and Autopilot Pod Security baseline policies locally in under 15ms.",
        specs: ["Gateway API", "Workload Identity", "Autopilot Baseline"],
        badge: "GKE Ready"
    },
    {
        name: "Microsoft Azure AKS",
        category: "Azure Cloud",
        desc: "Reconciles Azure CNI port mappings, Application Gateway Ingress (AGIC) backends, and Key Vault SecretProviderClass manifests.",
        specs: ["Azure CNI", "AGIC Ingress", "Key Vault CSI"],
        badge: "AKS Ready"
    },
    {
        name: "Red Hat OpenShift",
        category: "Enterprise K8s",
        desc: "Strictly verifies SecurityContextConstraints (SCC), OpenShift Route objects, and multi-tenant namespace boundaries across hybrid topologies.",
        specs: ["SCC Enforce", "Route Objects", "Multi-Tenant"],
        badge: "OCP Ready"
    },
    {
        name: "Talos & Bare-Metal",
        category: "Edge & On-Prem",
        desc: "Hermetic offline verification for air-gapped datacenters, immutable OS clusters, and edge K3s nodes with zero outbound internet egress.",
        specs: ["100% Air-Gapped", "Talos Linux", "K3s / Edge"],
        badge: "Hermetic"
    },
    {
        name: "CNCF Open Standards",
        category: "Neutral Core",
        desc: "Definitive schema validation against official Kubernetes OpenAPI v1.21–v1.33+ specs. Standard SARIF reporting for any CI/CD pipeline.",
        specs: ["OpenAPI v1.33+", "SARIF v2.1", "Zero Lock-In"],
        badge: "CNCF Aligned"
    }
];

export default function CloudNeutrality() {
    return (
        <section className="py-20 bg-white dark:bg-[#0D1117] border-t border-slate-200 dark:border-slate-800 transition-colors duration-300">
            <div className="max-w-7xl mx-auto px-8">

                {/* Header */}
                <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
                    <RevealAnimation>
                        <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3.5 py-1.5 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20">
                            Vendor-Neutral Architecture
                        </span>
                    </RevealAnimation>

                    <RevealAnimation delay={100}>
                        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight leading-[1.15]">
                            Cloud-Agnostic.{" "}
                            <span className="text-[#4285F4]">Zero Vendor Lock-In.</span>
                        </h2>
                    </RevealAnimation>

                    <RevealAnimation delay={200}>
                        <p className="text-slate-600 dark:text-slate-400 text-base md:text-lg leading-relaxed">
                            Yamlr is an independent resolution plane. It runs 100% in your local terminal and CI pipelines—validating and repairing Kubernetes manifests across any hyperscaler, managed service, or bare-metal cluster without cluster credentials.
                        </p>
                    </RevealAnimation>
                </div>

                {/* Cloud Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                    {CLOUD_PLATFORMS.map((cloud, idx) => (
                        <RevealAnimation key={cloud.name} delay={idx * 50}>
                            <div className="h-full p-7 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 hover:border-[#4285F4]/40 hover:shadow-lg hover:shadow-blue-500/5 transition-all duration-200 flex flex-col justify-between group">
                                <div>
                                    <div className="flex items-center justify-between mb-4">
                                        <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                            {cloud.category}
                                        </span>
                                        <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/10 text-[#4285F4] border border-blue-500/20">
                                            {cloud.badge}
                                        </span>
                                    </div>

                                    <h3 className="text-lg font-bold font-outfit text-slate-900 dark:text-white mb-2.5 group-hover:text-[#4285F4] transition-colors">
                                        {cloud.name}
                                    </h3>

                                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-6 font-normal">
                                        {cloud.desc}
                                    </p>
                                </div>

                                <div className="flex flex-wrap gap-1.5 pt-4 border-t border-slate-200/60 dark:border-slate-800/60">
                                    {cloud.specs.map((spec) => (
                                        <span 
                                            key={spec} 
                                            className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded bg-slate-200/60 dark:bg-slate-800/60"
                                        >
                                            <CheckCircle2 size={10} className="text-emerald-500" />
                                            {spec}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </RevealAnimation>
                    ))}
                </div>

                {/* Bottom Trust Assurance */}
                <RevealAnimation delay={300}>
                    <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-500/5 via-indigo-500/5 to-purple-500/5 border border-blue-500/10 dark:border-blue-500/20 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-[#4285F4] shrink-0">
                                <Lock size={20} />
                            </div>
                            <div>
                                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                                    100% Offline & Air-Gapped Manifest Auditing
                                </h4>
                                <p className="text-xs text-slate-500 dark:text-slate-400">
                                    No kubeconfig required. No outbound cluster API queries. Zero manifest telemetry.
                                </p>
                            </div>
                        </div>

                        <Link
                            href="/docs/security-architecture"
                            className="inline-flex items-center gap-2 text-xs font-bold text-[#4285F4] hover:text-[#3367D6] whitespace-nowrap transition-colors"
                        >
                            Read Security Architecture &rarr;
                        </Link>
                    </div>
                </RevealAnimation>

            </div>
        </section>
    );
}
