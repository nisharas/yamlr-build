"use client";

import { RevealAnimation } from "./Hero";
import { Shield, Activity, Share2, Layers, Search, Code2, Cpu, ShieldAlert } from "lucide-react";

const FEATURE_PILLARS = [
    {
        name: "Engine Architecture",
        caps: [
            {
                id: "TC-009",
                icon: <Cpu size={20} />,
                title: "Rust-Accelerated Scanning",
                desc: "Native Rust fast-path for identity extraction and lexing. Parallel file scanning with automatic Python fallback.",
            },
            {
                id: "TC-010",
                icon: <Code2 size={20} />,
                title: "Surgical Python Healing",
                desc: "Deep semantic repairs with 100% comment and formatting preservation. Accuracy without compromise.",
            },
        ]
    },
    {
        name: "Detection & Analysis",
        caps: [
            {
                id: "TC-002",
                icon: <Share2 size={20} />,
                title: "ResourceGraph Engine",
                desc: "Persistent SQLite-backed graph for 100k+ nodes. Detects cross-resource blackholes at scale.",
            },
            {
                id: "TC-011",
                icon: <Search size={20} />,
                title: "Cross-Resource Graph",
                desc: "Detects Ghost Services, broken ConfigMap/Secret refs, port mismatches, orphan PVCs, and missing PodDisruptionBudgets across the entire manifest set.",
            },
        ]
    },
    {
        name: "AI & Integrations",
        caps: [
            {
                id: "TC-012",
                icon: <Activity size={20} />,
                title: "MCP Server Interface",
                desc: "Model Context Protocol support. Provides AI agents with conversational safety rationale.",
            },
            {
                id: "TC-013",
                icon: <Layers size={20} />,
                title: "Fleet Sync Control",
                desc: "Bi-directional reconciliation between live cluster state and local source-of-truth.",
            },
        ]
    },
    {
        name: "Security Engine",
        caps: [
            {
                id: "TC-014",
                icon: <ShieldAlert size={20} />,
                title: "Secret Leak Detection",
                desc: "Scans every line — including comments — for exposed AWS keys, Slack tokens, private keys, and cloud connection strings. Outputs SARIF for GitHub Security.",
            },
            {
                id: "TC-015",
                icon: <Shield size={20} />,
                title: "Pod Security Standards",
                desc: "Enforces PSS Baseline and Restricted: hostPath auditing, privilege escalation, seccompProfile, runAsNonRoot, and missing fsGroup.",
            },
        ]
    }
];

interface FeatureCapability {
    id: string;
    icon: React.ReactNode;
    title: string;
    desc: string;
}

// Special Highlight
const DNA_FEATURE: FeatureCapability = {
    id: "TC-008",
    icon: <Shield size={20} />,
    title: "Deterministic Manifest Verification",
    desc: "Deterministic 0-100 metric for manifest health with cryptographic audit seals. Proves production readiness across commits and CI/CD gates.",
};

const cardClass = "h-full p-8 rounded-2xl bg-white dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 hover:border-[#4285F4]/30 hover:shadow-md transition-all duration-150 group";

const FeatureCard = ({ cap }: { cap: FeatureCapability }) => (
    <div className={cardClass}>
        <div className="flex items-center mb-6">
            <div className="text-slate-400 group-hover:text-[#4285F4] transition-colors duration-150">
                {cap.icon}
            </div>
        </div>
        <h4 className="text-lg font-bold font-outfit text-slate-900 dark:text-white mb-3 tracking-tight">
            {cap.title}
        </h4>
        <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
            {cap.desc}
        </p>
    </div>
);

export default function Features() {
    return (
        <section className="py-16 sm:py-20 lg:py-24 bg-slate-50 dark:bg-[#0D1117] border-t border-slate-200 dark:border-slate-800">
            <div className="max-w-7xl mx-auto px-6 sm:px-8">

                {/* Section Header */}
                <div className="mb-16">
                    <RevealAnimation>
                        <div className="space-y-4">
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight">
                                Engineered for Manifest Integrity &amp; Determinism.
                            </h2>
                            <p className="max-w-2xl text-slate-600 dark:text-slate-400 text-lg leading-relaxed font-medium">
                                Deterministic healing. Zero guess-work. Every class of Kubernetes manifest and Helm chart violation &mdash; identified and resolved.
                            </p>
                        </div>
                    </RevealAnimation>
                </div>

                {/* Robust 4-Pillar Grid Architecture */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16 items-stretch">
                    {FEATURE_PILLARS.map((pillar, pIdx) => (
                        <div key={pillar.name} className="flex flex-col gap-4 h-full">
                            {/* Pillar Header */}
                            <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
                                <div className="h-4 w-1 bg-[#4285F4] rounded-full" />
                                <h3 className="text-xs font-bold font-outfit uppercase tracking-wider text-[#4285F4]">
                                    {pillar.name}
                                </h3>
                            </div>

                            {/* Pillar Capability Cards */}
                            <div className="flex flex-col gap-4 flex-1">
                                {pillar.caps.map((cap, cIdx) => (
                                    <RevealAnimation key={cap.id} delay={100 + (pIdx * 60) + (cIdx * 40)} className="flex-1">
                                        <FeatureCard cap={cap} />
                                    </RevealAnimation>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* DNA Highlight — Full Width Impact Card */}
                <RevealAnimation delay={300}>
                    <div className="p-8 rounded-2xl bg-[#4285F4]/5 border border-[#4285F4]/20 flex flex-col md:flex-row items-center gap-8 group hover:border-[#4285F4]/40 transition-all">
                        <div className="w-16 h-16 rounded-full bg-[#4285F4] text-white flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20">
                            <Shield size={32} />
                        </div>
                        <div className="flex-1 text-center md:text-left">
                            <h3 className="text-xl font-bold font-outfit text-slate-900 dark:text-white mb-2">{DNA_FEATURE.title}</h3>
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-2xl">{DNA_FEATURE.desc}</p>
                        </div>
                        <div className="px-6 py-2 rounded-full border border-[#4285F4]/20 text-[11px] font-bold font-outfit uppercase tracking-widest text-[#4285F4]">
                            Engine Verification
                        </div>
                    </div>
                </RevealAnimation>

            </div>
        </section>
    );
}