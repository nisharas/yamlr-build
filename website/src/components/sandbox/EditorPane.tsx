"use client";

import { useRef, RefObject } from "react";
import { Upload, Copy, Check, Wand2, FileCode } from "lucide-react";
import { motion } from "framer-motion";

interface EditorPaneProps {
    type: "ORIGINAL" | "HEALED";
    fileName: string;
    content: string;
    status: "IDLE" | "ANALYZING" | "VERIFIED";
    isCustom: boolean;
    modifierKey: string;
    targetK8sVersion: string;
    healedLinesSet: Set<number>;
    deletedLinesSet: Set<number>;
    scrollRef: RefObject<HTMLDivElement | null>;
    onScroll: () => void;
    // Callbacks for custom editing on ORIGINAL pane
    customYaml?: string;
    onCustomYamlChange?: (val: string) => void;
    onLoadSample?: () => void;
    onFileInput?: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onDropFile?: (text: string, name: string) => void;
    onRunAnalysis?: () => void;
    // Copy states
    copied: boolean;
    onCopy: () => void;
}

export default function EditorPane({
    type,
    fileName,
    content,
    status,
    isCustom,
    modifierKey,
    targetK8sVersion,
    healedLinesSet,
    deletedLinesSet,
    scrollRef,
    onScroll,
    customYaml,
    onCustomYamlChange,
    onLoadSample,
    onFileInput,
    onDropFile,
    onRunAnalysis,
    copied,
    onCopy
}: EditorPaneProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const lineGutterRef = useRef<HTMLDivElement>(null);

    const isOriginal = type === "ORIGINAL";
    const isRightWaiting = !isOriginal && status === "IDLE";
    const isRightLoading = !isOriginal && status === "ANALYZING";

    const handleTextareaScroll = () => {
        if (textareaRef.current && lineGutterRef.current) {
            lineGutterRef.current.scrollTop = textareaRef.current.scrollTop;
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0] && onDropFile) {
            const file = e.dataTransfer.files[0];
            const reader = new FileReader();
            reader.onload = (event) => {
                const text = event.target?.result as string;
                if (text) onDropFile(text, file.name);
            };
            reader.readAsText(file);
        }
    };

    const renderCodeLines = (code: string) => {
        const lines = code.split("\n");
        return lines.map((line, idx) => {
            const lineNum = idx + 1;
            let bgColor = "transparent";
            let textColor = "text-slate-200";
            let prefix = "  ";

            if (status === "VERIFIED") {
                if (isOriginal && deletedLinesSet.has(lineNum)) {
                    bgColor = "bg-rose-500/15";
                    textColor = "text-rose-300";
                    prefix = "- ";
                } else if (!isOriginal && healedLinesSet.has(lineNum)) {
                    bgColor = "bg-emerald-500/20";
                    textColor = "text-emerald-300 font-semibold";
                    prefix = "+ ";
                }
            }

            return (
                <div
                    key={idx}
                    className={`flex px-4 py-0.5 border-l-2 border-transparent transition-all duration-150 ${bgColor}`}
                >
                    <span className="w-9 text-right pr-4 select-none text-slate-500 text-xs flex-shrink-0 font-mono">
                        {lineNum}
                    </span>
                    <span className={`w-4 select-none ${textColor} text-xs font-bold font-mono`}>
                        {prefix}
                    </span>
                    <span className={`whitespace-pre font-mono text-xs sm:text-sm ${textColor}`}>
                        {line}
                    </span>
                </div>
            );
        });
    };

    return (
        <div
            onDragOver={isOriginal && isCustom ? (e) => e.preventDefault() : undefined}
            onDrop={isOriginal && isCustom ? handleDrop : undefined}
            className={`flex flex-col rounded-2xl border bg-[#161B22] shadow-xl overflow-hidden h-[540px] relative transition-all ${
                isOriginal
                    ? "border-slate-800 border-t-2 border-t-[#4285F4]"
                    : "border-slate-800 border-t-2 border-t-[#10B981]"
            }`}
        >
            {/* Hidden file input for custom manifest uploads */}
            {isOriginal && isCustom && (
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={onFileInput}
                    accept=".yaml,.yml"
                    className="hidden"
                />
            )}

            {/* Pane Header */}
            <div className="h-12 flex items-center justify-between px-4 bg-[#11161d] border-b border-slate-800/90">
                <div className="flex items-center gap-2.5">
                    <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                            isOriginal
                                ? "bg-rose-500/10 border border-rose-500/20 text-rose-400"
                                : status === "VERIFIED"
                                ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                                : "bg-slate-800 border border-slate-700 text-slate-400"
                        }`}
                    >
                        {isOriginal ? "Original" : "Healed"}
                    </span>
                    <span className="text-xs font-mono text-slate-300 font-bold">
                        {fileName}
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    {isOriginal && isCustom && (
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-md text-xs font-medium transition-colors border border-slate-700"
                            title="Upload local .yaml manifest"
                        >
                            <Upload size={12} className="text-[#4285F4]" />
                            Upload
                        </button>
                    )}

                    {(isOriginal || status === "VERIFIED") && (
                        <button
                            onClick={onCopy}
                            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors border ${
                                !isOriginal && status === "VERIFIED"
                                    ? "bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border-emerald-500/30"
                                    : "bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border-slate-700"
                            }`}
                            title={isOriginal ? "Copy original YAML" : "Copy healed YAML"}
                        >
                            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                            {copied ? "Copied" : isOriginal ? "Copy" : "Copy Healed"}
                        </button>
                    )}
                </div>
            </div>

            {/* Pane Content */}
            <div
                ref={scrollRef}
                onScroll={onScroll}
                className="flex-1 overflow-auto font-mono text-xs sm:text-sm custom-scrollbar"
            >
                {isOriginal ? (
                    isCustom ? (
                        !customYaml || customYaml.trim() === "" ? (
                            /* Clean Empty Canvas State for Custom Tab */
                            <div className="h-full flex flex-col items-center justify-center text-center p-8">
                                <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-3 text-[#4285F4]">
                                    <FileCode size={24} />
                                </div>
                                <h4 className="text-white font-bold text-sm mb-1 font-outfit">
                                    Empty Manifest Canvas
                                </h4>
                                <p className="text-slate-400 text-xs max-w-[320px] leading-relaxed mb-5 font-sans">
                                    Paste your Kubernetes manifest directly, drag &amp; drop a <code className="text-slate-300 font-mono">.yaml</code> file, or populate with our sample.
                                </p>
                                <div className="flex items-center gap-2.5 font-sans">
                                    {onLoadSample && (
                                        <button
                                            onClick={onLoadSample}
                                            className="px-4 py-2 rounded-xl bg-[#4285F4] hover:bg-[#3367D6] text-white text-xs font-bold transition-all shadow-sm"
                                        >
                                            Load Sample Manifest
                                        </button>
                                    )}
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-all border border-slate-700"
                                    >
                                        Upload File
                                    </button>
                                </div>
                            </div>
                        ) : (
                            /* Active Custom Editor */
                            <div className="flex min-h-full">
                                <div
                                    ref={lineGutterRef}
                                    className="w-10 py-3 pr-3 text-right select-none text-slate-500 font-mono text-xs border-r border-slate-800/80 flex-shrink-0 bg-[#13171f]"
                                >
                                    {customYaml.split("\n").map((_, idx) => (
                                        <div key={idx} className="leading-6">
                                            {idx + 1}
                                        </div>
                                    ))}
                                </div>
                                <textarea
                                    ref={textareaRef}
                                    onScroll={handleTextareaScroll}
                                    value={customYaml}
                                    onChange={(e) => onCustomYamlChange && onCustomYamlChange(e.target.value)}
                                    className="flex-1 min-w-0 bg-transparent text-slate-200 font-mono text-xs sm:text-sm px-4 py-3 outline-none resize-none leading-6 whitespace-pre overflow-x-auto"
                                    placeholder="Paste or drop Kubernetes YAML here..."
                                    spellCheck={false}
                                />
                            </div>
                        )
                    ) : (
                        <div className="py-3">{renderCodeLines(content)}</div>
                    )
                ) : isRightWaiting ? (
                    /* Healed Pane Waiting State */
                    <div className="h-full flex flex-col items-center justify-center text-center p-8">
                        <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-4 text-[#4285F4] shadow-md">
                            <Wand2 size={24} />
                        </div>
                        <h4 className="text-white font-bold text-sm mb-2 font-outfit">
                            Ready for Manifest Synthesis
                        </h4>
                        <p className="text-slate-400 text-xs max-w-[280px] leading-relaxed mb-6 font-sans">
                            Click <span className="text-[#4285F4] font-semibold">Heal Manifest</span> or press{" "}
                            <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px] text-slate-300">
                                {modifierKey}+Enter
                            </kbd>{" "}
                            to execute forensic repair and inspect diffs.
                        </p>
                        {onRunAnalysis && (
                            <button
                                onClick={onRunAnalysis}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#4285F4] hover:bg-[#3367D6] text-white text-xs font-bold transition-all shadow-md active:scale-95 font-sans"
                            >
                                Heal Manifest
                            </button>
                        )}
                    </div>
                ) : isRightLoading ? (
                    /* Healed Pane Analyzing State */
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
                            className="w-12 h-12 border-3 border-[#4285F4]/20 border-t-[#4285F4] rounded-full"
                        />
                        <p className="text-xs font-bold text-white uppercase tracking-wider">
                            Evaluating AST Rules for K8s v{targetK8sVersion}...
                        </p>
                    </div>
                ) : (
                    /* Healed Content Rendered */
                    <div className="py-3">{renderCodeLines(content)}</div>
                )}
            </div>
        </div>
    );
}
