import React from "react";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { Shield, Lock, EyeOff, Server, Terminal, CheckCircle2 } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Privacy Policy & Zero-Data Egress Charter | Yamlr",
    description: "Yamlr's privacy policy, local-first execution model, and zero manifest exfiltration guarantee.",
    alternates: { canonical: "https://yamlr.dev/privacy/" },
    openGraph: {
        title: "Privacy Policy & Zero-Data Egress Charter | Yamlr",
        description: "Yamlr's privacy policy, local-first execution model, and zero manifest exfiltration guarantee.",
        url: "https://yamlr.dev/privacy/",
    },
};

export default function PrivacyPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-[#4285F4]/10 selection:text-[#4285F4]">
            <Navigation />

            <main className="flex-1 pt-20 sm:pt-24 pb-16 px-6 sm:px-8">
                <div className="max-w-4xl mx-auto">
                    {/* Header */}
                    <div className="mb-12 pb-8 border-b border-slate-200 dark:border-slate-800">
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-100 dark:border-emerald-500/20 rounded-full mb-4">
                            <Shield size={13} className="text-emerald-600 dark:text-emerald-400" />
                            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                                Trust &amp; Data Sovereignty
                            </span>
                        </div>
                        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white mb-4">
                            Privacy Policy &amp; Zero-Data Egress Charter
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 text-sm sm:text-base leading-relaxed max-w-2xl">
                            Yamlr is architected with a fundamental principle: <strong>Your code, manifests, and secrets belong to you alone.</strong> This charter outlines our cryptographic and operational guarantees that your configuration data never leaves your perimeter.
                        </p>
                        <div className="mt-4 text-xs font-mono text-slate-400">
                            Effective Date: January 1, 2026 · Last Revised: March 2026
                        </div>
                    </div>

                    {/* Highlights Grid */}
                    <h2 className="sr-only">Core Privacy Principles</h2>
                    <div className="grid sm:grid-cols-3 gap-4 mb-12">
                        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                            <Lock size={20} className="text-emerald-500 mb-3" />
                            <h3 className="text-lg font-bold font-outfit text-slate-900 dark:text-white mb-1">100% Local-First</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                                CST parsing, graph resolution, and auto-healing run entirely in memory on your host machine.
                            </p>
                        </div>
                        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                            <EyeOff size={20} className="text-[#4285F4] mb-3" />
                            <h3 className="text-lg font-bold font-outfit text-slate-900 dark:text-white mb-1">Zero Manifest Egress</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                                No YAML lines, Helm values, cloud secrets, or cluster endpoints are ever transmitted off-box.
                            </p>
                        </div>
                        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                            <Server size={20} className="text-purple-500 mb-3" />
                            <h3 className="text-lg font-bold font-outfit text-slate-900 dark:text-white mb-1">Air-Gapped Validated</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                                Operates with zero network degradation in fully air-gapped, isolated sovereign networks.
                            </p>
                        </div>
                    </div>

                    {/* Deep Charter Sections */}
                    <div className="space-y-10 text-base leading-relaxed text-slate-700 dark:text-slate-300">
                        {/* Section 1 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                1. What Yamlr Does NOT Collect
                            </h2>
                            <p>
                                When running the Yamlr CLI or invoking its Model Context Protocol (MCP) server interface, the following categories of data are <strong>strictly quarantined</strong> to the local execution context:
                            </p>
                            <ul className="space-y-2.5 mt-2">
                                {[
                                    "Kubernetes YAML manifests, Helm templates, Kustomization files, or CRD schemas.",
                                    "Passwords, API tokens, AWS/GCP/Azure access keys, Slack webhooks, or TLS private keys.",
                                    "Namespace identifiers, internal cluster DNS names, or pod service account tokens.",
                                    "Source code, git commit messages, author names, or file directory hierarchies."
                                ].map((item, i) => (
                                    <li key={i} className="flex items-start gap-2.5 text-sm text-slate-600 dark:text-slate-400">
                                        <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>

                        {/* Section 2 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                2. Anonymous Pulse Signals &amp; Opt-Out
                            </h2>
                            <p>
                                To monitor rule accuracy and verify that the healing engine does not introduce syntactic regressions, Yamlr may transmit a periodic anonymous operational heartbeat (&ldquo;Pulse&rdquo;).
                            </p>
                            <p>
                                A Pulse payload contains only aggregated counts (e.g. number of files audited, rule IDs triggered, execution latency in milliseconds, and CLI version). Pulses contain zero user-identifiable information, zero IP retention, and zero configuration payloads.
                            </p>
                            <div className="p-5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2">
                                <div className="text-sm font-bold font-outfit text-slate-900 dark:text-white flex items-center gap-2">
                                    <Terminal size={15} className="text-[#4285F4]" />
                                    <span>Complete Opt-Out Control</span>
                                </div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    You can permanently disable all network telemetry by setting the environment variable in your shell or CI/CD runner:
                                </p>
                                <code className="block p-3 rounded-lg bg-slate-950 text-slate-100 font-mono text-xs">
                                    export YAMLR_TELEMETRY=0
                                </code>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Alternatively, pass the <code className="font-mono text-xs text-[#4285F4]">--no-telemetry</code> flag to any command. When disabled, Yamlr operates completely silent with zero outbound socket requests.
                                </p>
                            </div>
                        </section>

                        {/* Section 3 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                3. Website Cookies &amp; Tracking
                            </h2>
                            <p>
                                The yamlr.dev documentation and product portal is a statically exported website hosted on global edge CDN infrastructure. We do not use advertising cookies, marketing tracking pixels, or third-party behavioral profiling trackers.
                            </p>
                            <p>
                                Preferences such as light/dark mode are stored exclusively in your browser&rsquo;s local storage and are never transmitted to our servers.
                            </p>
                        </section>

                        {/* Section 4 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                4. Enterprise Compliance &amp; Air-Gapped Environments
                            </h2>
                            <p>
                                For organizations with strict security and governance mandates (PCI-DSS, HIPAA, or air-gapped defense VPCs), Yamlr Pro offers full binary self-containment with zero external dependencies. Binaries can be checksum-verified via SHA-256 digests and deployed directly into disconnected Bastion hosts or sovereign air-gapped VPCs.
                            </p>
                        </section>

                        {/* Section 5 */}
                        <section className="space-y-3">
                            <h2 className="text-2xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                                5. Security Vulnerability Disclosure
                            </h2>
                            <p>
                                We maintain a rigorous coordinated vulnerability disclosure policy. If you discover a security vulnerability or memory safety issue in the Yamlr engine or website, please contact our security team directly:
                            </p>
                            <div className="mt-2 font-mono text-sm bg-slate-100 dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                                Security Response Team<br />
                                Email: <a href="mailto:security@yamlr.dev" className="text-[#4285F4] hover:underline">security@yamlr.dev</a><br />
                                PGP Key ID: Available upon request
                            </div>
                        </section>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
