import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Yamlr vs Alternatives — Comparison',
    description: 'Performance and capability comparison between Yamlr and static linters, policy gateways, and multi-IaC scanners.',
    alternates: { canonical: 'https://yamlr.dev/docs/compare/' },
    openGraph: {
        title: 'Yamlr vs Alternatives — Comparison',
        description: 'Performance and capability comparison between Yamlr and static linters, policy gateways, and multi-IaC scanners.',
        url: 'https://yamlr.dev/docs/compare/',
    },
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
