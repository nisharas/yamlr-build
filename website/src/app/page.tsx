
import { HeroSection } from "@/components/Hero";
import TerminalDisplay from "@/components/Terminal";
import Pricing from "@/components/Pricing";
import Footer from "@/components/Footer";
import Navigation from "@/components/Navigation";
import Workflow from "@/components/Workflow";
import IntegrationSnippetViewer from "@/components/IntegrationSnippetViewer";
import SmartInstall from "@/components/SmartInstall";
import CommentPreservation from "@/components/CommentPreservation";
import DetectorGrid from "@/components/DetectorGrid";

export default function Home() {
    return (
        <div className="flex flex-col min-h-screen bg-white dark:bg-[#0D1117]">
            <Navigation />

            <main className="flex-1">
                {/* Act 1: Hero & Value Foundation */}
                <HeroSection />

                {/* Act 2: Live CLI Demo & Terminal Execution */}
                <section className="py-14 bg-slate-50/50 dark:bg-slate-900/20 border-y border-slate-200/60 dark:border-slate-800/60 relative overflow-hidden">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-500/5 dark:bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />

                    <div className="max-w-5xl mx-auto px-6 sm:px-8 relative z-10">
                        <div className="text-center mb-6 sm:mb-8 space-y-2.5">
                            <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20">
                                Live CLI Demo
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight">
                                See what yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span> actually detects
                            </h2>
                            <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg max-w-xl mx-auto">
                                Real findings from the shipped engine &mdash; Ghost Services, secret leaks, broken references, and port mismatches.
                            </p>
                        </div>
                        <div className="relative mt-8">
                            <TerminalDisplay />
                        </div>
                    </div>
                </section>

                {/* Act 3: Visual Proof & Comment Preservation Moat */}
                <CommentPreservation />

                {/* Act 4: The Healing Architecture & Engine */}
                <Workflow />

                <DetectorGrid />

                {/* Act 5: Developer Workflow & Ecosystem */}
                <section className="py-14 bg-white dark:bg-[#0D1117]">
                    <div className="max-w-5xl mx-auto px-6 sm:px-8">
                        <div className="text-center mb-6 sm:mb-8 space-y-2.5">
                            <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 inline-block">
                                Integrations
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white tracking-tight">
                                Works everywhere you ship.
                            </h2>
                            <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto">
                                Run <span className="font-bold font-outfit tracking-normal">yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span></span> in GitHub Actions, pre-commit hooks, VS Code, or directly in your terminal. Every audit runs locally &mdash; your manifests never leave your environment.
                            </p>
                        </div>

                        {/* Integration Snippets */}
                        <div className="max-w-4xl mx-auto">
                            <IntegrationSnippetViewer />
                        </div>
                    </div>
                </section>

                {/* Act 5: Transparent Pricing & Getting Started */}
                <Pricing />

                <section id="install" className="py-14 bg-white dark:bg-[#0D1117]">
                    <div className="max-w-7xl mx-auto px-6 sm:px-8">
                        <div className="text-center mb-6 sm:mb-8">
                            <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 mb-3 inline-block">
                                Distribution
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit mb-3 tracking-tight">
                                <span className="text-[#326CE5] dark:text-[#5B8BF0]">Install </span>
                                <span className="text-slate-950 dark:text-white">yamlr</span><span className="text-[#059669] dark:text-[#10B981]">.</span>
                            </h2>
                            <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
                                Install the zero-dependency CLI to start scanning and healing locally in seconds.
                            </p>
                        </div>
                        <SmartInstall />
                    </div>
                </section>
            </main>

            <Footer />
        </div>
    );
}