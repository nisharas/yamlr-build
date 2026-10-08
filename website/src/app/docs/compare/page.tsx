"use client";

import BenchmarkMatrix from "@/components/BenchmarkMatrix";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";

export default function ComparePage() {
    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117]">
            <Navigation />
            <main className="pt-20 sm:pt-24">
                <div className="max-w-7xl mx-auto px-6 sm:px-8 pt-8 pb-4">
                    <h1 className="text-4xl sm:text-5xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white mb-4">
                        Yamlr vs Alternatives<span className="text-[#4285F4]">.</span>
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 text-lg max-w-2xl leading-relaxed mb-8">
                        See how Yamlr compares to static linters, policy gateways, and multi-IaC scanners.
                    </p>
                </div>
                <BenchmarkMatrix />
            </main>
            <Footer />
        </div>
    );
}
