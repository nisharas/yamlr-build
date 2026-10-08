"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Github, Twitter, Linkedin, ArrowUp, Mail, BookOpen, Bug, ShieldCheck, Sliders, Scale, Bot, Boxes, FlaskConical } from "lucide-react";

export default function Footer() {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const toggleVisibility = () => {
            const scrolled = window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
            setIsVisible(scrolled > 150);
        };
        toggleVisibility();
        window.addEventListener("scroll", toggleVisibility, { passive: true });
        document.addEventListener("scroll", toggleVisibility, { passive: true });
        return () => {
            window.removeEventListener("scroll", toggleVisibility);
            document.removeEventListener("scroll", toggleVisibility);
        };
    }, []);

    const scrollToTop = () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
        document.documentElement.scrollTo({ top: 0, behavior: "smooth" });
    };

    return (
        <footer className="relative bg-slate-50 dark:bg-[#0D1117] border-t border-slate-200 dark:border-slate-800 pt-12 pb-6">

            <div className="relative max-w-7xl mx-auto px-6 sm:px-8">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-12 mb-8">

                    {/* Brand Section */}
                    <div className="md:col-span-4 flex flex-col gap-6">
                        <Link href="/" aria-label="yamlr. home" className="flex items-center focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] rounded-md">
                            <span className="font-outfit font-extrabold text-2xl sm:text-[26px] tracking-tight text-slate-900 dark:text-white leading-none">
                                yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span>
                            </span>
                        </Link>

                        <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-sm">
                            The deterministic, comment-preserving auto-healing engine for Kubernetes.
                        </p>

                        {/* Social Links */}
                        <div className="flex items-center gap-3">
                            <a
                                href="https://github.com/yamlr/yamlr"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2.5 rounded-full bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] hover:border-[#4285F4]/30 dark:hover:border-[#4285F4]/30 hover:shadow-sm transition-all duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4]"
                                aria-label="yamlr. on GitHub"
                            >
                                <Github size={18} strokeWidth={2} />
                            </a>
                            <a
                                href="https://twitter.com/yamlr_dev"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2.5 rounded-full bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] hover:border-[#4285F4]/30 dark:hover:border-[#4285F4]/30 hover:shadow-sm transition-all duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4]"
                                aria-label="yamlr. on Twitter / X"
                            >
                                <Twitter size={18} strokeWidth={2} />
                            </a>
                            <a
                                href="https://linkedin.com/company/yamlr"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2.5 rounded-full bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] hover:border-[#4285F4]/30 dark:hover:border-[#4285F4]/30 hover:shadow-sm transition-all duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4]"
                                aria-label="yamlr. on LinkedIn"
                            >
                                <Linkedin size={18} strokeWidth={2} />
                            </a>
                        </div>
                    </div>

                    {/* Resources Column */}
                    <div className="md:col-span-3">
                        <h3 className="text-xs font-bold font-outfit uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 mb-6">
                            Resources
                        </h3>
                        <ul className="flex flex-col gap-4 text-sm font-medium">
                            <li>
                                <Link
                                    href="/docs"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <BookOpen size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    Documentation
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/docs/features"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <Sliders size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    Features Catalog
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/docs/compare"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <Scale size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    yamlr. vs Alternatives
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/mcp"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <Bot size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    AI &amp; MCP Protocol
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/helm"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <Boxes size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    Helm &amp; Kustomize
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/sandbox"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <FlaskConical size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    Sandbox
                                </Link>
                            </li>
                            <li>
                                <a
                                    href="https://github.com/yamlr/yamlr"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="group text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150 flex items-center gap-2"
                                >
                                    <Github size={14} className="text-slate-400 dark:text-slate-500 group-hover:text-[#4285F4]" />
                                    GitHub Releases
                                </a>
                            </li>
                        </ul>
                    </div>

                    {/* Legal & Governance Column */}
                    <div className="md:col-span-2">
                        <h3 className="text-xs font-bold font-outfit uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 mb-6">
                            Trust &amp; Legal
                        </h3>
                        <ul className="flex flex-col gap-4 text-sm font-medium">
                            <li>
                                <Link
                                    href="/terms"
                                    className="text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150"
                                >
                                    Terms of Service
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/privacy"
                                    className="text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150"
                                >
                                    Privacy Charter
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/docs/yamlr-legal"
                                    className="text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150"
                                >
                                    CLI EULA License
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/docs/security-architecture"
                                    className="text-slate-600 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors duration-150"
                                >
                                    Zero-Egress Spec
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Contact Column */}
                    <div className="md:col-span-3">
                        <h3 className="text-xs font-bold font-outfit uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 mb-6">
                            Enterprise
                        </h3>
                        <div className="p-5 rounded-xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed mb-4">
                                Team & Enterprise licensing, air-gapped binary distribution, and custom CRD policy vaults.
                            </p>
                            <a
                                href="mailto:contact@yamlr.dev"
                                className="inline-flex items-center gap-2 text-sm font-bold text-[#4285F4] hover:text-[#3367D6] transition-colors duration-150"
                            >
                                <Mail size={16} />
                                contact@yamlr.dev
                            </a>
                        </div>
                    </div>
                </div>

                {/* Bottom Legal Bar */}
                <div className="pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-medium text-slate-500">
                    <div className="text-center md:text-left">
                        © {new Date().getFullYear()} Timonel Labs. All rights reserved. Zero-Data Egress Architecture.
                    </div>
                    <div className="flex flex-wrap items-center justify-center gap-5 sm:gap-6">
                        <Link href="/terms" className="hover:text-[#4285F4] transition-colors">Terms of Service</Link>
                        <Link href="/privacy" className="hover:text-[#4285F4] transition-colors">Privacy Charter</Link>
                        <Link href="/docs/security-architecture" className="hover:text-[#4285F4] transition-colors">Security</Link>
                    </div>
                </div>
            </div>

            {/* Floating Back to Top Button */}
            <button
                onClick={scrollToTop}
                className={`fixed bottom-6 right-6 sm:bottom-8 sm:right-8 p-3 sm:p-3.5 rounded-full bg-[#4285F4] hover:bg-[#3367D6] active:bg-[#2a56c6] text-white shadow-xl shadow-blue-500/30 z-[90] transition-all duration-300 active:scale-95 cursor-pointer focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117] flex items-center justify-center ${
                    isVisible
                        ? "opacity-100 translate-y-0 pointer-events-auto scale-100"
                        : "opacity-0 translate-y-6 pointer-events-none scale-75"
                }`}
                aria-label="Floating back to top"
            >
                <ArrowUp size={20} strokeWidth={2.5} />
            </button>
        </footer>
    );
}