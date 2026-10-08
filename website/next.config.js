/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'export',
    reactStrictMode: true,
    trailingSlash: true,
    images: {
        domains: [],
        unoptimized: true,
    },
};

module.exports = nextConfig;
