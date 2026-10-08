"use client";

import React, { useEffect } from 'react';
import Link from 'next/link';
import { BookOpen, FileCode, Shield as ShieldIcon, GitBranch, ChevronRight, Activity, Settings, Terminal, CheckCircle, Search } from "lucide-react";
import Navigation from "@/components/Navigation";
import { RevealAnimation } from "@/components/Hero";

export default function DocsPage() {
    useEffect(() => {
        document.title = "Documentation | Yamlr";
    }, []);

    const [searchQuery, setSearchQuery] = React.useState("");

    const quickstarts = [
        { title: "Downloads & Installation", slug: "installation", desc: "Get the standalone binary for Linux, macOS, and Windows.", icon: <Terminal className="text-slate-600" size={24} /> },
        { title: "Quickstart Guide", slug: "getting-started", desc: "Execute your first automated scan in 60 seconds.", icon: <BookOpen className="text-[#4285F4]" size={24} /> },
    ];

    const intelligence = [
        { title: "Core Concepts", slug: "core-concepts", desc: "ResourceGraph, Semantic Validation, and Risk Classification.", icon: <Activity className="text-indigo-500" size={24} /> },
        { title: "Configuration Spec", slug: "configuration", desc: "Customize the .yamlr.yaml configuration model.", icon: <Settings className="text-slate-500" size={24} /> },
        { title: "Security Architecture", slug: "security-architecture", desc: "Zero-Data Egress and local-first air-gapped auditing.", icon: <ShieldIcon className="text-rose-500" size={24} /> },
        { title: "Compliance & DNA", slug: "compliance-and-dna", desc: "Cryptographic DNA Receipts and regulatory mapping.", icon: <CheckCircle className="text-teal-500" size={24} /> }
    ];

    const remediation = [
        { title: "Features Catalog", href: "/docs/features", desc: "Complete breakdown of detection rules, engine capabilities, and security safeguards.", icon: <FileCode className="text-amber-500" size={24} /> },
        { title: "Yamlr vs Alternatives", href: "/docs/compare", desc: "Side-by-side benchmark comparison against linters, policy gateways, and scanners.", icon: <CheckCircle className="text-teal-500" size={24} /> },
        { title: "Healing Engine Internals", slug: "healing-engine", desc: "Visual diffs, repair mutations, and backup rotation.", icon: <Activity className="text-blue-500" size={24} /> },
        { title: "CI/CD Integration", slug: "ci-cd-integration", desc: "GitHub Actions, Pre-commit hooks, and exit codes.", icon: <GitBranch className="text-purple-500" size={24} /> },
    ];

    const commandGroups = [
        {
            name: "Analysis & Diagnostics",
            commands: [
                { name: "scan", slug: "yamlr-scan" },
                { name: "check", slug: "yamlr-check" },
                { name: "audit", slug: "yamlr-audit" },
                { name: "doctor", slug: "yamlr-doctor" },
                { name: "diagnose", slug: "yamlr-diagnose" },
                { name: "schema", slug: "yamlr-schema" },
                { name: "baseline", slug: "yamlr-baseline" },
                { name: "explain", slug: "yamlr-explain" },
            ]
        },
        {
            name: "Healing & Remediation",
            commands: [
                { name: "heal", slug: "yamlr-heal" },
                { name: "diff", slug: "yamlr-diff" },
                { name: "fmt", slug: "yamlr-fmt" },
                { name: "fix", slug: "yamlr-fix" },
                { name: "fleet", slug: "yamlr-fleet" },
                { name: "secure", slug: "yamlr-secure" },
                { name: "rollback", slug: "yamlr-rollback" },
                { name: "upgrade", slug: "yamlr-upgrade" },
                { name: "migrate", slug: "yamlr-migrate" },
                { name: "restore", slug: "yamlr-restore" },
                { name: "rules", slug: "yamlr-rules" },
            ]
        },
        {
            name: "Intelligence & ROI",
            commands: [
                { name: "graph", slug: "yamlr-graph" },
                { name: "roi", slug: "yamlr-roi" },
                { name: "pulse", slug: "yamlr-pulse" },
                { name: "drift", slug: "yamlr-drift" },
                { name: "stats", slug: "yamlr-stats" },
            ]
        },
        {
            name: "Metadata & Governance",
            commands: [
                { name: "dna", slug: "yamlr-dna" },
                { name: "sign", slug: "yamlr-sign" },
                { name: "verify", slug: "yamlr-verify" },
                { name: "evidence", slug: "yamlr-evidence" },
                { name: "mcp", slug: "yamlr-mcp" },
                { name: "lsp", slug: "yamlr-lsp" },
                { name: "idp-export", slug: "yamlr-idp-export" },
            ]
        },
        {
            name: "Utilities & Setup",
            commands: [
                { name: "admin", slug: "yamlr-admin" },
                { name: "install", slug: "yamlr-install" },
                { name: "subscribe", slug: "yamlr-subscribe" },
                { name: "init", slug: "yamlr-init" },
                { name: "auth", slug: "yamlr-auth" },
                { name: "catalog", slug: "yamlr-catalog" },
                { name: "completion", slug: "yamlr-completion" },
                { name: "status", slug: "yamlr-status" },
                { name: "version", slug: "yamlr-version" },
                { name: "help", slug: "yamlr-help" },
                { name: "welcome", slug: "yamlr-welcome" },
                { name: "manual", slug: "yamlr-manual" },
                { name: "legal", slug: "yamlr-legal" },
            ]
        }
    ];

    const filterDocs = (list: any[]) => list.filter(doc => 
        doc.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
        doc.desc.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const filteredQuickstarts = filterDocs(quickstarts);
    const filteredIntelligence = filterDocs(intelligence);
    const filteredRemediation = filterDocs(remediation);

    const filteredCommandGroups = commandGroups.map(group => ({
        ...group,
        commands: group.commands.filter(cmd => 
            cmd.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            group.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
    })).filter(group => group.commands.length > 0);

    return (
        <div className="min-h-screen bg-white dark:bg-background transition-colors">
            <Navigation />

            <main className="pt-20 sm:pt-24 pb-16 px-6 sm:px-8">
                <div className="max-w-6xl mx-auto">
                    {/* Hero Section */}
                    <div className="text-center mb-10 space-y-4">
                        <RevealAnimation>
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white leading-[1.1]">
                                Documentation<span className="text-[#4285F4]">.</span>
                            </h1>
                        </RevealAnimation>
                        <RevealAnimation delay={100}>
                            <p className="text-base text-slate-500 max-w-xl mx-auto leading-relaxed font-medium">
                                Architected for zero-exfiltration. Search for rules, CLI commands, or core configuration specifications.
                            </p>
                        </RevealAnimation>

                        {/* Search Layer (The Omnibox) */}
                        <RevealAnimation delay={150}>
                            <div className="max-w-2xl mx-auto relative group">
                                <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-[#4285F4] transition-colors">
                                    <Search size={18} />
                                </div>
                                <input 
                                    type="text" 
                                    placeholder="Search Yamlr documentation..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full h-16 pl-14 pr-6 rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-4 focus:ring-[#4285F4]/10 focus:border-[#4285F4] transition-all placeholder:text-slate-400 text-base font-medium shadow-sm"
                                />
                                <div className="absolute inset-y-0 right-5 flex items-center gap-2">
                                    <span className="px-2 py-1 rounded-md bg-white dark:bg-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-widest border border-slate-200 dark:border-slate-700 shadow-sm">Ctrl K</span>
                                </div>
                            </div>
                        </RevealAnimation>
                    </div>

                    {/* Section Clusters */}
                    <div className="space-y-12">
                        
                        {/* 1. Quickstarts */}
                        {filteredQuickstarts.length > 0 && (
                            <section>
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-7 h-7 rounded-lg bg-[#4285F4]/10 flex items-center justify-center">
                                        <Terminal size={16} className="text-[#4285F4]" />
                                    </div>
                                    <h2 className="text-xs font-bold font-outfit uppercase tracking-wider text-slate-500 dark:text-slate-400">Setup &amp; Quickstarts</h2>
                                </div>
                                <div className="grid md:grid-cols-2 gap-4">
                                    {filteredQuickstarts.map((doc, i) => (
                                        <DocCard key={i} {...doc} accent="sky" />
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* 2. Intelligence & Core */}
                        {filteredIntelligence.length > 0 && (
                            <section>
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                                        <Activity size={16} className="text-indigo-500" />
                                    </div>
                                    <h2 className="text-xs font-bold font-outfit uppercase tracking-wider text-slate-500 dark:text-slate-400">Core Intelligence</h2>
                                </div>
                                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                                    {filteredIntelligence.map((doc, i) => (
                                        <DocCard key={i} {...doc} accent="indigo" />
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* 3. Remediation Engine */}
                        {filteredRemediation.length > 0 && (
                            <section>
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center">
                                        <FileCode size={16} className="text-amber-500" />
                                    </div>
                                    <h2 className="text-xs font-bold font-outfit uppercase tracking-wider text-slate-500 dark:text-slate-400">Remediation Engine</h2>
                                </div>
                                <div className="grid md:grid-cols-2 gap-4">
                                    {filteredRemediation.map((doc, i) => (
                                        <DocCard key={i} {...doc} accent="amber" />
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* 4. Command Reference */}
                        <section id="cli-reference" className="pt-8 border-t border-slate-100 dark:border-slate-800 text-density-manual">
                            <div className="flex items-center justify-between mb-8">
                                <div className="space-y-0.5">
                                    <h2 className="text-2xl sm:text-3xl font-bold font-outfit tracking-tight text-slate-950 dark:text-white">CLI Reference</h2>
                                    <p className="text-sm text-slate-500 font-medium">Detailed specifications for all 38 engine commands.</p>
                                </div>
                                <div className="hidden sm:block px-3 py-1 rounded-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider">
                                    38 Commands · 42 Detectors
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                                {filteredCommandGroups.map((group, i) => (
                                    <div key={i} className="space-y-3">
                                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-2 pb-1 border-b border-slate-100 dark:border-slate-800">
                                            <div className="w-1.5 h-1.5 rounded-full bg-[#4285F4]" />
                                            {group.name}
                                        </h3>
                                        <ul className="space-y-0.5">
                                            {group.commands.map((cmd, j) => (
                                                <li key={j}>
                                                    <Link 
                                                        href={`/docs/${cmd.slug}`}
                                                        className="flex items-center justify-between px-3 py-2 rounded-xl border border-transparent hover:border-slate-200 dark:hover:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 group transition-all"
                                                    >
                                                        <span className="font-mono text-sm text-slate-900 dark:text-white flex items-center gap-2">
                                                            <span className="text-slate-400 font-normal">yamlr</span>
                                                            <span className="font-bold text-[#4285F4]">{cmd.name}</span>
                                                        </span>
                                                        <ChevronRight size={14} className="text-slate-300 dark:text-slate-700 group-hover:text-[#4285F4] group-hover:translate-x-1 transition-all" />
                                                    </Link>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    {/* Integrated Help CTA */}
                    <div className="mt-16 p-8 rounded-3xl bg-slate-900 text-white relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6 group">
                        <div className="absolute top-0 right-0 w-[20rem] h-[20rem] bg-[#4285F4]/10 blur-[100px] rounded-full translate-x-1/2 -translate-y-1/2 group-hover:bg-[#4285F4]/15 transition-all duration-500" />
                        <div className="relative z-10 space-y-4">
                            <h2 className="text-3xl sm:text-4xl font-bold font-outfit tracking-tight">CLI Integrated Manual</h2>
                            <p className="text-slate-400 text-base max-w-sm leading-relaxed">
                                Access the full user guide directly in your terminal. No internet required.
                            </p>
                        </div>
                        <div className="relative z-10 px-8 py-5 rounded-xl bg-white/5 border border-white/10 font-mono text-lg text-sky-400 group-hover:border-[#4285F4]/30 transition-all cursor-default">
                            <span className="text-slate-600 mr-4 select-none">$</span>
                            yamlr manual
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

function DocCard({ title, slug, desc, icon, accent, href }: any) {
    const accentColors = {
        sky: "group-hover:text-[#4285F4] group-hover:border-[#4285F4]/20 group-hover:shadow-[#4285F4]/5",
        indigo: "group-hover:text-indigo-500 group-hover:border-indigo-500/20 group-hover:shadow-indigo-500/5",
        amber: "group-hover:text-amber-500 group-hover:border-amber-500/20 group-hover:shadow-amber-500/5",
    };

    const targetUrl = href || `/docs/${slug}`;

    return (
        <Link
            href={targetUrl}
            className={`group p-7 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-card transition-all duration-300 hover:shadow-xl ${accentColors[accent as keyof typeof accentColors]}`}
        >
            <div className="flex items-start justify-between mb-8">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:scale-105 group-hover:bg-white dark:group-hover:bg-slate-800 transition-all duration-300">
                    {icon}
                </div>
                <ChevronRight size={16} className="text-slate-300 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="text-lg font-bold font-outfit text-slate-950 dark:text-white mb-2 tracking-tight">{title}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed mb-6 font-medium">{desc}</p>
            <div className="flex items-center gap-2 text-xs font-bold tracking-wider uppercase text-slate-400 group-hover:text-inherit transition-colors">
                Explore Doc
            </div>
        </Link>
    );
}
