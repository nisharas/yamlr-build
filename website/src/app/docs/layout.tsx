import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Documentation — Yamlr',
    description: 'CLI reference, quickstart guides, and configuration specs for the Yamlr Kubernetes healing engine.',
    alternates: { canonical: 'https://yamlr.dev/docs/' },
    openGraph: {
        title: 'Documentation — Yamlr',
        description: 'CLI reference, quickstart guides, and configuration specs for the Yamlr Kubernetes healing engine.',
        url: 'https://yamlr.dev/docs/',
    },
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
