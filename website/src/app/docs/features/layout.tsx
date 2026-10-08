import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Features — Yamlr',
    description: 'Complete list of detection rules, healing capabilities, and security features in the Yamlr Kubernetes engine.',
    alternates: { canonical: 'https://yamlr.dev/docs/features/' },
    openGraph: {
        title: 'Features — Yamlr',
        description: 'Complete list of detection rules, healing capabilities, and security features in the Yamlr Kubernetes engine.',
        url: 'https://yamlr.dev/docs/features/',
    },
};

export default function FeaturesLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
