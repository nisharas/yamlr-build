"use client";

import { Wand2, CheckCircle2 } from "lucide-react";
import { Scenario } from "@/data/scenarios";

interface ScenarioTabsProps {
    scenarios: Scenario[];
    activeId: string;
    onSelectScenario: (id: string) => void;
    targetK8sVersion: string;
    isCustom: boolean;
    activeScenario: Scenario;
}

export default function ScenarioTabs({
    scenarios,
    activeId,
    onSelectScenario,
    targetK8sVersion,
    isCustom,
    activeScenario
}: ScenarioTabsProps) {
    return (
        <div className="flex flex-col mb-5">
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#4285F4] font-outfit">
                    Production Failure Modes &amp; Live Studio
                </span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:inline-flex items-center gap-1">
                    Select a curated scenario or live-edit custom YAML
                </span>
            </div>

            {/* Scrollable Tab Strip */}
            <div className="flex items-center gap-1.5 p-1.5 bg-slate-100 dark:bg-slate-900/70 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-x-auto custom-scrollbar">
                {/* Custom Manifest Tab */}
                <button
                    onClick={() => onSelectScenario("custom")}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap active:scale-[0.98] ${
                        isCustom
                            ? "bg-[#4285F4] text-white shadow-sm"
                            : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-white/60 dark:hover:bg-slate-800/60"
                    }`}
                >
                    <Wand2 size={14} />
                    Custom Manifest (Live Edit)
                </button>

                {/* Curated Scenarios */}
                {scenarios.map((s) => (
                    <button
                        key={s.id}
                        onClick={() => onSelectScenario(s.id)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap active:scale-[0.98] ${
                            activeId === s.id
                                ? "bg-[#4285F4] text-white shadow-sm"
                                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-white/60 dark:hover:bg-slate-800/60"
                        }`}
                    >
                        {s.icon}
                        {s.label}
                    </button>
                ))}
            </div>

            {/* Active Mode Contextual Banner */}
            <div className="mt-3 px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#161B22]/80 border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600 dark:text-slate-300">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-[#4285F4] font-outfit uppercase tracking-wider text-[11px]">
                        Active Mode:
                    </span>
                    <span>
                        {isCustom
                            ? "Edit freely, paste YAML, or upload files. Typo repair, selector generation & PSS hardening apply live."
                            : activeScenario.description}
                    </span>
                </div>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium inline-flex items-center gap-1.5 flex-shrink-0">
                    <CheckCircle2 size={13} />
                    Target Kubernetes v{targetK8sVersion} OpenAPI Schema
                </span>
            </div>
        </div>
    );
}
