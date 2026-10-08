import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Helm & Kustomize Healing — Yamlr',
    description: 'In-memory Helm chart rendering and Kustomize overlay verification with comment-preserving auto-healing.',
    alternates: { canonical: 'https://yamlr.dev/helm/' },
    openGraph: {
        title: 'Helm & Kustomize Healing — Yamlr',
        description: 'In-memory Helm chart rendering and Kustomize overlay verification with comment-preserving auto-healing.',
        url: 'https://yamlr.dev/helm/'
    },
};

export default function HelmLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
