"use client";

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { Check, Copy, Info, Lightbulb, AlertTriangle, AlertOctagon, Sparkles } from "lucide-react";

export default function MarkdownRender({ content }: { content: string }) {
    // Strip all background colors from the VS Code Dark+ theme
    // to prevent grey boxes behind individual tokens/lines.
    const customTheme = { ...vscDarkPlus } as Record<string, React.CSSProperties>;
    Object.keys(customTheme).forEach(key => {
        if (customTheme[key] && customTheme[key].background) {
            customTheme[key] = { ...customTheme[key], background: 'transparent' };
        }
    });

    const getNodeText = (node: any): string => {
        if (!node) return '';
        if (typeof node === 'string' || typeof node === 'number') return String(node);
        if (Array.isArray(node)) return node.map(getNodeText).join('');
        if (node.props?.children) return getNodeText(node.props.children);
        return '';
    };

    const slugify = (node: any): string => {
        const text = getNodeText(node);
        return text
            .toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/[\s_-]+/g, '-')
            .replace(/^-+|-+$/g, '');
    };

    return (
        <div className="prose prose-docs max-w-none prose-code:before:content-none prose-code:after:content-none prose-headings:font-outfit prose-headings:tracking-tight prose-h1:text-3xl sm:prose-h1:text-4xl prose-h1:font-extrabold prose-h1:mt-0 prose-h1:mb-6 prose-h2:text-xl sm:prose-h2:text-2xl prose-h2:font-bold prose-h2:mt-10 prose-h2:mb-3 prose-h3:text-lg sm:prose-h3:text-xl prose-h3:font-bold prose-h3:mt-6 prose-h3:mb-2 text-slate-700 dark:text-slate-300">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    h2: ({ children }) => {
                        const id = slugify(children);
                        return <h2 id={id}>{children}</h2>;
                    },
                    h3: ({ children }) => {
                        const id = slugify(children);
                        return <h3 id={id}>{children}</h3>;
                    },
                    table: ({ children }) => (
                        <div className="my-6 w-full overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161B22]/40 shadow-xs custom-scrollbar">
                            <table className="w-full text-left text-sm divide-y divide-slate-200 dark:divide-slate-800 min-w-[520px]">
                                {children}
                            </table>
                        </div>
                    ),
                    code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '');
                        if (!inline && match) {
                            return (
                                <CodeBlock language={match[1]} codeText={String(children).replace(/\n$/, '')}>
                                    <SyntaxHighlighter
                                        {...props}
                                        style={customTheme}
                                        language={match[1]}
                                        PreTag="div"
                                        customStyle={{ margin: 0, padding: '1.25rem 1.5rem', background: 'transparent' }}
                                        codeTagProps={{ className: 'font-mono text-[13px] leading-relaxed' }}
                                    >
                                        {String(children).replace(/\n$/, '')}
                                    </SyntaxHighlighter>
                                </CodeBlock>
                            );
                        }
                        return (
                            <code 
                                className={`bg-slate-100 dark:bg-slate-800/80 text-slate-800 dark:text-slate-200 border border-slate-200/80 dark:border-slate-700/60 px-1.5 py-0.5 rounded text-[0.875em] font-mono font-medium ${className || ''}`} 
                                {...props}
                            >
                                {children}
                            </code>
                        );
                    },
                    blockquote: ({ children }) => {
                        const childrenArray = React.Children.toArray(children);
                        const firstChild = childrenArray[0] as any;

                        const getFirstText = (node: any): string => {
                            if (!node) return "";
                            if (typeof node === 'string') return node;
                            if (node.props?.children) {
                                if (Array.isArray(node.props.children)) return getFirstText(node.props.children[0]);
                                return getFirstText(node.props.children);
                            }
                            return "";
                        };

                        const text = getFirstText(firstChild);
                        const alertMatch = text.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i);

                        if (alertMatch) {
                            const type = alertMatch[1].toLowerCase();
                            const stripMarker = (node: React.ReactNode): React.ReactNode => {
                                if (!node) return node;
                                if (typeof node === 'string') {
                                    return node.replace(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*/i, '');
                                }
                                if (Array.isArray(node)) {
                                    return node.map((item, idx) => idx === 0 ? stripMarker(item) : item);
                                }
                                if (React.isValidElement(node) && (node as any).props?.children) {
                                    return React.cloneElement(node as React.ReactElement<any>, {
                                        children: stripMarker((node as any).props.children)
                                    });
                                }
                                return node;
                            };

                            return <AlertBlock type={type}>{stripMarker(children)}</AlertBlock>;
                        }

                        return (
                            <blockquote className="border-l-4 border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 py-2.5 px-6 rounded-r-xl italic text-slate-700 dark:text-slate-300 my-6">
                                {children}
                            </blockquote>
                        );
                    }
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}

function AlertBlock({ type, children }: { type: string, children: React.ReactNode }) {
    const config: Record<string, { icon: React.ReactNode, color: string, border: string, bg: string }> = {
        note: { 
            icon: <Info size={18} className="text-[#4285F4] shrink-0 mt-0.5" />, 
            color: "text-[#4285F4]", 
            border: "border-[#4285F4]", 
            bg: "bg-blue-50/70 dark:bg-blue-950/20" 
        },
        tip: { 
            icon: <Lightbulb size={18} className="text-emerald-500 shrink-0 mt-0.5" />, 
            color: "text-emerald-600 dark:text-emerald-400", 
            border: "border-emerald-500", 
            bg: "bg-emerald-50/70 dark:bg-emerald-950/20" 
        },
        important: { 
            icon: <Sparkles size={18} className="text-indigo-500 shrink-0 mt-0.5" />, 
            color: "text-indigo-600 dark:text-indigo-400", 
            border: "border-indigo-500", 
            bg: "bg-indigo-50/70 dark:bg-indigo-950/20" 
        },
        warning: { 
            icon: <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />, 
            color: "text-amber-600 dark:text-amber-400", 
            border: "border-amber-500", 
            bg: "bg-amber-50/70 dark:bg-amber-950/20" 
        },
        caution: { 
            icon: <AlertOctagon size={18} className="text-rose-500 shrink-0 mt-0.5" />, 
            color: "text-rose-600 dark:text-rose-400", 
            border: "border-rose-500", 
            bg: "bg-rose-50/70 dark:bg-rose-950/20" 
        },
    };

    const style = config[type] || config.note;

    return (
        <div className={`my-6 p-5 sm:p-6 rounded-2xl border-l-4 ${style.border} ${style.bg} flex gap-4 items-start shadow-xs`}>
            {style.icon}
            <div className="flex-1 min-w-0">
                <span className={`block text-xs font-bold uppercase tracking-wider mb-1.5 ${style.color}`}>
                    {type}
                </span>
                <div className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed [&>p]:m-0">
                    {children}
                </div>
            </div>
        </div>
    );
}

function CodeBlock({ language, codeText, children }: { language: string, codeText: string, children: React.ReactNode }) {
    const [copied, setCopied] = useState(false);

    const copy = () => {
        navigator.clipboard.writeText(codeText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="not-prose my-6 rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-[#0F141C] shadow-md">
            {/* Header bar */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 dark:bg-[#161B22] border-b border-slate-800 text-xs text-slate-400 font-mono">
                <span className="font-semibold tracking-wide uppercase text-[11px] text-slate-300 dark:text-slate-400">{language || 'text'}</span>
                <button
                    onClick={copy}
                    aria-label="Copy code snippet"
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors text-[11px] font-medium"
                >
                    {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
            </div>
            <div className="overflow-x-auto text-[13px] leading-relaxed custom-scrollbar">
                {children}
            </div>
        </div>
    );
}
