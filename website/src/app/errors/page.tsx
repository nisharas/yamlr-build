import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import Link from 'next/link';
import { DETECTORS } from '@/data/detectors';
import { Shield, ArrowRight, Activity, Wrench, Search } from 'lucide-react';

import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Kubernetes Error & Violation Catalog | Yamlr',
    description: 'Comprehensive directory of Kubernetes configuration hazards, silent outages, security risks, and automated Yamlr healing rules.',
    alternates: { canonical: 'https://yamlr.dev/errors/' },
    openGraph: {
        title: 'Kubernetes Error & Violation Catalog | Yamlr',
        description: 'Comprehensive directory of Kubernetes configuration hazards, silent outages, security risks, and automated Yamlr healing rules.',
        url: 'https://yamlr.dev/errors/',
    },
};

export default function ErrorsCatalogPage() {
    const categories = Array.from(new Set(DETECTORS.map(d => d.category)));

    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] text-slate-900 dark:text-slate-100 selection:bg-[#4285F4]/10 selection:text-[#4285F4] transition-colors duration-200">
            <Navigation />

            <main className="max-w-6xl mx-auto px-6 pt-20 sm:pt-24 pb-20">
                {/* Hero Header */}
                <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 text-[#4285F4] text-xs font-semibold">
                        <Activity className="w-3.5 h-3.5" />
                        Forensic Violation Catalog ({DETECTORS.length} Detectors)
                    </div>
                    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight leading-tight">
                        Kubernetes Manifest Hazard Directory
                    </h1>
                    <p className="text-base sm:text-lg text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
                        Explore every silent outage pattern, security vulnerability, and API deprecation detected and surgically healed by the Yamlr engine.
                    </p>
                </div>

                {/* Categories & Rules Grid */}
                <div className="space-y-12">
                    {categories.map(cat => {
                        const rules = DETECTORS.filter(d => d.category === cat);
                        return (
                            <div key={cat} className="space-y-4">
                                <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                                    <h2 className="text-xl font-bold font-outfit text-slate-900 dark:text-white flex items-center gap-2">
                                        <Shield className="w-5 h-5 text-[#4285F4]" />
                                        {cat} Rules
                                    </h2>
                                    <span className="text-xs font-mono text-slate-400">
                                        {rules.length} detector{rules.length > 1 ? 's' : ''}
                                    </span>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {rules.map(rule => {
                                        const severityBadge = {
                                            CRITICAL: 'text-rose-600 dark:text-rose-400 border-rose-500/30 bg-rose-50 dark:bg-rose-500/10',
                                            ERROR: 'text-amber-600 dark:text-amber-400 border-amber-500/30 bg-amber-50 dark:bg-amber-500/10',
                                            WARNING: 'text-yellow-600 dark:text-yellow-400 border-yellow-500/30 bg-yellow-50 dark:bg-yellow-500/10',
                                            INFO: 'text-blue-600 dark:text-blue-400 border-blue-500/30 bg-blue-50 dark:bg-blue-500/10',
                                        }[rule.severity];

                                        return (
                                            <Link
                                                key={rule.id}
                                                href={`/errors/${rule.id.toLowerCase()}`}
                                                className="group block p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#161B22] hover:bg-white dark:hover:bg-[#1C2128] hover:border-[#4285F4]/40 hover:shadow-md transition-all"
                                            >
                                                <div className="flex items-center justify-between gap-2 mb-2.5">
                                                    <span className="font-mono text-sm font-bold text-[#4285F4]">
                                                        {rule.id}
                                                    </span>
                                                    <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${severityBadge}`}>
                                                        {rule.severity}
                                                    </span>
                                                </div>
                                                <h3 className="text-sm font-bold font-outfit text-slate-900 dark:text-slate-100 group-hover:text-[#4285F4] transition-colors line-clamp-1 mb-1.5">
                                                    {rule.name}
                                                </h3>
                                                <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed mb-3">
                                                    {rule.rationale}
                                                </p>
                                                <div className="flex items-center gap-1 text-xs font-semibold text-[#4285F4] group-hover:translate-x-0.5 transition-transform">
                                                    <span>View failure rationale & fix</span>
                                                    <ArrowRight className="w-3.5 h-3.5" />
                                                </div>
                                            </Link>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </main>

            <Footer />
        </div>
    );
}
