import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'AI & MCP Server — Yamlr',
    description: 'Model Context Protocol integration for AI coding agents. In-memory manifest validation and auto-healing.',
    alternates: { canonical: 'https://yamlr.dev/mcp/' },
    openGraph: {
        title: 'AI & MCP Server — Yamlr',
        description: 'Model Context Protocol integration for AI coding agents. In-memory manifest validation and auto-healing.',
        url: 'https://yamlr.dev/mcp/',
    },
};

export default function McpLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
