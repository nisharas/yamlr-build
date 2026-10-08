"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
    Search, 
    Terminal, 
    BookOpen, 
    ShieldAlert, 
    ArrowRight, 
    X, 
    Command,
    Activity,
    Layers,
    Bot,
    ExternalLink
} from "lucide-react";

interface SearchItem {
    title: string;
    description: string;
    category: "Commands" | "Guides" | "Detectors" | "Tools";
    href: string;
    icon: React.ReactNode;
    badge?: string;
}

const SEARCH_INDEX: SearchItem[] = [
    // Core Guides & Tools
    { title: "Downloads & Installation", description: "Standalone binaries for Linux, macOS, Windows, and package managers", category: "Guides", href: "/docs/installation", icon: <Terminal size={16} /> },
    { title: "Getting Started Guide", description: "Execute your first automated scan and lossless auto-heal in 60 seconds", category: "Guides", href: "/docs/getting-started", icon: <BookOpen size={16} /> },
    { title: "Core Concepts", description: "ResourceGraph, Semantic Validation, and Risk Classification", category: "Guides", href: "/docs/core-concepts", icon: <Activity size={16} /> },
    { title: "Security Architecture", description: "Zero-Data Egress, local-first engine, air-gapped auditing", category: "Guides", href: "/docs/security-architecture", icon: <BookOpen size={16} /> },
    { title: "CI/CD & GitOps Integration", description: "GitHub Actions, GitLab CI, Pre-commit hooks, and exit codes", category: "Guides", href: "/docs/ci-cd-integration", icon: <Layers size={16} /> },
    { title: "AI & Model Context Protocol (MCP)", description: "Local MCP server integration for AI coding assistants and IDEs", category: "Tools", href: "/mcp", icon: <Bot size={16} /> },
    { title: "Helm & Kustomize Auditing", description: "In-memory template rendering and values.yaml auto-healing", category: "Tools", href: "/helm", icon: <Layers size={16} /> },
    { title: "Interactive Sandbox", description: "Test real-time YAML healing in your browser with zero install", category: "Tools", href: "/sandbox", icon: <Activity size={16} /> },
    { title: "Hazard Catalog & Detectors", description: "Directory of silent outage patterns and security risks", category: "Tools", href: "/errors", icon: <ShieldAlert size={16} /> },

    // Top CLI Commands
    { title: "yamlr scan", description: "Fast-path forensic manifest analysis with SQLite ResourceGraph", category: "Commands", href: "/docs/yamlr-scan", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr heal", description: "Surgically repair invalid manifests with 100% comment preservation", category: "Commands", href: "/docs/yamlr-heal", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr diff", description: "Preview unified terminal diffs of proposed AST mutations", category: "Commands", href: "/docs/yamlr-diff", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr verify", description: "Verify cryptographic SHA-256 DNA signatures and manifest integrity", category: "Commands", href: "/docs/yamlr-verify", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr sign", description: "Cryptographically sign healed manifest batches with DNA receipts", category: "Commands", href: "/docs/yamlr-sign", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr fleet", description: "Multi-cluster and fleet-wide reconciliation with drift detection", category: "Commands", href: "/docs/yamlr-fleet", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr doctor", description: "Environment, schema compatibility and target K8s version diagnostic", category: "Commands", href: "/docs/yamlr-doctor", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr schema", description: "Display supported Kubernetes OpenAPI versions (v1.21 → v1.37)", category: "Commands", href: "/docs/yamlr-schema", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr mcp", description: "Launch native Model Context Protocol server for AI coding agents", category: "Commands", href: "/docs/yamlr-mcp", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr lsp", description: "Start Language Server Protocol daemon for VS Code and Neovim", category: "Commands", href: "/docs/yamlr-lsp", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr graph", description: "Inspect cross-resource dependency graph and surface orphaned nodes", category: "Commands", href: "/docs/yamlr-graph", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr roi", description: "Calculate engineering hours and outage downtime costs saved", category: "Commands", href: "/docs/yamlr-roi", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr baseline", description: "Generate baseline snapshot to track and suppress historical warnings", category: "Commands", href: "/docs/yamlr-baseline", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr audit", description: "Deep security, CIS Benchmark, and PSS compliance verification", category: "Commands", href: "/docs/yamlr-audit", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr fmt", description: "Format and canonicalize manifest indentation and keys losslessly", category: "Commands", href: "/docs/yamlr-fmt", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr fix", description: "Targeted single-rule remediation for specific manifest errors", category: "Commands", href: "/docs/yamlr-fix", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr secure", description: "Harden manifests to Pod Security Standards (PSS Baseline/Restricted)", category: "Commands", href: "/docs/yamlr-secure", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr rollback", description: "Instant zero-downtime atomic rollback to previous backup state", category: "Commands", href: "/docs/yamlr-rollback", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr upgrade", description: "Automatically upgrade deprecated apiVersions to current K8s target", category: "Commands", href: "/docs/yamlr-upgrade", icon: <Terminal size={16} />, badge: "CLI" },
    { title: "yamlr admin", description: "Machine ID verification, offline key activation, and license telemetry", category: "Commands", href: "/docs/yamlr-admin", icon: <Terminal size={16} />, badge: "CLI" },

    // Forensic Detectors
    { title: "NET-001: Port Collision & Invisible Outage", description: "Mismatched Service port/targetPort and containerPort causing silent traffic loss", category: "Detectors", href: "/errors/net-001", icon: <ShieldAlert size={16} />, badge: "CRITICAL" },
    { title: "NET-002: Orphaned Ingress Backend", description: "Ingress references a Service that does not exist in target namespace", category: "Detectors", href: "/errors/net-002", icon: <ShieldAlert size={16} />, badge: "CRITICAL" },
    { title: "NET-003: Localhost Binding Trap", description: "Service targeting 127.0.0.1 fails across container network boundaries", category: "Detectors", href: "/errors/net-003", icon: <ShieldAlert size={16} />, badge: "ERROR" },
    { title: "SEC-001: Hardcoded Secret Leak", description: "Plaintext AWS access keys, private keys, or Slack tokens in manifests", category: "Detectors", href: "/errors/sec-001", icon: <ShieldAlert size={16} />, badge: "CRITICAL" },
    { title: "SEC-004: Root Execution Violation", description: "Containers running as root without runAsNonRoot: true in PSS Restricted", category: "Detectors", href: "/errors/sec-004", icon: <ShieldAlert size={16} />, badge: "ERROR" },
    { title: "DEP-001: Deprecated Ingress API", description: "extensions/v1beta1 Ingress apiVersion deprecated in K8s v1.22+", category: "Detectors", href: "/errors/dep-001", icon: <ShieldAlert size={16} />, badge: "WARNING" },
    { title: "RES-001: OOMKill Hazard", description: "Missing memory limits risking unconstrained node eviction", category: "Detectors", href: "/errors/res-001", icon: <ShieldAlert size={16} />, badge: "WARNING" },
];

interface CommandPaletteProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
    const router = useRouter();
    const [query, setQuery] = useState("");
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

    const filtered = query.trim() === ""
        ? SEARCH_INDEX.slice(0, 10)
        : SEARCH_INDEX.filter(item => 
            item.title.toLowerCase().includes(query.toLowerCase()) ||
            item.description.toLowerCase().includes(query.toLowerCase()) ||
            item.category.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 12);

    useEffect(() => {
        if (isOpen) {
            setQuery("");
            setSelectedIndex(0);
            setTimeout(() => inputRef.current?.focus(), 50);
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "";
        }
        return () => { document.body.style.overflow = ""; };
    }, [isOpen]);

    useEffect(() => {
        setSelectedIndex(0);
    }, [query]);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!isOpen) return;

            if (e.key === "Escape") {
                e.preventDefault();
                onClose();
            } else if (e.key === "ArrowDown") {
                e.preventDefault();
                setSelectedIndex(i => (i + 1) % (filtered.length || 1));
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setSelectedIndex(i => (i - 1 + (filtered.length || 1)) % (filtered.length || 1));
            } else if (e.key === "Enter" && filtered[selectedIndex]) {
                e.preventDefault();
                const target = filtered[selectedIndex].href;
                onClose();
                router.push(target);
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isOpen, filtered, selectedIndex, onClose, router]);

    if (!isOpen) return null;

    return (
        <div 
            className="fixed inset-0 z-[200] flex items-start justify-center pt-20 px-4 sm:px-6 bg-slate-950/60 backdrop-blur-sm transition-opacity animate-in fade-in duration-150"
            onClick={onClose}
            role="dialog"
            aria-modal="true"
            aria-label="Command Palette"
        >
            <div 
                className="w-full max-w-2xl bg-white dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150"
                onClick={e => e.stopPropagation()}
            >
                {/* Search Input Bar */}
                <div className="flex items-center gap-3 px-5 py-3.5 border-b border-slate-200 dark:border-slate-800">
                    <Search size={18} className="text-slate-400 shrink-0" />
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="Search CLI commands, documentation, and error catalog..."
                        className="w-full bg-transparent text-slate-900 dark:text-white placeholder-slate-400 text-sm font-medium focus:outline-none"
                    />
                    <div className="flex items-center gap-1.5 shrink-0">
                        <kbd className="px-2 py-0.5 text-[11px] font-mono font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded">
                            ESC
                        </kbd>
                    </div>
                </div>

                {/* Results List */}
                <div className="max-h-[380px] overflow-y-auto p-2 divide-y divide-slate-100 dark:divide-slate-800/40">
                    {filtered.length === 0 ? (
                        <div className="py-12 text-center text-slate-400 text-sm">
                            No results found for &ldquo;<span className="text-slate-600 dark:text-slate-300 font-semibold">{query}</span>&rdquo;
                        </div>
                    ) : (
                        filtered.map((item, idx) => {
                            const isSelected = idx === selectedIndex;
                            return (
                                <div
                                    key={item.href + item.title}
                                    onMouseEnter={() => setSelectedIndex(idx)}
                                    onClick={() => {
                                        onClose();
                                        router.push(item.href);
                                    }}
                                    className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors ${
                                        isSelected 
                                            ? "bg-[#4285F4]/10 dark:bg-[#4285F4]/15 text-[#4285F4]" 
                                            : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40"
                                    }`}
                                >
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`p-2 rounded-lg shrink-0 ${
                                            isSelected 
                                                ? "bg-[#4285F4] text-white" 
                                                : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                                        }`}>
                                            {item.icon}
                                        </div>
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs font-bold font-mono truncate text-slate-900 dark:text-white">
                                                    {item.title}
                                                </span>
                                                {item.badge && (
                                                    <span className={`text-[11px] font-bold font-mono px-1.5 py-0.5 rounded border ${
                                                        item.badge === "CRITICAL"
                                                            ? "bg-rose-500/10 text-rose-500 border-rose-500/20"
                                                            : item.badge === "CLI"
                                                            ? "bg-blue-500/10 text-blue-500 border-blue-500/20"
                                                            : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                                                    }`}>
                                                        {item.badge}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                                                {item.description}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2 text-slate-400 pl-3 shrink-0">
                                        <span className="text-[11px] font-mono uppercase tracking-wider hidden sm:inline opacity-60">
                                            {item.category}
                                        </span>
                                        <ArrowRight size={14} className={isSelected ? "text-[#4285F4]" : "opacity-40"} />
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                {/* Footer hints */}
                <div className="px-4 py-2.5 bg-slate-50 dark:bg-[#0D1117] border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-400">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1">
                            <kbd className="px-1.5 py-0.5 font-mono text-[11px] bg-slate-200 dark:bg-slate-800 rounded">↑</kbd>
                            <kbd className="px-1.5 py-0.5 font-mono text-[11px] bg-slate-200 dark:bg-slate-800 rounded">↓</kbd>
                            Navigate
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="px-1.5 py-0.5 font-mono text-[11px] bg-slate-200 dark:bg-slate-800 rounded">↵</kbd>
                            Open
                        </span>
                    </div>
                    <span className="font-mono text-[11px] text-slate-400">
                        yamlr.dev search
                    </span>
                </div>
            </div>
        </div>
    );
}
