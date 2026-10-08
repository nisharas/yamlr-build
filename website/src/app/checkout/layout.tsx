import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Checkout — Yamlr',
    description: 'Complete your Yamlr Pro subscription setup.',
    alternates: { canonical: 'https://yamlr.dev/checkout/' },
    openGraph: {
        title: 'Checkout — Yamlr',
        description: 'Complete your Yamlr Pro subscription setup.',
        url: 'https://yamlr.dev/checkout/'
    },
};

export default function CheckoutLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
