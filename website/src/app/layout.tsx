import type { Metadata, Viewport } from "next";
import { Inter, Outfit, Roboto_Mono } from "next/font/google";
import { ThemeManager } from "@/components/ThemeManager";
import "./globals.css";

export const dynamic = 'force-static';

const outfit = Outfit({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700", "800", "900"],
    variable: "--font-outfit",
    display: 'swap',
});

const inter = Inter({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700"],
    variable: "--font-inter",
    display: 'swap',
});

const robotoMono = Roboto_Mono({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700"],
    variable: "--font-mono",
    display: 'swap',
});

export const viewport: Viewport = {
    themeColor: "#ffffff",
    width: "device-width",
    initialScale: 1,
};

export const metadata: Metadata = {
    metadataBase: new URL("https://yamlr.dev"),
    alternates: {
        canonical: "/",
    },
    title: "yamlr. | The Local-First Auto-Healing Engine for Kubernetes",
    description: "Audit and auto-heal Kubernetes manifests and Helm charts before they reach the cluster. Local-first verification, native Model Context Protocol (MCP) support, and 100% comment preservation.",
    authors: [{ name: "yamlr. Team" }],
    keywords: [
        "Kubernetes CLI",
        "AI Coding Guardrail",
        "AI Agent MCP Server",
        "Local Kubernetes MCP Server",
        "Helm Chart Auto-Fix",
        "YAML Auto-Healing",
        "K8s Manifest Verification",
        "Platform Engineering",
        "SRE Tools",
        "Pre-Commit Kubernetes Hook",
        "Comment Preserving YAML"
    ],
    icons: {
        icon: [
            { url: "/favicon.svg", type: "image/svg+xml" },
            { url: "/favicon.png", type: "image/png" },
        ],
        apple: "/favicon.png",
    },
    openGraph: {
        title: "yamlr. | The Local-First Auto-Healing Engine for Kubernetes",
        description: "Audit and auto-heal Kubernetes manifests before they reach the cluster. Model Context Protocol (MCP) support and native Rust engine.",
        url: "https://yamlr.dev",
        siteName: "yamlr.",
        locale: "en_US",
        type: "website",
        images: [
            {
                url: "/og-image.png",
                width: 1200,
                height: 630,
                alt: "yamlr. — The Local-First Auto-Healing Engine for Kubernetes",
            },
        ],
    },
    twitter: {
        card: "summary_large_image",
        title: "yamlr. | The Local-First Auto-Healing Engine for Kubernetes",
        description: "Audit and auto-heal Kubernetes manifests before they reach the cluster. Model Context Protocol (MCP) support and native Rust engine.",
        images: ["/og-image.png"],
    },
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="scroll-smooth antialiased" suppressHydrationWarning>
            <head>
                <script
                    type="application/ld+json"
                    dangerouslySetInnerHTML={{
                        __html: JSON.stringify({
                            "@context": "https://schema.org",
                            "@type": "SoftwareApplication",
                            "name": "yamlr.",
                            "applicationCategory": "DeveloperApplication",
                            "operatingSystem": "Linux, macOS, Windows",
                            "description": "Auto-healing engine for Kubernetes manifests with 100% comment preservation.",
                            "url": "https://yamlr.dev",
                            "offers": {
                                "@type": "Offer",
                                "price": "0",
                                "priceCurrency": "USD"
                            },
                            "publisher": {
                                "@type": "Organization",
                                "name": "Timonel Labs",
                                "url": "https://yamlr.dev"
                            }
                        })
                    }}
                />
            </head>
            <body className={`${outfit.variable} ${inter.variable} ${robotoMono.variable} font-sans bg-background text-foreground min-h-screen selection:bg-[#4285F4]/10 selection:text-[#4285F4] overflow-x-hidden`}>
                <ThemeManager>
                    <div className="flex flex-col min-h-screen">
                        {children}
                    </div>
                </ThemeManager>
            </body>
        </html>
    );
}
