"use client";

import Link from "next/link";
import { Zap, X } from "lucide-react";
import { useState } from "react";

export default function AnnouncementBar({ onDismiss }: { onDismiss?: () => void }) {
    const [dismissed, setDismissed] = useState(false);

    if (dismissed) return null;

    const handleDismiss = () => {
        setDismissed(true);
        onDismiss?.();
    };

    return (
        <div className="w-full bg-[#4285F4] text-white relative z-[99]">
            <div className="max-w-7xl mx-auto px-6 py-2 flex items-center justify-center gap-3 text-xs font-semibold pr-10 sm:pr-6">
                <Zap size={12} className="shrink-0 opacity-90" />
                <span className="truncate sm:overflow-visible font-medium">
                    <span className="hidden sm:inline">v1.0.0 Architecture Preview &mdash; Sub-10ms AST engine, 38 commands, 42 forensic detectors, zero data egress</span>
                    <span className="sm:hidden">v1.0.0 &mdash; Sub-10ms AST engine &amp; auto-healer</span>
                </span>
                <Link
                    href="/docs/getting-started"
                    className="underline underline-offset-2 opacity-95 hover:opacity-100 transition-opacity shrink-0 hidden sm:inline font-bold ml-1"
                >
                    Get started &rarr;
                </Link>
                <button
                    onClick={handleDismiss}
                    aria-label="Dismiss announcement"
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-2 min-w-[32px] min-h-[32px] flex items-center justify-center opacity-70 hover:opacity-100 transition-opacity"
                >
                    <X size={14} />
                </button>
            </div>
        </div>
    );
}
