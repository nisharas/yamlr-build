import fs from 'fs';
import path from 'path';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import MarkdownRender from '@/components/MarkdownRender';
import Navigation from '@/components/Navigation';
import DocMobileMenu from '@/components/DocMobileMenu';
import { Github, ChevronLeft, ChevronRight, Calendar, User, Home, Book } from 'lucide-react';

const DOC_PAGES = [
    // Tier 1: Fundamentals
    { slug: "installation", file: "DOWNLOADS.md", title: "Downloads & Installation", category: "Fundamentals" },
    { slug: "getting-started", file: "GETTING_STARTED.md", title: "Getting Started", category: "Fundamentals" },
    { slug: "core-concepts", file: "CORE_CONCEPTS.md", title: "Core Concepts", category: "Fundamentals" },
    { slug: "configuration", file: "CONFIGURATION.md", title: "Configuration Spec", category: "Fundamentals" },
    { slug: "security-architecture", file: "SECURITY_ARCHITECTURE.md", title: "Security Architecture", category: "Fundamentals" },
    { slug: "schema-support", file: "SCHEMA_SUPPORT.md", title: "Schema Support Matrix", category: "Fundamentals" },
    
    // Tier 2: CLI Reference (Analysis & Diagnostics)
    { slug: "yamlr-scan", file: "cli/yamlr_scan.md", title: "yamlr scan", category: "Analysis & Diagnostics" },
    { slug: "yamlr-check", file: "cli/yamlr_check.md", title: "yamlr check", category: "Analysis & Diagnostics" },
    { slug: "yamlr-audit", file: "cli/yamlr_audit.md", title: "yamlr audit", category: "Analysis & Diagnostics" },
    { slug: "yamlr-doctor", file: "cli/yamlr_doctor.md", title: "yamlr doctor", category: "Analysis & Diagnostics" },
    { slug: "yamlr-diagnose", file: "cli/yamlr_diagnose.md", title: "yamlr diagnose", category: "Analysis & Diagnostics" },
    { slug: "yamlr-schema", file: "cli/yamlr_schema.md", title: "yamlr schema", category: "Analysis & Diagnostics" },
    { slug: "yamlr-baseline", file: "cli/yamlr_baseline.md", title: "yamlr baseline", category: "Analysis & Diagnostics" },
    { slug: "yamlr-explain", file: "cli/yamlr_explain.md", title: "yamlr explain", category: "Analysis & Diagnostics" },
    
    // Tier 2: CLI Reference (Healing & Remediation)
    { slug: "yamlr-heal", file: "cli/yamlr_heal.md", title: "yamlr heal", category: "Healing & Remediation" },
    { slug: "yamlr-diff", file: "cli/yamlr_diff.md", title: "yamlr diff", category: "Healing & Remediation" },
    { slug: "yamlr-fmt", file: "cli/yamlr_fmt.md", title: "yamlr fmt", category: "Healing & Remediation" },
    { slug: "yamlr-fix", file: "cli/yamlr_fix.md", title: "yamlr fix", category: "Healing & Remediation" },
    { slug: "yamlr-fleet", file: "cli/yamlr_fleet.md", title: "yamlr fleet", category: "Healing & Remediation" },
    { slug: "yamlr-secure", file: "cli/yamlr_secure.md", title: "yamlr secure", category: "Healing & Remediation" },
    { slug: "yamlr-rollback", file: "cli/yamlr_rollback.md", title: "yamlr rollback", category: "Healing & Remediation" },
    { slug: "yamlr-upgrade", file: "cli/yamlr_upgrade.md", title: "yamlr upgrade", category: "Healing & Remediation" },
    { slug: "yamlr-migrate", file: "cli/yamlr_migrate.md", title: "yamlr migrate", category: "Healing & Remediation" },
    { slug: "yamlr-restore", file: "cli/yamlr_restore.md", title: "yamlr restore", category: "Healing & Remediation" },
    { slug: "yamlr-rules", file: "cli/yamlr_rules.md", title: "yamlr rules", category: "Healing & Remediation" },
    { slug: "yamlr-init", file: "cli/yamlr_init.md", title: "yamlr init", category: "Healing & Remediation" },

    // Tier 2: CLI Reference (Intelligence & ROI)
    { slug: "yamlr-graph", file: "cli/yamlr_graph.md", title: "yamlr graph", category: "Intelligence & ROI" },
    { slug: "yamlr-stats", file: "cli/yamlr_stats.md", title: "yamlr stats", category: "Intelligence & ROI" },
    { slug: "yamlr-roi", file: "cli/yamlr_roi.md", title: "yamlr roi", category: "Intelligence & ROI" },
    { slug: "yamlr-pulse", file: "cli/yamlr_pulse.md", title: "yamlr pulse", category: "Intelligence & ROI" },
    { slug: "yamlr-drift", file: "cli/yamlr_drift.md", title: "yamlr drift", category: "Intelligence & ROI" },

    // Tier 2: CLI Reference (Metadata & Governance)
    { slug: "yamlr-dna", file: "cli/yamlr_dna.md", title: "yamlr dna", category: "Metadata & Governance" },
    { slug: "yamlr-sign", file: "cli/yamlr_sign.md", title: "yamlr sign", category: "Metadata & Governance" },
    { slug: "yamlr-verify", file: "cli/yamlr_verify.md", title: "yamlr verify", category: "Metadata & Governance" },
    { slug: "yamlr-evidence", file: "cli/yamlr_evidence.md", title: "yamlr evidence", category: "Metadata & Governance" },
    { slug: "yamlr-idp-export", file: "cli/yamlr_idp_export.md", title: "yamlr idp-export", category: "Metadata & Governance" },
    { slug: "yamlr-mcp", file: "cli/yamlr_mcp.md", title: "yamlr mcp", category: "Metadata & Governance" },
    { slug: "yamlr-lsp", file: "cli/yamlr_lsp.md", title: "yamlr lsp", category: "Metadata & Governance" },

    // Tier 2: CLI Reference (Utilities & Setup)
    { slug: "yamlr-help", file: "cli/yamlr_help.md", title: "yamlr help", category: "Utilities & Setup" },
    { slug: "yamlr-welcome", file: "cli/yamlr_welcome.md", title: "yamlr welcome", category: "Utilities & Setup" },
    { slug: "yamlr-manual", file: "cli/yamlr_manual.md", title: "yamlr manual", category: "Utilities & Setup" },
    { slug: "yamlr-demo", file: "cli/yamlr_demo.md", title: "yamlr demo", category: "Utilities & Setup" },
    { slug: "yamlr-version", file: "cli/yamlr_version.md", title: "yamlr version", category: "Utilities & Setup" },
    { slug: "yamlr-status", file: "cli/yamlr_status.md", title: "yamlr status", category: "Utilities & Setup" },
    { slug: "yamlr-admin", file: "cli/yamlr_admin.md", title: "yamlr admin", category: "Utilities & Setup" },
    { slug: "yamlr-install", file: "cli/yamlr_install.md", title: "yamlr install", category: "Utilities & Setup" },
    { slug: "yamlr-subscribe", file: "cli/yamlr_subscribe.md", title: "yamlr subscribe", category: "Utilities & Setup" },
    { slug: "yamlr-legal", file: "cli/yamlr_legal.md", title: "yamlr legal", category: "Utilities & Setup" },
    { slug: "yamlr-completion", file: "cli/yamlr_completion.md", title: "yamlr completion", category: "Utilities & Setup" },
    { slug: "yamlr-catalog", file: "cli/yamlr_catalog.md", title: "yamlr catalog", category: "Utilities & Setup" },
    { slug: "yamlr-auth", file: "cli/yamlr_auth.md", title: "yamlr auth", category: "Utilities & Setup" },
    { slug: "yamlr-features", file: "cli/yamlr_features.md", title: "yamlr features", category: "Utilities & Setup" },

    // Tier 3: Advanced Topics
    { slug: "ci-cd-integration", file: "CI_CD_INTEGRATION.md", title: "CI/CD Integration", category: "Advanced" },
    { slug: "healing-engine", file: "HEALING_ENGINE.md", title: "Healing Engine Internals", category: "Advanced" },
    { slug: "compliance-and-dna", file: "COMPLIANCE_AND_DNA.md", title: "Compliance Mapping", category: "Advanced" },
    { slug: "benchmarks", file: "BENCHMARKS.md", title: "Performance Benchmarks", category: "Advanced" },
];

const SLUG_TO_FILE: Record<string, string> = DOC_PAGES.reduce((acc, curr) => {
    acc[curr.slug] = curr.file;
    return acc;
}, {} as Record<string, string>);

export async function generateStaticParams() {
    return Object.keys(SLUG_TO_FILE).map((slug) => ({
        slug: slug,
    }));
}

export default async function DocDetail({ 
    params 
}: { 
    params: Promise<{ slug: string }> 
}) {
    const { slug } = await params;
    const filename = SLUG_TO_FILE[slug];

    if (!filename) {
        notFound();
    }

    const currentIndex = DOC_PAGES.findIndex(p => p.slug === slug);
    const prevPage = currentIndex > 0 ? DOC_PAGES[currentIndex - 1] : null;
    const nextPage = currentIndex < DOC_PAGES.length - 1 ? DOC_PAGES[currentIndex + 1] : null;

    // Try multiple possible paths to project root
    const possiblePaths = [
        path.join(process.cwd(), "docs", filename),      // Root structure (if deployed differently)
        path.join(process.cwd(), "..", "docs", filename), // Native dev/build structure
    ];

    let content = "";
    let found = false;

    for (const p of possiblePaths) {
        try {
            if (fs.existsSync(p)) {
                content = fs.readFileSync(p, 'utf8');
                found = true;
                break;
            }
        } catch (e) {
            continue;
        }
    }

    if (!found) {
        notFound();
    }

    const toc = content.match(/^(#{2,3})\s+(.+)$/gm)?.map(h => {
        const level = h.startsWith('###') ? 3 : 2;
        const rawTitle = h.replace(/^#{2,3}\s+/, '');
        const cleanTitle = rawTitle.replace(/[*_`]/g, '').trim();
        const id = cleanTitle.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s_-]+/g, '-').replace(/^-+|-+$/g, '');
        return { title: cleanTitle, id, level };
    }) || [];

    return (
        <div className="min-h-screen bg-white dark:bg-background transition-colors flex flex-col font-sans">
            <Navigation />

            {/* Breadcrumbs Sub-Bar */}
            <div className="border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0D1117]/95 backdrop-blur-md sticky top-14 z-30 px-6 sm:px-8 py-2.5 mt-14">
                <div className="max-w-[1400px] mx-auto flex items-center justify-between text-xs font-medium gap-4">
                    <div className="flex items-center gap-2 text-slate-500 flex-wrap min-w-0">
                        <Link href="/docs" className="flex items-center gap-1 hover:text-[#4285F4] transition-colors shrink-0">
                            <ChevronLeft size={14} />
                            Documentation
                        </Link>
                        <span className="text-slate-300 dark:text-slate-700">/</span>
                        <span className="text-slate-400 truncate">{(DOC_PAGES.find(p => p.slug === slug)?.category || "Fundamentals")}</span>
                        <span className="text-slate-300 dark:text-slate-700">/</span>
                        <span className="font-semibold text-slate-900 dark:text-white truncate">{DOC_PAGES.find(p => p.slug === slug)?.title}</span>
                    </div>

                    {/* Mobile Doc Navigation Drawer Trigger */}
                    <DocMobileMenu pages={DOC_PAGES} currentSlug={slug} />
                </div>
            </div>

            <main className="pt-6 pb-16 px-6 sm:px-8 max-w-[1400px] mx-auto w-full flex gap-8 lg:gap-10 relative flex-1">
                {/* Left Sidebar */}
                <aside className="hidden lg:block w-64 shrink-0 border-r border-slate-200 dark:border-slate-800 pr-6 overflow-y-auto max-h-[calc(100vh-6.5rem)] sticky top-[6.25rem] custom-scrollbar">
                    <div className="space-y-6">
                        {[
                            "Fundamentals",
                            "Architecture & Engine",
                            "Analysis & Diagnostics",
                            "Healing & Remediation",
                            "Intelligence & ROI",
                            "Metadata & Governance",
                            "Utilities & Setup"
                        ].map((cat) => {
                            const pages = DOC_PAGES.filter(p => {
                                if (cat === "Fundamentals") return p.category === "Fundamentals" || !p.category;
                                if (cat === "Architecture & Engine") return p.category === "Advanced";
                                return p.category === cat;
                            });
                            if (pages.length === 0) return null;

                            return (
                                <div key={cat}>
                                    <div role="heading" aria-level={3} className="text-xs font-bold font-outfit uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2.5">
                                        {cat}
                                    </div>
                                    <ul className="space-y-1">
                                        {pages.map((page) => {
                                            const isActive = page.slug === slug;

                                            return (
                                                <li key={page.slug}>
                                                    <Link
                                                        href={`/docs/${page.slug}`}
                                                        className={`group flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-sans transition-all duration-150 ${
                                                            isActive
                                                                ? "bg-[#4285F4]/10 text-[#4285F4] font-semibold"
                                                                : "text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60"
                                                        }`}
                                                    >
                                                        {isActive && (
                                                            <div className="w-1.5 h-1.5 rounded-full bg-[#4285F4] shrink-0" />
                                                        )}
                                                        <span className="font-medium truncate">
                                                            {page.title}
                                                        </span>
                                                    </Link>
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            );
                        })}
                    </div>
                </aside>

                {/* Main Content Area */}
                <div className="flex-1 min-w-0 flex gap-8 lg:gap-10 items-start">
                    <div className="flex-1 max-w-4xl min-w-0">
                        {/* Meta Header */}
                        <div className="mb-4 flex flex-wrap items-center gap-6 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                            <div className="flex items-center gap-2">
                                <Book size={14} className="text-[#4285F4]" />
                                Authoritative Engine Specification
                            </div>
                        </div>

                        <MarkdownRender content={content} />

                        {/* Sequential Pagination */}
                        <div className="mt-12 pt-10 border-t border-slate-200 dark:border-slate-800 grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                            {prevPage ? (
                                <Link href={`/docs/${prevPage.slug}`} className="flex flex-col items-start p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161B22]/40 hover:border-[#4285F4]/40 hover:shadow-lg hover:shadow-blue-500/5 transition-all group relative overflow-hidden">
                                    <div className="absolute inset-0 bg-gradient-to-br from-sky-50/60 dark:from-[#4285F4]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                    <span className="relative z-10 text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1"><ChevronLeft size={14} className="group-hover:-translate-x-1 transition-transform" /> Previous</span>
                                    <span className="relative z-10 text-base sm:text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#4285F4] transition-colors">{prevPage.title}</span>
                                </Link>
                            ) : <div />}

                            {nextPage ? (
                                <Link href={`/docs/${nextPage.slug}`} className="flex flex-col items-end text-right p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161B22]/40 hover:border-[#4285F4]/40 hover:shadow-lg hover:shadow-blue-500/5 transition-all group relative overflow-hidden">
                                    <div className="absolute inset-0 bg-gradient-to-tl from-sky-50/60 dark:from-[#4285F4]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                    <span className="relative z-10 text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1">Next <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" /></span>
                                    <span className="relative z-10 text-base sm:text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#4285F4] transition-colors">{nextPage.title}</span>
                                </Link>
                            ) : <div />}
                        </div>
                    </div>

                    {/* Right Sidebar (Table of Contents) */}
                    {toc.length > 0 && (
                        <aside className="hidden xl:block w-56 shrink-0 sticky top-[6.25rem] overflow-y-auto max-h-[calc(100vh-6.5rem)] pr-2 custom-scrollbar">
                            <div role="heading" aria-level={3} className="text-xs font-bold font-outfit uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
                                On this page
                            </div>
                            <ul className="space-y-2 border-l border-slate-200 dark:border-slate-800 pl-3">
                                {toc.map((item, i) => (
                                    <li key={i}>
                                        <a 
                                            href={`#${item.id}`} 
                                            className={`block font-medium text-slate-500 dark:text-slate-400 hover:text-[#4285F4] dark:hover:text-[#4285F4] transition-colors leading-relaxed truncate ${
                                                item.level === 3 ? "pl-2 text-[11px]" : "text-xs"
                                            }`}
                                        >
                                            {item.title}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </aside>
                    )}
                </div>
            </main>
        </div>
    );
}
