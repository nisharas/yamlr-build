"use client";

import { useState } from "react";
import { Terminal, Github, Code, Check, Copy, Zap } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

const SNIPPETS = {
    "GitHub Actions": {
        icon: <Github size={16} />,
        lang: "yaml",
        file: ".github/workflows/yamlr.yaml",
        code: `- name: yamlr scan
  uses: yamlr/yamlr-action@v1
  with:
    path: './manifests'
    fail-level: error
    output: sarif`
    },
    "Pre-commit": {
        icon: <Terminal size={16} />,
        lang: "yaml",
        file: ".pre-commit-config.yaml",
        code: `- repo: https://github.com/yamlr/yamlr
  rev: v1.0.0-stable
  hooks:
    - id: yamlr-scan
    - id: yamlr-heal
      args: ["--dry-run"]`
    },
    "VS Code": {
        icon: <Code size={16} />,
        lang: "json",
        file: ".vscode/settings.json",
        code: `// Install the yamlr extension from the Marketplace.
// The LSP server activates on all .yaml files automatically.
// Real-time healing diagnostics appear as you type.
{
  "yamlr.enable": true,
  "yamlr.kubeVersion": "v1.31",
  "yamlr.lintOnSave": true
}`
    },
    "GitLab CI": {
        icon: <Terminal size={16} />,
        lang: "yaml",
        file: ".gitlab-ci.yml",
        code: `yamlr-audit:
  image: yamlr/yamlr:latest
  script:
    - yamlr scan ./manifests --output sarif
  artifacts:
    reports:
      sast: yamlr-results.sarif`
    },
};

export default function IntegrationSnippetViewer() {
    const [activeTab, setActiveTab] = useState<keyof typeof SNIPPETS>("GitHub Actions");
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(SNIPPETS[activeTab].code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="w-full">
            {/* Tabs */}
            <div className="flex flex-wrap justify-center gap-2.5 sm:gap-3 mb-8">
                {(Object.keys(SNIPPETS) as Array<keyof typeof SNIPPETS>).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`inline-flex items-center gap-2 px-4 sm:px-5 py-2 sm:py-2.5 min-h-[40px] rounded-full border font-semibold text-xs sm:text-sm tracking-normal transition-all duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4] focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#0D1117] ${
                            activeTab === tab
                                ? "bg-[#4285F4] text-white border-[#4285F4] shadow-lg shadow-blue-500/20"
                                : "bg-white dark:bg-[#161B22] text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800 hover:text-slate-900 dark:hover:text-white hover:border-slate-300 dark:hover:border-slate-700"
                        }`}
                    >
                        {SNIPPETS[tab].icon}
                        <span>{tab}</span>
                    </button>
                ))}
            </div>

            {/* Code Block */}
            <div className="relative rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-[#161B22] shadow-xl">
                <div className="flex items-center justify-between px-5 sm:px-6 py-3 border-b border-white/5 bg-slate-900/50">
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-medium text-slate-300 dark:text-slate-400 tracking-normal">
                            {SNIPPETS[activeTab].file}
                        </span>
                    </div>
                    <button
                        onClick={handleCopy}
                        className="p-2 hover:bg-white/5 rounded-lg transition-colors text-slate-400 hover:text-white focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#4285F4]"
                        title="Copy to clipboard"
                        aria-label="Copy to clipboard"
                    >
                        {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                    </button>
                </div>
                <div className="p-5 sm:p-7 overflow-x-auto CustomScrollbar">
                    <SyntaxHighlighter
                        language={SNIPPETS[activeTab].lang}
                        style={oneDark}
                        customStyle={{
                            background: 'transparent',
                            padding: 0,
                            margin: 0,
                            fontSize: '13px',
                            lineHeight: '1.65',
                        }}
                        codeTagProps={{ style: { fontFamily: 'var(--font-mono)' } }}
                    >
                        {SNIPPETS[activeTab].code}
                    </SyntaxHighlighter>
                </div>
                
                {/* Background Glow */}
                <div className="absolute bottom-0 right-0 w-32 h-32 bg-[#4285F4]/10 blur-[60px] rounded-full translate-x-1/2 translate-y-1/2 pointer-events-none" />
            </div>
        </div>
    );
}
