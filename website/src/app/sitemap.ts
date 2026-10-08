import type { MetadataRoute } from "next";

export const dynamic = "force-static";

/**
 * Generates sitemap.xml for search engine indexing.
 */
export default function sitemap(): MetadataRoute.Sitemap {
    const baseUrl = "https://yamlr.dev";

    const docPages = [
        "getting-started",
        "installation",
        "core-concepts",
        "configuration",
        "security-architecture",
        "ci-cd-integration",
        "healing-engine",
        "compliance-and-dna",
        // CLI Commands
        "yamlr-scan", "yamlr-check", "yamlr-audit", "yamlr-doctor", "yamlr-diagnose",
        "yamlr-heal", "yamlr-restore", "yamlr-rollback", "yamlr-migrate", "yamlr-upgrade", "yamlr-secure",
        "yamlr-stats", "yamlr-roi", "yamlr-pulse", "yamlr-graph", "yamlr-drift",
        "yamlr-dna", "yamlr-evidence", "yamlr-baseline", "yamlr-idp-export", "yamlr-mcp", "yamlr-lsp",
        "yamlr-welcome", "yamlr-manual", "yamlr-explain", "yamlr-demo", "yamlr-version", "yamlr-status",
        "yamlr-init", "yamlr-catalog", "yamlr-completion", "yamlr-auth", "yamlr-features"
    ];

    const sitemapEntries: MetadataRoute.Sitemap = [
        {
            url: baseUrl,
            lastModified: new Date(),
            changeFrequency: "weekly",
            priority: 1,
        },
        {
            url: `${baseUrl}/docs`,
            lastModified: new Date(),
            changeFrequency: "weekly",
            priority: 0.9,
        },
        {
            url: `${baseUrl}/sandbox`,
            lastModified: new Date(),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        ...docPages.map((slug) => ({
            url: `${baseUrl}/docs/${slug}`,
            lastModified: new Date(),
            changeFrequency: "monthly" as const,
            priority: slug.startsWith("yamlr-") ? 0.6 : 0.7,
        })),
    ];

    return sitemapEntries;
}
