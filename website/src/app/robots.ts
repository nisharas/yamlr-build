import type { MetadataRoute } from "next";

export const dynamic = "force-static";

/**
 * Configuration for search engine crawlers pointing to the sitemap.
 */
export default function robots(): MetadataRoute.Robots {
    return {
        rules: {
            userAgent: "*",
            allow: "/",
        },
        sitemap: "https://yamlr.dev/sitemap.xml",
    };
}
