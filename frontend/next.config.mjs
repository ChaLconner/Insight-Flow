import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required by the production Dockerfile's minimal runtime image.
  output: "standalone",

  // Monorepo configuration - trace dependencies from the root directory
  outputFileTracingRoot: path.join(__dirname, "../"),

  // Turbopack configuration - must match outputFileTracingRoot
  turbopack: {
    root: path.join(__dirname, "../"),
  },

  // Production optimizations
  reactStrictMode: true,
  compress: true, // Enable gzip compression
  poweredByHeader: false, // Security improvement (removes X-Powered-By)
  productionBrowserSourceMaps: false, // Disable source maps in production for performance
  devIndicators: process.env.NEXT_PUBLIC_E2E === "1" ? false : undefined,
  allowedDevOrigins: ["127.0.0.1", "localhost"],

  // Image optimization - updated for Next.js 16
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/**",
      },
      // Production API domain should be added here or via environment variable
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.googleusercontent.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
        pathname: "/**",
      },
      { protocol: "https", hostname: "ui-avatars.com", pathname: "/**" },
      { protocol: "https", hostname: "api.dicebear.com", pathname: "/7.x/**" },
      // Cloudinary for avatar uploads
      {
        protocol: "https",
        hostname: "res.cloudinary.com",
        pathname: "/**",
      },
    ],
    formats: ["image/webp", "image/avif"],
    qualities: [75, 85],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    contentDispositionType: "attachment",
    minimumCacheTTL: 31536000,
  },

  // Experimental features
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "framer-motion",
      "date-fns",
      "@radix-ui/react-icons",
      "clsx",
      "tailwind-merge",
    ],
    // CSS optimizations for faster critical path
    inlineCss: true, // Inline critical CSS to avoid render-blocking requests
  },

  // Performance optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },

  // Environment variables
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // Headers for security and performance
  async headers() {
    const headers = [
      {
        source: "/auth/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, max-age=0, must-revalidate",
          },
          {
            key: "Pragma",
            value: "no-cache",
          },
        ],
      },
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "origin-when-cross-origin",
          },
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
          {
            key: "Permissions-Policy",
            value:
              "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];

    // Only add aggressive caching in production
    if (process.env.NODE_ENV === "production") {
      headers.push(
        {
          source: "/(.*).(jpg|jpeg|gif|png|svg|ico|webp|avif)",
          headers: [
            {
              key: "Cache-Control",
              value: "public, max-age=31536000, immutable",
            },
          ],
        },
        {
          source: "/(.*).(woff|woff2|ttf|otf|eot)",
          headers: [
            {
              key: "Cache-Control",
              value: "public, max-age=31536000, immutable",
            },
          ],
        }
      );
    }

    return headers;
  },

  // Redirect rules
  async redirects() {
    return [
      {
        source: "/login",
        destination: "/auth/login",
        permanent: true,
      },
    ];
  },

  // API Proxy Rewrites
  async rewrites() {
    const apiUrl = process.env.API_URL || "http://127.0.0.1:8000";
    return [
      // Root level endpoints that should NOT go to /api/v1
      {
        source: "/api/minimal-test",
        destination: `${apiUrl}/minimal-test`,
      },
      {
        source: "/api/health",
        destination: `${apiUrl}/health`,
      },
      {
        source: "/api/health/:path*",
        destination: `${apiUrl}/health/:path*`,
      },
      {
        source: "/api/metrics",
        destination: `${apiUrl}/metrics`,
      },
      // All other API requests go to /api/v1
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
