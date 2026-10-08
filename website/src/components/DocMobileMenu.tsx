"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, X, Book, ChevronRight } from "lucide-react";

interface DocPageItem {
    slug: string;
    title: string;
    category?: string;
}

interface DocMobileMenuProps {
    pages: DocPageItem[];
    currentSlug: string;
}

const CATEGORIES = [
    "Fundamentals",
    "Architecture & Engine",
    "Analysis & Diagnostics",
    "Healing & Remediation",
    "Intelligence & ROI",
    "Metadata & Governance",
    "Utilities & Setup"
];

export default function DocMobileMenu({ pages, currentSlug }: DocMobileMenuProps) {
    const [open, setOpen] = useState(false);

    useEffect(() => {
        if (open) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "";
        }
        return () => {
            document.body.style.overflow = "";
        };
    }, [open]);

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                aria-label="Open documentation navigation menu"
                aria-expanded={open}
                className="lg:hidden flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161B22] text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors shadow-2xs"
            >
                <Menu size={14} />
                <span>Doc Menu</span>
            </button>

            {open && (
                <div
                    className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm lg:hidden flex justify-end"
                    onClick={() => setOpen(false)}
                >
                    <div
                        className="w-full max-w-xs h-full bg-white dark:bg-[#0D1117] border-l border-slate-200 dark:border-slate-800 p-6 flex flex-col overflow-y-auto custom-scrollbar"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800 mb-6">
                            <div className="flex items-center gap-2 text-sm font-bold font-outfit text-slate-900 dark:text-white">
                                <Book size={16} className="text-[#4285F4]" />
                                Documentation
                            </div>
                            <button
                                onClick={() => setOpen(false)}
                                aria-label="Close menu"
                                className="p-1 rounded-md text-slate-400 hover:text-slate-900 dark:hover:text-white"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Navigation Groups */}
                        <div className="space-y-6 flex-1">
                            {CATEGORIES.map((cat) => {
                                const groupPages = pages.filter((p) => {
                                    if (cat === "Fundamentals") return p.category === "Fundamentals" || !p.category;
                                    if (cat === "Architecture & Engine") return p.category === "Advanced";
                                    return p.category === cat;
                                });
                                if (groupPages.length === 0) return null;

                                return (
                                    <div key={cat}>
                                        <h4 className="text-xs font-bold font-outfit uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
                                            {cat}
                                        </h4>
                                        <ul className="space-y-1">
                                            {groupPages.map((page) => {
                                                const isActive = page.slug === currentSlug;
                                                return (
                                                    <li key={page.slug}>
                                                        <Link
                                                            href={`/docs/${page.slug}`}
                                                            onClick={() => setOpen(false)}
                                                            className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                                                                isActive
                                                                    ? "bg-[#4285F4]/10 text-[#4285F4] font-semibold"
                                                                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800/60"
                                                            }`}
                                                        >
                                                            <span className="truncate">{page.title}</span>
                                                            {isActive && (
                                                                <ChevronRight size={14} className="text-[#4285F4] shrink-0" />
                                                            )}
                                                        </Link>
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
