/** @type {import('next').NextConfig} */
const nextConfig = {
    // Production optimizations
    reactStrictMode: true,
    compress: true, // Enable gzip compression
    poweredByHeader: false, // Security improvement (removes X-Powered-By)
    productionBrowserSourceMaps: false, // Disable source maps in production for performance

    // Image optimization - updated for Next.js 16
    images: {
        remotePatterns: [
            { protocol: 'http', hostname: 'localhost', port: '8000', pathname: '/**' },
            { protocol: 'https', hostname: 'your-api-domain.com', pathname: '/**' },
            { protocol: 'https', hostname: 'lh3.googleusercontent.com', pathname: '/**' },
            { protocol: 'https', hostname: '*.googleusercontent.com', pathname: '/**' },
            { protocol: 'https', hostname: 'ui-avatars.com', pathname: '/**' },
            { protocol: 'https', hostname: 'api.dicebear.com', pathname: '/**' }
        ],
        formats: ['image/webp', 'image/avif'],
        deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
        imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
        dangerouslyAllowSVG: true,
        contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    },

    // Experimental features
    experimental: {
        optimizePackageImports: [
            'lucide-react',
            'recharts',
            'framer-motion',
            'date-fns',
            '@radix-ui/react-icons',
            'clsx',
            'tailwind-merge'
        ],
        // CSS optimizations for faster critical path
        inlineCss: true, // Inline critical CSS to avoid render-blocking requests
        cssChunking: 'strict', // More aggressive CSS code-splitting
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
                    {
                        key: 'Cross-Origin-Opener-Policy',
                        value: 'same-origin-allow-popups',
                    },
                    {
                        key: 'Permissions-Policy',
                        value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
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
            {
                source: '/(.*).(jpg|jpeg|gif|png|svg|ico|webp|avif)',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
            {
                source: '/(.*).(woff|woff2|ttf|otf|eot)',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
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

    // API Proxy Rewrites
    async rewrites() {
        const apiUrl = process.env.API_URL || 'http://localhost:8000';
        return [
            {
                source: '/api/:path*',
                destination: `${apiUrl}/:path*`,
            },
        ];
    },
};

module.exports = nextConfig;