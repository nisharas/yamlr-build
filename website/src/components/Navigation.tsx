"use client";

import Link from "next/link";
import { Github, Menu, X, Search, Command, Star } from "lucide-react";
import { useState, useEffect } from "react";
import ThemeToggle from "./ThemeToggle";
import CommandPalette from "./CommandPalette";

interface NavigationProps {
    showAnnouncement?: boolean;
}

export default function Navigation({ showAnnouncement = false }: NavigationProps) {
    const [mobileOpen, setMobileOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const [announcementDismissed, setAnnouncementDismissed] = useState(false);
    const [paletteOpen, setPaletteOpen] = useState(false);
    const [isMac, setIsMac] = useState(true);

    useEffect(() => {
        setIsMac(/(mac|iphone|ipad)/i.test(navigator.userAgent));
        const handleScroll = () => setScrolled(window.scrollY > 10);
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    useEffect(() => {
        document.body.style.overflow = mobileOpen ? "hidden" : "";
        return () => { document.body.style.overflow = ""; };
    }, [mobileOpen]);

    // Global keyboard shortcut for CommandPalette (Cmd+K / Ctrl+K)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                setPaletteOpen(v => !v);
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, []);

    const navLinks = [
        { href: "/docs", label: "Documentation" },
        { href: "/sandbox", label: "Sandbox" },
        { href: "/mcp", label: "AI & MCP" },
        { href: "/helm", label: "Helm & Kustomize" },
        { href: "/errors", label: "Violations" },
        { href: "/#pricing", label: "Pricing" },
    ];

    return (
        <>
            <header className="fixed top-0 inset-x-0 z-[100] transition-all duration-200">
                <nav
                    className={`h-14 flex items-center transition-all duration-200 ${scrolled
                        ? "bg-white/85 dark:bg-[#0D1117]/85 backdrop-blur-md border-b border-slate-200/70 dark:border-slate-800/70 shadow-xs"
                        : "bg-white dark:bg-[#0D1117] border-b border-slate-200 dark:border-slate-800"
                        }`}
                >
                    <div className="max-w-7xl mx-auto w-full px-6 flex items-center justify-between">

                        {/* Brand + Desktop Links */}
                        <div className="flex items-center gap-8">
                            <Link href="/" aria-label="yamlr. home" className="flex items-center focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] rounded-md">
                                <span className="text-2xl sm:text-[28px] font-extrabold tracking-tight text-slate-950 dark:text-white font-outfit leading-none">
                                    yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span>
                                </span>
                            </Link>

                            <div className="hidden md:flex items-center gap-5 lg:gap-6">
                                {navLinks.map(({ href, label }) => (
                                    <Link
                                        key={href}
                                        href={href}
                                        className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white tracking-normal transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] rounded-sm py-1"
                                    >
                                        {label}
                                    </Link>
                                ))}
                            </div>
                        </div>

                        {/* Right side controls */}
                        <div className="flex items-center gap-2 sm:gap-3">
                            {/* Search Palette Trigger */}
                            <button
                                onClick={() => setPaletteOpen(true)}
                                aria-label="Search documentation"
                                className="flex items-center gap-2 px-2.5 py-1.5 h-9 rounded-lg bg-slate-100 hover:bg-slate-200/70 dark:bg-slate-800/80 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white border border-slate-200/60 dark:border-slate-700/60 transition-all text-xs font-medium focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4]"
                            >
                                <Search size={14} className="shrink-0" />
                                <span className="hidden xl:inline text-slate-400 dark:text-slate-400">Search docs...</span>
                                <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[11px] font-mono font-bold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded text-slate-400">
                                    {isMac ? <><Command size={10} />K</> : 'Ctrl+K'}
                                </kbd>
                            </button>

                            <ThemeToggle />

                            <a
                                href="https://github.com/yamlr/yamlr"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1.5 h-9 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50 hover:bg-slate-100 dark:bg-slate-900/60 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white text-xs font-semibold transition-all focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4]"
                                aria-label="View yamlr. on GitHub"
                            >
                                <Github size={14} />
                                <span>GitHub</span>
                            </a>

                            <Link
                                href="/#install"
                                aria-label="Install the yamlr. CLI"
                                className="hidden sm:flex items-center gap-2 px-4 py-2 h-9 rounded-full bg-[#4285F4] hover:bg-[#3367D6] active:bg-[#2a56c6] text-white text-xs font-bold tracking-normal transition-all duration-150 active:scale-[0.98] shadow-xs focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117]"
                            >
                                Install CLI
                            </Link>

                            {/* Hamburger — mobile only */}
                            <button
                                className="md:hidden p-2 text-slate-500 hover:text-slate-950 dark:hover:text-white transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] rounded-md"
                                onClick={() => setMobileOpen((v) => !v)}
                                aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
                                aria-expanded={mobileOpen}
                            >
                                {mobileOpen ? <X size={20} /> : <Menu size={20} />}
                            </button>
                        </div>
                    </div>
                </nav>
            </header>

            {/* Global Cmd+K Command Palette Modal */}
            <CommandPalette isOpen={paletteOpen} onClose={() => setPaletteOpen(false)} />

            {/* Mobile Menu Drawer Overlay */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 z-[101] bg-white dark:bg-[#0D1117] px-6 py-4 flex flex-col"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Mobile navigation menu"
                >
                    {/* Drawer Header */}
                    <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800 mb-4">
                        <Link href="/" onClick={() => setMobileOpen(false)} className="flex items-center">
                            <span className="text-[27px] font-extrabold tracking-tight text-slate-950 dark:text-white font-outfit leading-none">
                                yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span>
                            </span>
                        </Link>
                        <button
                            onClick={() => setMobileOpen(false)}
                            className="p-2 rounded-lg text-slate-500 hover:text-slate-950 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            aria-label="Close menu"
                        >
                            <X size={20} />
                        </button>
                    </div>

                    <div className="flex flex-col gap-1 flex-1 overflow-y-auto">
                        {/* Mobile Search button */}
                        <button
                            onClick={() => {
                                setMobileOpen(false);
                                setPaletteOpen(true);
                            }}
                            className="flex items-center justify-between p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-semibold text-sm mb-4"
                        >
                            <span className="flex items-center gap-2.5">
                                <Search size={16} className="text-slate-400" />
                                Search documentation & CLI...
                            </span>
                            <kbd className="px-2 py-0.5 text-[11px] font-mono bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded text-slate-400">
                                {isMac ? '⌘K' : 'Ctrl+K'}
                            </kbd>
                        </button>

                        {navLinks.map(({ href, label }) => (
                            <Link
                                key={href}
                                href={href}
                                onClick={() => setMobileOpen(false)}
                                className="text-lg font-semibold text-slate-800 dark:text-slate-200 hover:text-[#4285F4] dark:hover:text-[#4285F4] py-3.5 border-b border-slate-100 dark:border-slate-800/80 transition-colors"
                            >
                                {label}
                            </Link>
                        ))}

                        {/* Mobile CTA */}
                        <div className="pt-6">
                            <Link
                                href="/#install"
                                onClick={() => setMobileOpen(false)}
                                aria-label="Install the yamlr. CLI"
                                className="flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-[#4285F4] hover:bg-[#3367D6] text-white text-sm font-bold tracking-normal transition-all"
                            >
                                Install CLI
                            </Link>
                        </div>

                        {/* Mobile GitHub */}
                        <div className="pt-3">
                            <a
                                href="https://github.com/yamlr/yamlr"
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={() => setMobileOpen(false)}
                                className="flex items-center justify-center gap-2 px-6 py-3 rounded-full border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-bold tracking-normal transition-all hover:bg-slate-50 dark:hover:bg-slate-800/60"
                            >
                                <Github size={16} />
                                <span>Star on GitHub</span>
                                <Star size={13} className="fill-amber-400 text-amber-400 ml-0.5" />
                            </a>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}