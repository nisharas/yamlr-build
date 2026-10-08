"use client";

import { useState } from "react";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { RevealAnimation } from "@/components/Hero";
import { 
    Bot, 
    Copy, 
    Check, 
    Terminal, 
    Shield, 
    Cpu, 
    ArrowRight, 
    Zap, 
    Network, 
    FileSearch, 
    Wrench, 
    Database, 
    CheckCircle2, 
    Code2,
    Lock
} from "lucide-react";
import Link from "next/link";

interface McpTool {
    id: string;
    name: string;
    tagline: string;
    description: string;
    icon: typeof Cpu;
    color: string;
    params: { name: string; type: string; required: boolean; description: string }[];
    sampleRequest: object;
    sampleResponse: object;
}

const MCP_TOOLS: McpTool[] = [
    {
        id: "propose_infrastructure_mutation",
        name: "propose_infrastructure_mutation",
        tagline: "In-Memory Pre-Flight Mutation Guardrail",
        description: "Enables autonomous AI coding agents to dry-run proposed YAML edits in-memory before writing to disk. Returns health score deltas, OpenAPI schema violations, and topology integrity checks.",
        icon: Shield,
        color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
        params: [
            { name: "file_path", type: "string", required: true, description: "Target manifest file path to evaluate against." },
            { name: "proposed_patch", type: "string", required: true, description: "The complete proposed YAML patch string to dry-run." }
        ],
        sampleRequest: {
            method: "tools/call",
            params: {
                name: "propose_infrastructure_mutation",
                arguments: {
                    file_path: "deployments/web-service.yaml",
                    proposed_patch: "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-service\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: web\n        image: nginx:1.25\n        ports:\n        - containerPort: 80\n"
                }
            }
        },
        sampleResponse: {
            status: "success",
            mutation_status: "APPROVED",
            before_score: 82.0,
            after_score: 100.0,
            health_delta: "+18.0",
            schema_violations: [],
            integrity_violations: [],
            message: "Mutation preserves structural integrity and meets Kubernetes schema standards."
        }
    },
    {
        id: "scan_manifests",
        name: "scan_manifests",
        tagline: "Comprehensive Clinical Manifest Audit",
        description: "Performs full-tree clinical audit of manifests at a given directory path. Inspects structural schemas, deprecated API versions, security boundaries, and cross-resource links.",
        icon: FileSearch,
        color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
        params: [
            { name: "path", type: "string", required: false, description: "Directory or file path to audit (defaults to workspace root)." }
        ],
        sampleRequest: {
            method: "tools/call",
            params: {
                name: "scan_manifests",
                arguments: {
                    path: "./manifests"
                }
            }
        },
        sampleResponse: {
            status: "success",
            total_files: 14,
            results: [
                {
                    file: "manifests/ingress.yaml",
                    score: 65.0,
                    violations: [
                        { field: "apiVersion", message: "extensions/v1beta1 is deprecated in K8s 1.22+; migrate to networking.k8s.io/v1" }
                    ]
                }
            ]
        }
    },
    {
        id: "heal_manifests",
        name: "heal_manifests",
        tagline: "Atomic Native Lossless Remediation",
        description: "Automatically applies deterministic, atomic fixes to manifests using Yamlr's native CST engine while guaranteeing 100% comment, docstring, and whitespace preservation.",
        icon: Wrench,
        color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
        params: [
            { name: "path", type: "string", required: false, description: "Manifest directory path to heal." }
        ],
        sampleRequest: {
            method: "tools/call",
            params: {
                name: "heal_manifests",
                arguments: {
                    path: "./manifests"
                }
            }
        },
        sampleResponse: {
            status: "success",
            total_files: 14,
            applied_fixes: 3,
            results: [
                {
                    file: "manifests/ingress.yaml",
                    score: 100.0,
                    violations: []
                }
            ]
        }
    },
    {
        id: "get_resource_dependencies",
        name: "get_resource_dependencies",
        tagline: "Cross-Resource Topology Graph Query",
        description: "Traverses Yamlr's in-memory ResourceGraph to identify all upstream and downstream resources linked to a target manifest (e.g., ConfigMaps and Secrets consumed by a Deployment).",
        icon: Network,
        color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
        params: [
            { name: "path", type: "string", required: true, description: "Path to manifests to construct graph." },
            { name: "kind", type: "string", required: true, description: "Target resource kind (e.g., Deployment, Service)." },
            { name: "name", type: "string", required: true, description: "Target resource metadata name." }
        ],
        sampleRequest: {
            method: "tools/call",
            params: {
                name: "get_resource_dependencies",
                arguments: {
                    path: "./k8s",
                    kind: "Deployment",
                    name: "api-server"
                }
            }
        },
        sampleResponse: {
            status: "success",
            target: "Deployment/api-server",
            dependencies: [
                "ConfigMap api-config",
                "Secret api-credentials",
                "Service api-cluster-ip"
            ]
        }
    },
    {
        id: "get_openapi_schema",
        name: "get_openapi_schema",
        tagline: "Strict Kubernetes OpenAPI Schema Authority",
        description: "Retrieves authoritative schema property definitions and type requirements directly from compiled Kubernetes OpenAPI specifications for any kind and target version.",
        icon: Database,
        color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20",
        params: [
            { name: "kind", type: "string", required: true, description: "Resource kind to look up (e.g., Ingress, CronJob, Deployment)." },
            { name: "k8s_version", type: "string", required: true, description: "Target Kubernetes schema version (e.g., 1.30)." }
        ],
        sampleRequest: {
            method: "tools/call",
            params: {
                name: "get_openapi_schema",
                arguments: {
                    kind: "Ingress",
                    k8s_version: "1.30"
                }
            }
        },
        sampleResponse: {
            status: "success",
            k8s_version: "1.30",
            schema: [
                {
                    api_version: "networking.k8s.io/v1",
                    kind: "Ingress",
                    properties: [
                        { name: "metadata", type: "ObjectMeta", required: true },
                        { name: "spec", type: "IngressSpec", required: true }
                    ]
                }
            ]
        }
    }
];

export default function McpPage() {
    const [copied, setCopied] = useState<string | null>(null);
    const [selectedToolId, setSelectedToolId] = useState<string>(MCP_TOOLS[0].id);
    const [activeTab, setActiveTab] = useState<"standard" | "ide" | "cli">("standard");

    const copyCode = (id: string, text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
    };

    const selectedTool = MCP_TOOLS.find(t => t.id === selectedToolId) || MCP_TOOLS[0];

    const standardConfig = `{
  "mcpServers": {
    "yamlr": {
      "command": "yamlr",
      "args": ["mcp"]
    }
  }
}`;

    const ideConfig = `{
  "mcpServers": {
    "yamlr": {
      "command": "yamlr",
      "args": ["mcp"],
      "disabled": false,
      "autoApprove": [
        "get_openapi_schema",
        "get_resource_dependencies",
        "propose_infrastructure_mutation"
      ]
    }
  }
}`;

    const cliExecution = `# Start the Model Context Protocol stdio server directly:
yamlr mcp

# Test protocol initialization over stdio:
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | yamlr mcp`;

    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-[#4285F4]/10 selection:text-[#4285F4]">
            <Navigation />

            <main className="flex-1 pt-20 sm:pt-24 pb-20">
                <div className="max-w-6xl mx-auto px-6">
                    {/* Header */}
                    <div className="text-center mb-16">
                        <RevealAnimation>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 rounded-full mb-6">
                                <Bot size={14} className="text-[#4285F4]" />
                                <span className="text-xs font-semibold text-[#4285F4] uppercase tracking-wider">
                                    Open Standard • Model Context Protocol (MCP)
                                </span>
                            </div>
                        </RevealAnimation>

                        <RevealAnimation delay={100}>
                            <h1 className="text-4xl sm:text-6xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white mb-6">
                                The Autonomous AI Resolution Plane for{" "}
                                <span className="text-[#4285F4]">Kubernetes Manifests</span>
                            </h1>
                        </RevealAnimation>

                        <RevealAnimation delay={200}>
                            <p className="text-lg text-slate-600 dark:text-slate-400 max-w-3xl mx-auto leading-relaxed">
                                Autonomous AI coding assistants and LLMs frequently generate manifests with outdated APIs, unlinked selectors, or syntax flaws. 
                                Yamlr MCP provides an in-memory resolution plane and schema validation boundary, ensuring all infrastructure mutations are verified against strict OpenAPI schemas before touching disk or version control.
                            </p>
                        </RevealAnimation>
                    </div>

                    {/* Architectural Pillars (4-Card Grid) */}
                    <h2 className="sr-only">Architectural Capabilities</h2>
                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
                        <div className="p-6 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 flex flex-col shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-[#4285F4] mb-4">
                                <Cpu size={22} />
                            </div>
                            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">In-Memory Sandboxing</h3>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                Evaluates proposed YAML patches against official schemas with zero disk I/O, scoring health deltas before mutations land.
                            </p>
                        </div>

                        <div className="p-6 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 flex flex-col shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 mb-4">
                                <Shield size={22} />
                            </div>
                            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">Comment Preservation</h3>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                Zero-copy CST arena sharding guarantees human docstrings, comments, annotations, and spacing remain 100% intact.
                            </p>
                        </div>

                        <div className="p-6 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 flex flex-col shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center text-purple-500 mb-4">
                                <Zap size={22} />
                            </div>
                            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">Sub-10ms Native Latency</h3>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                Compiled native Rust validation executes in single-digit milliseconds, fitting seamlessly into real-time agent tool loops.
                            </p>
                        </div>

                        <div className="p-6 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 flex flex-col shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center text-amber-500 mb-4">
                                <Network size={22} />
                            </div>
                            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">Deterministic Topology</h3>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                Resolves cross-manifest references (Services to Deployments, ConfigMaps to Pods) to prevent broken linkages.
                            </p>
                        </div>
                    </div>

                    {/* Full 5-Tool Suite Interactive Showcase */}
                    <div className="mb-20">
                        <div className="text-center mb-10">
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white mb-3 tracking-tight">
                                The Complete Yamlr MCP Tool Suite
                            </h2>
                            <p className="text-sm text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
                                Five specialized tools exposed over standard JSON-RPC, equipping AI coding agents with real-time verification, schema authority, and safe remediation.
                            </p>
                        </div>

                        {/* Tool Selector Tabs */}
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
                            {MCP_TOOLS.map((tool) => {
                                const Icon = tool.icon;
                                const isSelected = tool.id === selectedToolId;
                                return (
                                    <button
                                        key={tool.id}
                                        onClick={() => setSelectedToolId(tool.id)}
                                        className={`p-4 rounded-2xl border text-left transition-all flex flex-col gap-2 ${
                                            isSelected 
                                                ? "bg-blue-50/80 dark:bg-blue-900/20 border-[#4285F4] shadow-sm shadow-blue-500/10" 
                                                : "bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                                        }`}
                                    >
                                        <div className={`w-8 h-8 rounded-xl flex items-center justify-center border ${tool.color}`}>
                                            <Icon size={16} />
                                        </div>
                                        <div>
                                            <div className="font-mono text-xs font-bold text-slate-900 dark:text-white truncate">
                                                {tool.name}
                                            </div>
                                            <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                                                {tool.tagline}
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>

                        {/* Active Tool Detailed View */}
                        <div className="rounded-3xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-6 sm:p-8">
                            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 mb-6 border-b border-slate-200 dark:border-slate-800">
                                <div>
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${selectedTool.color}`}>
                                            <selectedTool.icon size={18} />
                                        </div>
                                        <h3 className="text-xl font-bold font-mono text-slate-950 dark:text-white">
                                            {selectedTool.name}
                                        </h3>
                                    </div>
                                    <p className="text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
                                        {selectedTool.description}
                                    </p>
                                </div>
                                <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-xs font-semibold text-slate-700 dark:text-slate-300 self-start lg:self-center">
                                    <CheckCircle2 size={13} className="text-emerald-500" />
                                    <span>JSON-RPC 2.0 Stdio</span>
                                </div>
                            </div>

                            {/* Parameters & Payloads */}
                            <div className="grid lg:grid-cols-12 gap-6">
                                {/* Parameters Column */}
                                <div className="lg:col-span-4 space-y-4">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
                                        <Code2 size={14} />
                                        Input Parameters
                                    </h4>
                                    <div className="space-y-2">
                                        {selectedTool.params.map((param) => (
                                            <div 
                                                key={param.name}
                                                className="p-3 rounded-xl bg-white dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80"
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-mono text-xs font-bold text-slate-900 dark:text-white">
                                                        {param.name}
                                                    </span>
                                                    <span className="text-[11px] font-mono text-slate-500 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                                                        {param.type}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-slate-600 dark:text-slate-400">
                                                    {param.description}
                                                </p>
                                                {param.required && (
                                                    <span className="text-[11px] font-semibold text-rose-500 uppercase mt-1 inline-block">
                                                        Required
                                                    </span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Sample Request & Response */}
                                <div className="lg:col-span-8 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
                                            <Terminal size={14} />
                                            Sample Agent Request & Execution Result
                                        </h4>
                                        <button
                                            onClick={() => copyCode(selectedTool.id, JSON.stringify(selectedTool.sampleResponse, null, 2))}
                                            className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white inline-flex items-center gap-1 transition-colors"
                                        >
                                            {copied === selectedTool.id ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                                            <span>{copied === selectedTool.id ? "Copied" : "Copy Response"}</span>
                                        </button>
                                    </div>

                                    <div className="grid sm:grid-cols-2 gap-4">
                                        <div>
                                            <div className="text-[11px] font-mono text-slate-500 mb-1 px-1">Agent Request (Input)</div>
                                            <pre className="font-mono text-xs text-slate-300 p-4 bg-[#090D14] rounded-2xl border border-slate-800 overflow-x-auto max-h-72">
                                                {JSON.stringify(selectedTool.sampleRequest, null, 2)}
                                            </pre>
                                        </div>
                                        <div>
                                            <div className="text-[11px] font-mono text-slate-500 mb-1 px-1">Yamlr Engine Response (Output)</div>
                                            <pre className="font-mono text-xs text-emerald-400 p-4 bg-[#090D14] rounded-2xl border border-slate-800 overflow-x-auto max-h-72">
                                                {JSON.stringify(selectedTool.sampleResponse, null, 2)}
                                            </pre>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Universal Setup Code Blocks */}
                    <div className="mb-20">
                        <div className="text-center mb-8">
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-outfit text-slate-950 dark:text-white mb-3 tracking-tight">
                                Universal Client Configuration
                            </h2>
                            <p className="text-sm text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
                                Standard Model Context Protocol integration compatible with any compliant IDE, coding agent, or orchestration engine.
                            </p>
                        </div>

                        <div className="p-6 sm:p-8 rounded-3xl bg-[#0b0e14] border border-slate-800 text-white">
                            {/* Tabs */}
                            <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
                                <div className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
                                    <button
                                        onClick={() => setActiveTab("standard")}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                            activeTab === "standard" 
                                                ? "bg-[#4285F4] text-white shadow-sm" 
                                                : "text-slate-400 hover:text-white"
                                        }`}
                                    >
                                        Standard MCP Client (mcp.json)
                                    </button>
                                    <button
                                        onClick={() => setActiveTab("ide")}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                            activeTab === "ide" 
                                                ? "bg-[#4285F4] text-white shadow-sm" 
                                                : "text-slate-400 hover:text-white"
                                        }`}
                                    >
                                        IDE & Editor Configuration
                                    </button>
                                    <button
                                        onClick={() => setActiveTab("cli")}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                            activeTab === "cli" 
                                                ? "bg-[#4285F4] text-white shadow-sm" 
                                                : "text-slate-400 hover:text-white"
                                        }`}
                                    >
                                        Direct Stdio Invocation
                                    </button>
                                </div>

                                <button
                                    onClick={() => {
                                        const text = activeTab === "standard" ? standardConfig : activeTab === "ide" ? ideConfig : cliExecution;
                                        copyCode(activeTab, text);
                                    }}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition-all"
                                >
                                    {copied === activeTab ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                                    <span>{copied === activeTab ? "Copied" : "Copy Configuration"}</span>
                                </button>
                            </div>

                            {/* Active Content */}
                            <pre className="font-mono text-sm text-slate-300 overflow-x-auto p-4 bg-black/50 rounded-2xl border border-slate-800/80">
                                {activeTab === "standard" && standardConfig}
                                {activeTab === "ide" && ideConfig}
                                {activeTab === "cli" && cliExecution}
                            </pre>
                        </div>
                    </div>

                    {/* Protocol Compliance Specifications */}
                    <div className="p-8 rounded-3xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 mb-16">
                        <div className="grid md:grid-cols-3 gap-6">
                            <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-[#4285F4] shrink-0">
                                    <Lock size={20} />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Zero-Data Egress</h3>
                                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                        All manifest parsing, CST sharding, and schema validation execute locally in-process with zero network telemetry or cluster connection required.
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 shrink-0">
                                    <CheckCircle2 size={20} />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Deterministic Verification</h3>
                                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                        100% deterministic output. Same manifest + target Kubernetes version always produces identical health scores, violations, and patches.
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-500 shrink-0">
                                    <Database size={20} />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Universal Schema Coverage</h3>
                                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                        Native OpenAPI schema validation spanning Kubernetes v1.21 through v1.37+ (forward-compatible), covering core workloads, custom CRDs, and network policies.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* CTA */}
                    <div className="text-center p-8 sm:p-12 rounded-2xl bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 shadow-sm">
                        <h2 className="text-3xl sm:text-4xl font-extrabold font-outfit text-slate-950 dark:text-white mb-4 tracking-tight">
                            Test Yamlr in Your Browser
                        </h2>
                        <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-md mx-auto">
                            Experiment with Yamlr&apos;s real-time manifest analysis and lossless auto-healing playground with zero setup.
                        </p>
                        <div className="flex flex-wrap items-center justify-center gap-4">
                            <Link
                                href="/sandbox"
                                className="inline-flex items-center gap-2 bg-[#4285F4] hover:bg-[#3367D6] text-white px-8 py-3.5 min-h-[48px] rounded-full font-bold transition-all shadow-md shadow-blue-500/20 active:scale-95 text-sm"
                            >
                                Open Interactive Sandbox
                                <ArrowRight size={16} />
                            </Link>
                            <Link
                                href="/docs/getting-started"
                                className="inline-flex items-center gap-2 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-900 dark:text-white px-8 py-3.5 min-h-[48px] rounded-full font-bold transition-all active:scale-95 text-sm"
                            >
                                Read Documentation
                            </Link>
                        </div>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
