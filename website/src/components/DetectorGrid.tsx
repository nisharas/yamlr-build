import { ShieldCheck, Network, Cpu, HardDrive, ScrollText, Activity } from "lucide-react";

const CATEGORIES = [
    {
        title: "Networking",
        icon: <Network size={20} className="text-[#4285F4]" />,
        desc: "Catches port mismatches, ghost services, and Ingress routing faults before traffic drops.",
        count: 8,
    },
    {
        title: "Security",
        icon: <ShieldCheck size={20} className="text-emerald-500" />,
        desc: "Prevents privilege escalation, hardcoded secrets, and root container deployments.",
        count: 14,
    },
    {
        title: "Reliability",
        icon: <Activity size={20} className="text-rose-500" />,
        desc: "Enforces liveness/readiness probes, pod disruption budgets, and safe rollout strategies.",
        count: 9,
    },
    {
        title: "Storage",
        icon: <HardDrive size={20} className="text-indigo-500" />,
        desc: "Validates PVC bindings, stops dangerous hostPath mounts, and checks volume permissions.",
        count: 6,
    },
    {
        title: "Governance",
        icon: <ScrollText size={20} className="text-amber-500" />,
        desc: "Catches deprecated APIs (v1.21-v1.37) and enforces organizational label requirements.",
        count: 7,
    },
    {
        title: "Operations",
        icon: <Cpu size={20} className="text-sky-500" />,
        desc: "Identifies HPA scaling loops, orphan ReplicaSets, and conflicting resource limits.",
        count: 4,
    },
];

export default function DetectorGrid() {
    return (
        <section className="py-14 bg-slate-50 dark:bg-slate-900/50 border-y border-slate-200 dark:border-slate-800">
            <div className="max-w-6xl mx-auto px-6 sm:px-8">
                <div className="text-center mb-10 sm:mb-12">
                    <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-widest px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 mb-3 inline-block">
                        Engine Catalog
                    </span>
                    <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white mb-4 tracking-tight">
                        Forensic Detectors. <br className="sm:hidden" /> Zero Noise.
                    </h2>
                    <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto">
                        We mapped common Kubernetes outage patterns to deterministic rules. <span className="font-bold font-outfit tracking-normal">yamlr<span className="text-[#059669] dark:text-[#10B981]">.</span></span> scans your manifests against the official K8s OpenAPI schemas to find these silently broken configurations.
                    </p>
                </div>

                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {CATEGORIES.map((cat, i) => (
                        <div key={i} className="p-6 rounded-2xl bg-white dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 shadow-xs hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between mb-4">
                                <div className="w-10 h-10 rounded-xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center">
                                    {cat.icon}
                                </div>
                                <span className="text-[11px] font-mono font-bold text-[#4285F4] bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 px-2.5 py-1 rounded-full uppercase tracking-wider">
                                    Schema-Backed
                                </span>
                            </div>
                            <h3 className="text-lg font-bold font-outfit text-slate-900 dark:text-white mb-2">
                                {cat.title}
                            </h3>
                            <p className="text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed">
                                {cat.desc}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
