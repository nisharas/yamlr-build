import { notFound } from 'next/navigation';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import Link from 'next/link';
import { DETECTORS, DETECTOR_MAP } from '@/data/detectors';
import InteractiveDiffCard from '@/components/InteractiveDiffCard';
import { AlertTriangle, CheckCircle2, ArrowLeft, Terminal, Wrench, Shield, Sparkles, Activity } from 'lucide-react';

export async function generateStaticParams() {
    const codes = new Set<string>();
    for (const d of DETECTORS) {
        codes.add(d.id.toLowerCase());
        codes.add(d.id.toUpperCase());
    }
    return Array.from(codes).map(code => ({ code }));
}

export default async function ErrorCodePage({
    params
}: {
    params: Promise<{ code: string }>
}) {
    const { code } = await params;
    const detector = DETECTOR_MAP.get(code.toUpperCase());

    if (!detector) {
        notFound();
    }

    const severityColor = {
        CRITICAL: 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/30',
        ERROR: 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/30',
        WARNING: 'bg-yellow-50 dark:bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-200 dark:border-yellow-500/30',
        INFO: 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-500/30'
    }[detector.severity];

    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] text-slate-900 dark:text-slate-100 selection:bg-[#4285F4]/10 selection:text-[#4285F4] font-sans">
            <Navigation />

            <main className="max-w-5xl mx-auto px-6 pt-20 sm:pt-24 pb-20">
                {/* Back to Docs */}
                <Link 
                    href="/errors" 
                    className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#4285F4] dark:text-slate-400 dark:hover:text-[#4285F4] transition-colors mb-8 group font-medium"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    Back to Violation Catalog
                </Link>

                {/* Header Card */}
                <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#161B22] p-8 mb-8">
                    <div className="flex flex-wrap items-center gap-3 mb-4">
                        <span className="font-mono text-xl font-bold text-[#4285F4]">
                            {detector.id}
                        </span>
                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${severityColor}`}>
                            {detector.severity}
                        </span>
                        <span className="text-xs font-medium px-2.5 py-1 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {detector.category}
                        </span>
                        {detector.k8sVersionImpact && (
                            <span className="text-xs font-medium px-2.5 py-1 rounded-full border border-blue-200 dark:border-blue-500/30 bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-300">
                                {detector.k8sVersionImpact}
                            </span>
                        )}
                    </div>

                    <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight mb-4">
                        {detector.name}
                    </h1>

                    <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed max-w-3xl">
                        {detector.rationale}
                    </p>
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                    {/* Left 2 Cols: Fix & Code */}
                    <div className="md:col-span-2 space-y-8">
                        {/* Runtime Outage Analysis (Deep Technical Rationale) */}
                        {detector.failureModeExplainer && (
                            <div className="rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/10 p-6">
                                <h2 className="text-xl font-bold font-outfit text-amber-700 dark:text-amber-300 flex items-center gap-2 mb-3">
                                    <Activity className="w-5 h-5 text-amber-500" />
                                    Kubernetes Runtime Outage Analysis
                                </h2>
                                <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
                                    {detector.failureModeExplainer}
                                </p>
                            </div>
                        )}

                        {/* How to Fix */}
                        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#161B22] p-6">
                            <h2 className="text-xl font-bold font-outfit text-slate-900 dark:text-white flex items-center gap-2 mb-3">
                                <Wrench className="w-5 h-5 text-[#4285F4]" />
                                Recommended Resolution
                            </h2>
                            <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed mb-4">
                                {detector.fixGuide || "Run yamlr heal to automatically resolve this issue across your manifests without dropping existing comments."}
                            </p>

                            <div className="rounded-lg bg-slate-900 dark:bg-[#0D1117] border border-slate-800 p-4 font-mono text-xs text-slate-200 flex items-center justify-between">
                                <code>yamlr heal ./k8s/ --k8s-version 1.30</code>
                                <span className="text-emerald-400 text-[11px] font-semibold">Auto-Heal Safe</span>
                            </div>
                        </div>

                        {/* Interactive Before / After Comparison */}
                        {detector.beforeExample && detector.afterExample && (
                            <InteractiveDiffCard
                                ruleId={detector.id}
                                beforeExample={detector.beforeExample}
                                afterExample={detector.afterExample}
                            />
                        )}
                    </div>

                    {/* Right Column: Quick Actions */}
                    <div className="space-y-6">
                        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#161B22] p-6 space-y-4">
                            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Test in Browser
                            </div>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                Paste your Kubernetes YAML into our interactive sandbox to see Yamlr detect and heal this pattern instantly.
                            </p>
                            <Link
                                href="/sandbox"
                                className="block w-full text-center py-2.5 px-4 rounded-full bg-[#4285F4] hover:bg-[#3367D6] text-white font-bold text-xs transition-colors shadow-xs"
                            >
                                Open Web Sandbox
                            </Link>
                        </div>

                        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#161B22] p-6 space-y-3">
                            <h3 className="text-sm font-bold font-outfit text-slate-900 dark:text-slate-200 flex items-center gap-2">
                                <Shield className="w-4 h-4 text-emerald-500" />
                                Rule Guarantee
                            </h3>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                All Yamlr healing preserves indentation, quotes, inline comments, and formatting deterministically.
                            </p>
                        </div>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
