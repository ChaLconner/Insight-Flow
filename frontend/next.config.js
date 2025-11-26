/** @type {import('next').NextConfig} */
const nextConfig = {
    // Production optimizations
    reactStrictMode: true,

    // Removed turbopack configuration to use default settings
    // turbopack: {
    //     root: './', // Explicitly set relative root to current directory
    // },

    // Image optimization - updated for Next.js 16
    images: {
        remotePatterns: [
            { protocol: 'http', hostname: 'localhost', port: '8000', pathname: '/**' },
            { protocol: 'https', hostname: 'your-api-domain.com', pathname: '/**' }
        ],
        formats: ['image/webp', 'image/avif'],
        deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
        imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    },

    // Experimental features
    experimental: {
        optimizePackageImports: [
            'lucide-react',
            'recharts'
        ],
    },

    // Performance optimizations
    compiler: {
        removeConsole: process.env.NODE_ENV === 'production',
    },

    // Environment variables
    env: {
        CUSTOM_KEY: process.env.CUSTOM_KEY,
    },

    // Headers for security and performance
    async headers() {
        return [
            {
                source: '/(.*)',
                headers: [
                    {
                        key: 'X-Frame-Options',
                        value: 'DENY',
                    },
                    {
                        key: 'X-Content-Type-Options',
                        value: 'nosniff',
                    },
                    {
                        key: 'Referrer-Policy',
                        value: 'origin-when-cross-origin',
                    },
                ],
            },
            {
                source: '/_next/static/(.*)',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
            {
                source: '/_next/image(.*)',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
            // Note: CORS for backend API is handled by the backend server (FastAPI).
            // Avoid adding wildcard CORS headers here which can conflict with
            // `Access-Control-Allow-Credentials` when credentials are used.
        ];
    },

    // Redirect rules
    async redirects() {
        return [
            {
                source: '/login',
                destination: '/auth/login',
                permanent: true,
            },
        ];
    },

    // Removed webpack config for Next.js 16 with Turbopack
    // Turbopack handles optimizations automatically
};

module.exports = nextConfig;
