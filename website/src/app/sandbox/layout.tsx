import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Interactive Sandbox | yamlr. Local-First Kubernetes Healing',
    description: 'Experiment with Kubernetes manifest healing. Explore 5 real-world production failure scenarios and observe deterministic, comment-preserving state restoration.',
    alternates: { canonical: 'https://yamlr.dev/sandbox/' },
    openGraph: {
        title: 'Interactive Sandbox | yamlr. Local-First Kubernetes Healing',
        description: 'Experiment with Kubernetes manifest healing. Explore 5 real-world production failure scenarios and observe deterministic, comment-preserving state restoration.',
        url: 'https://yamlr.dev/sandbox/',
    },
};

export default function PreviewLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
