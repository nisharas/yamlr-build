import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Pro & Enterprise — Yamlr',
    description: 'Fleet-wide governance, autonomous CI/CD bot PRs, and cryptographic manifest signing for teams shipping Kubernetes daily.',
    alternates: { canonical: 'https://yamlr.dev/pro/' },
    openGraph: {
        title: 'Pro & Enterprise — Yamlr',
        description: 'Fleet-wide governance, autonomous CI/CD bot PRs, and cryptographic manifest signing for teams shipping Kubernetes daily.',
        url: 'https://yamlr.dev/pro/'
    },
};

export default function ProLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
