"use client";

import { useState, useEffect } from "react";
import {
    Apple,
    Laptop,
    Monitor,
    Download,
    Copy,
    Check,
    Terminal as TerminalIcon,
    ChevronRight,
    ArrowLeft,
    CheckCircle2,
    Shield as ShieldIcon,
    Zap as ZapIcon,
    Lock as LockIcon
} from "lucide-react";
import Link from "next/link";

type OS = "macos" | "linux" | "windows";

const STEPS = ["Get Binary", "Global Setup", "Verify"];

export default function SmartInstall() {
    const [activeOS, setActiveOS] = useState<OS>("macos");
    const [activeStep, setActiveStep] = useState(0);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        // Detect OS platform using userAgentData with userAgent fallback
        const detect = async () => {
            let platformStr = "";
            if ((navigator as any).userAgentData?.platform) {
                platformStr = (navigator as any).userAgentData.platform.toLowerCase();
            } else {
                platformStr = navigator.userAgent.toLowerCase();
            }
            if (platformStr.includes("win")) setActiveOS("windows");
            else if (platformStr.includes("linux")) setActiveOS("linux");
            else if (platformStr.includes("mac")) setActiveOS("macos");
        };
        detect();
    }, []);

    const installCommands = {
        macos: {
            step1: "curl -fsSL https://yamlr.dev/install.sh | sh",
            step2: "export PATH=\"$HOME/.local/bin:$PATH\"",
            step3: "yamlr welcome"
        },
        linux: {
            step1: "curl -fsSL https://yamlr.dev/install.sh | sh",
            step2: "export PATH=\"$HOME/.local/bin:$PATH\"",
            step3: "yamlr welcome"
        },
        windows: {
            step1: "irm https://yamlr.dev/install.ps1 | iex",
            step2: "$env:Path += \";$HOME\\.yamlr\\bin\"",
            step3: "yamlr welcome"
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="max-w-3xl mx-auto w-full">
            {/* Step Indicator - CLICKABLE */}
            <div className="flex items-center justify-between mb-8 px-4">
                {STEPS.map((s, i) => (
                    <div key={s} className="flex items-center gap-3">
                        <button
                            onClick={() => setActiveStep(i)}
                            className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold transition-all border-2 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] ${activeStep === i ? "bg-[#4285F4] text-white border-[#4285F4] shadow-lg shadow-blue-500/20 scale-110" : activeStep > i ? "bg-emerald-500 text-white border-emerald-500" : "bg-white dark:bg-[#161B22] text-slate-400 border-slate-200 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-600"}`}
                        >
                            {activeStep > i ? <Check size={16} /> : i + 1}
                        </button>
                        <div className="hidden sm:flex flex-col items-start cursor-pointer" onClick={() => setActiveStep(i)} onKeyDown={(e) => e.key === 'Enter' && setActiveStep(i)} role="button" tabIndex={0} aria-label={`Go to step ${i + 1}: ${s}`}>
                            <span className={`text-[11px] uppercase font-bold tracking-widest ${activeStep === i ? "text-[#4285F4]" : "text-slate-400"}`}>Step {i + 1}</span>
                            <span className={`text-xs font-bold ${activeStep === i ? "text-slate-900 dark:text-slate-100" : "text-slate-500 dark:text-slate-600"}`}>{s}</span>
                        </div>
                        {i < STEPS.length - 1 && <div className="w-8 h-px bg-slate-200 dark:bg-slate-800 mx-2 hidden md:block" />}
                    </div>
                ))}
            </div>

            {/* Platform Selector - PERSISTENT */}
            <div className="rounded-t-2xl border-t border-x border-slate-200 dark:border-slate-800 p-1 flex gap-1 bg-slate-100 dark:bg-[#161B22]">
                {(["macos", "linux", "windows"] as OS[]).map((os) => (
                    <button
                        key={os}
                        onClick={() => setActiveOS(os)}
                        className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-xs font-bold uppercase tracking-wider transition-all rounded-xl focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] ${activeOS === os
                            ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-50 shadow-sm border border-slate-200 dark:border-slate-700"
                            : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-700/50"
                            }`}
                    >
                        {os === "macos" && <Apple size={16} />}
                        {os === "linux" && <TerminalIcon size={16} />}
                        {os === "windows" && <Monitor size={16} />}
                        {os}
                    </button>
                ))}
            </div>

            {/* Main Content Area */}
            <div className="bg-white dark:bg-[#161B22] rounded-b-2xl border border-slate-200 dark:border-slate-800 shadow-2xl relative overflow-hidden min-h-[340px] flex flex-col">
                <div className="p-8 md:p-10 flex-1 flex flex-col">
                    {/* Dynamic Title based on OS + Step */}
                    <div className="mb-8">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-4">
                            {activeOS} Setup
                        </div>
                        <h3 className="text-2xl font-bold font-outfit text-slate-900 dark:text-slate-50">
                            {activeStep === 0 && "Get the Signed Binary"}
                            {activeStep === 1 && "Configure Global Environment"}
                            {activeStep === 2 && "Verify & Initialize Installation"}
                        </h3>
                    </div>

                    <div className="flex-1">
                        {activeStep === 0 && (
                            <div className="space-y-6">
                                <p className="text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg">
                                    {activeOS === 'windows'
                                        ? "Run the 1-line PowerShell installer to download and configure PATH automatically, or download the portable binary."
                                        : "Automate your installation with our secure shell script, or tap directly into our native Homebrew repository."}
                                </p>
                                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                                    <div className="flex-1 min-w-[300px] group flex items-center justify-between p-4 bg-slate-50 dark:bg-[#0D1117] border border-slate-200 dark:border-slate-800 rounded-xl transition-all hover:border-[#4285F4]/30">
                                        <div className="flex items-center gap-4 overflow-hidden">
                                            <TerminalIcon size={18} className="text-[#4285F4] shrink-0" />
                                            <code className="text-slate-900 dark:text-slate-100 font-mono text-sm truncate">
                                                {activeOS === 'windows' ? 'PS> ' : '$ '}
                                                {installCommands[activeOS].step1}
                                            </code>
                                        </div>
                                        <button onClick={() => copyToClipboard(installCommands[activeOS].step1)} aria-label="Copy install command" className="p-2 hover:bg-white dark:hover:bg-slate-800 rounded-lg transition-all text-slate-400 hover:text-[#4285F4] border border-transparent hover:border-slate-200 dark:hover:border-slate-700">
                                            {copied ? <Check size={18} className="text-emerald-500" /> : <Copy size={18} />}
                                        </button>
                                    </div>
                                    </div>
                                    <a
                                        href={
                                            activeOS === "windows"
                                                ? "https://github.com/yamlr/yamlr/releases/latest/download/yamlr-windows-x86_64.zip"
                                                : activeOS === "macos"
                                                ? "https://github.com/yamlr/yamlr/releases/latest/download/yamlr-macos-aarch64.tar.gz"
                                                : "https://github.com/yamlr/yamlr/releases/latest/download/yamlr-linux-x86_64.tar.gz"
                                        }
                                        className="inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:border-[#4285F4] text-slate-700 dark:text-slate-300 text-xs font-bold transition-all shrink-0 hover:bg-slate-50 dark:hover:bg-slate-800"
                                    >
                                        <Download size={14} />
                                        {activeOS === "windows" ? "Download .zip" : "Download .tar.gz"}
                                    </a>
                                </div>
                            </div>
                        )}

                        {activeStep === 1 && (
                            <div className="space-y-6">
                                <p className="text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg">
                                    {activeOS === "windows"
                                        ? "Add the binary folder to your User PATH to enable global access via any PowerShell or CMD session."
                                        : "Set execute permissions and move to your local bin directory for global CLI access."}
                                </p>
                                <div className="p-6 bg-slate-900 dark:bg-[#0D1117] rounded-xl font-mono text-sm text-emerald-400 relative group overflow-hidden border border-slate-800">
                                    <div className="flex justify-between items-center mb-4">
                                        <span className="text-slate-500 uppercase text-[11px] font-bold tracking-[0.2em]">
                                            {activeOS === 'windows' ? 'Session Persistent Command' : 'Terminal Command'}
                                        </span>
                                        <button
                                            onClick={() => copyToClipboard(installCommands[activeOS].step2)}
                                            aria-label="Copy command"
                                            className="p-2 text-slate-500 hover:text-white transition-colors"
                                        >
                                            <Copy size={16} />
                                        </button>
                                    </div>
                                    <div className="flex items-start gap-4">
                                        <ChevronRight size={18} className="text-slate-600 shrink-0 mt-0.5" />
                                        <span className="break-all">{installCommands[activeOS].step2}</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeStep === 2 && (
                            <div className="space-y-6">
                                <p className="text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg">
                                    Verify your installation by running the welcome command. This will initialize your local config and display the version info.
                                </p>
                                <div className="flex items-center justify-between p-6 bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/20 rounded-2xl group transition-all hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30">
                                    <div className="flex items-center gap-4">
                                        <div className="p-2 rounded-lg bg-emerald-500 text-white shadow-lg shadow-emerald-500/20">
                                            <CheckCircle2 size={20} />
                                        </div>
                                        <code className="text-emerald-900 dark:text-emerald-400 font-bold text-lg font-mono tracking-tight">$ yamlr welcome</code>
                                    </div>
                                    <button
                                        onClick={() => copyToClipboard("yamlr welcome")}
                                        className="p-3 bg-white dark:bg-emerald-950 hover:bg-emerald-500 hover:text-white rounded-xl transition-all text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 shadow-sm font-bold text-xs uppercase tracking-widest"
                                    >
                                        {copied ? "Copied!" : "Copy"}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="mt-10 flex justify-between items-center pt-8 border-t border-slate-100 dark:border-slate-800">
                        <button
                            disabled={activeStep === 0}
                            onClick={() => setActiveStep(activeStep - 1)}
                            className={`flex items-center gap-2 group text-xs font-bold uppercase tracking-widest transition-all ${activeStep === 0 ? "text-slate-200 dark:text-slate-800" : "text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:hover:text-slate-300"}`}
                        >
                            <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                            Back
                        </button>
                        <div className="flex items-center gap-2">
                            {activeStep < 2 ? (
                                <button
                                    onClick={() => setActiveStep(activeStep + 1)}
                                    className="bg-slate-900 dark:bg-slate-800 text-white px-8 py-4 rounded-2xl font-bold uppercase text-[11px] tracking-widest hover:bg-[#4285F4] dark:hover:bg-[#4285F4] transition-all flex items-center gap-3 shadow-lg shadow-slate-900/10 active:scale-95"
                                >
                                    Continue to Step {activeStep + 2}
                                    <ChevronRight size={16} />
                                </button>
                            ) : (
                                <Link
                                    href="/sandbox"
                                    className="bg-emerald-600 dark:bg-emerald-500/20 text-white dark:text-emerald-400 border border-transparent dark:border-emerald-500/30 px-8 py-4 rounded-2xl font-bold uppercase text-[11px] tracking-widest hover:bg-emerald-700 dark:hover:bg-emerald-500/40 transition-all shadow-lg shadow-emerald-600/10 active:scale-95"
                                >
                                    Explore Sandbox
                                </Link>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Visual reassurance */}
            <div className="mt-6 flex flex-wrap items-center justify-center gap-8 px-6 text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
                <div className="flex items-center gap-2"><ShieldIcon size={14} className="text-emerald-500" /> Signed Binary</div>
                <div className="flex items-center gap-2"><ZapIcon size={14} className="text-[#4285F4] shadow-sm" /> Native Acceleration</div>
            </div>
        </div>
    );
}
