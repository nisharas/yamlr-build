import React from "react";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { FileText, CheckCircle2, AlertCircle } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Terms of Service | Yamlr",
    description: "Terms of service and software licensing conditions governing Yamlr CLI and yamlr.dev.",
    alternates: { canonical: "https://yamlr.dev/terms/" },
    openGraph: {
        title: "Terms of Service | Yamlr",
        description: "Terms of service and software licensing conditions governing Yamlr CLI and yamlr.dev.",
        url: "https://yamlr.dev/terms/",
    },
};

export default function TermsPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-[#4285F4]/10 selection:text-[#4285F4]">
            <Navigation />

            <main className="flex-1 pt-20 sm:pt-24 pb-16 px-6 sm:px-8">
                <div className="max-w-4xl mx-auto">
                    {/* Header */}
                    <div className="mb-12 pb-8 border-b border-slate-200 dark:border-slate-800">
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 rounded-full mb-4">
                            <FileText size={13} className="text-[#4285F4]" />
                            <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-wider">
                                Legal &amp; Governance
                            </span>
                        </div>
                        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white mb-4">
                            Terms of Service
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 text-sm sm:text-base leading-relaxed max-w-2xl">
                            These Terms of Service (&ldquo;Terms&rdquo;) govern your access to and use of the yamlr.dev website and the Yamlr Command-Line Interface and Autonomous Healing Engine, developed and distributed by Timonel Labs (&ldquo;we&rdquo;, &ldquo;our&rdquo;, or &ldquo;us&rdquo;).
                        </p>
                        <div className="mt-4 text-xs font-mono text-slate-400">
                            Effective Date: January 1, 2026 · Last Revised: March 2026
                        </div>
                    </div>

                    {/* Content Sections */}
                    <div className="space-y-10 text-base leading-relaxed text-slate-700 dark:text-slate-300">
                        {/* Section 1 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                1. Acceptance of Terms
                            </h2>
                            <p>
                                By downloading, installing, running, or accessing the Yamlr binary or accessing the yamlr.dev web portal, you acknowledge that you have read, understood, and agree to be legally bound by these Terms and our Privacy Policy. If you are entering into these Terms on behalf of an enterprise or organization, you represent and warrant that you possess the full legal authority to bind such entity.
                            </p>
                        </section>

                        {/* Section 2 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                2. Software Licensing &amp; Usage Tiers
                            </h2>
                            <p>
                                Yamlr is licensed under a tiered software model designed for zero friction local evaluation and robust enterprise deployment:
                            </p>
                            <div className="grid sm:grid-cols-2 gap-4 mt-4">
                                <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                                    <div className="flex items-center gap-2 mb-2 font-bold font-outfit text-slate-900 dark:text-white">
                                        <CheckCircle2 size={16} className="text-emerald-500" />
                                        <span>Community Tier (Free)</span>
                                    </div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                                        Permits individual software developers and platform engineers to run Yamlr locally for individual testing, learning, manual audits, and interactive manifest repair on individual workstations without cost.
                                    </p>
                                </div>
                                <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                                    <div className="flex items-center gap-2 mb-2 font-bold font-outfit text-slate-900 dark:text-white">
                                        <CheckCircle2 size={16} className="text-[#4285F4]" />
                                        <span>Enterprise &amp; Pro Tier</span>
                                    </div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                                        Required for automated CI/CD pipeline enforcement (e.g. GitHub Actions, GitLab CI, ArgoCD gates), team-wide fleet healing, multi-node cluster synchronization, and production deployment environments.
                                    </p>
                                </div>
                            </div>
                        </section>

                        {/* Section 3 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                3. Local-First Execution &amp; Data Security
                            </h2>
                            <p>
                                Yamlr is strictly engineered as a <strong>Local-First Auto-Healing Engine</strong>. All Concrete Syntax Tree (CST) parsing, cross-resource graph indexing, secret detection, and automated repair operations execute in memory on your host machine or self-hosted pipeline runner.
                            </p>
                            <p>
                                Under no circumstances does Yamlr transmit raw Kubernetes manifests, Helm values, cloud secrets, or application payloads to Timonel Labs or any third-party infrastructure. You retain 100% data residency and confidentiality.
                            </p>
                        </section>

                        {/* Section 4 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                4. Kubernetes Standard Compliance &amp; Compatibility
                            </h2>
                            <p>
                                Yamlr operates as an independent, neutral engine conforming to official Kubernetes OpenAPI schemas and CNCF specifications. We are unaffiliated with any single cloud vendor. Manifest validation and remediation logic is provided on a vendor-agnostic basis across Amazon Elastic Kubernetes Service (EKS), Google Kubernetes Engine (GKE), Azure Kubernetes Service (AKS), Red Hat OpenShift, Talos Linux, and bare-metal environments.
                            </p>
                        </section>

                        {/* Section 5 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                5. Intellectual Property Rights
                            </h2>
                            <p>
                                All source code, binaries, trademarks, logos, documentation, and algorithms embodied in Yamlr (including the native Rust CST parsing engine and deterministic proof specifications) are the exclusive intellectual property of Timonel Labs. You may not reverse engineer, decompile, disassemble, or derive source code from the compiled engine binaries, except to the extent permitted by applicable law.
                            </p>
                        </section>

                        {/* Section 6 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                6. Disclaimer of Warranties
                            </h2>
                            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-sm text-amber-900 dark:text-amber-200 flex gap-3 items-start">
                                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                                <div>
                                    THE SOFTWARE AND WEBSITE ARE PROVIDED ON AN &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; BASIS, WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. WHILE YAMLR STRIVES TO PRESERVE COMMENTS AND SEMANTIC INTEGRITY, YOU ARE RESPONSIBLE FOR REVIEWING AND TESTING ALL REMEDIATED MANIFESTS PRIOR TO PRODUCTION CLUSTER DEPLOYMENT.
                                </div>
                            </div>
                        </section>

                        {/* Section 7 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                7. Limitation of Liability
                            </h2>
                            <p>
                                TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL TIMONEL LABS OR ITS AFFILIATES BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF DATA, WORK INTERRUPTIONS, CLUSTER OUTAGES, OR SYSTEM DOWNTIME RESULTING FROM THE USE OR INABILITY TO USE YAMLR.
                            </p>
                        </section>

                        {/* Section 8 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                8. Governing Law &amp; Contact
                            </h2>
                            <p>
                                These Terms shall be governed by and construed in accordance with the laws of the State of Delaware, United States, without regard to conflict of law principles. For legal inquiries, licensing verifications, or enterprise agreements, please contact:
                            </p>
                            <div className="mt-2 font-mono text-sm bg-slate-100 dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                                Timonel Labs Inc.<br />
                                Legal &amp; Compliance Division<br />
                                Email: <a href="mailto:contact@yamlr.dev" className="text-[#4285F4] hover:underline">contact@yamlr.dev</a><br />
                                Security: <a href="mailto:security@yamlr.dev" className="text-[#4285F4] hover:underline">security@yamlr.dev</a>
                            </div>
                        </section>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
