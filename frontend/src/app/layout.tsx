import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { ErrorBoundary } from "@/components/error-boundary";
import { QueryProvider } from "@/providers/query-provider";
import { Toaster } from "sonner";
import WebVitalsReporter from "@/components/analytics/web-vitals-reporter";
import ServiceWorkerRegistration from "@/components/providers/service-worker-registration";
import { AuthInitializer } from "@/components/providers/auth-initializer";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s | Insight Flow",
    default: "Insight Flow",
  },
  description: "Modern project management platform with glassmorphism design",
  keywords: [
    "project management",
    "task management",
    "team collaboration",
    "productivity",
  ],
  authors: [{ name: "Insight Flow Team" }],
  creator: "Insight Flow",
  publisher: "Insight Flow",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"
  ),
  openGraph: {
    type: "website",
    locale: "en_US",
    url: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
    title: "Insight Flow",
    description: "Modern project management platform with glassmorphism design",
    siteName: "Insight Flow",
  },
  twitter: {
    card: "summary_large_image",
    title: "Insight Flow - Modern Project Management",
    description: "Modern project management platform with glassmorphism design",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
// Google Verification
  verification: {
    google: "google-site-verification=YOUR_VERIFICATION_CODE",
    yandex: "yandex-verification=YOUR_VERIFICATION_CODE",
  },
  alternates: {
    canonical: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "white" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_URL &&
    process.env.NEXT_PUBLIC_API_URL.trim().length > 0
      ? process.env.NEXT_PUBLIC_API_URL
      : "http://localhost:8000";

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  // JSON-LD for Organization
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Insight Flow",
    applicationCategory: "ProjectManagementApplication",
    operatingSystem: "Web",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
    author: {
      "@type": "Organization",
      name: "Insight Flow Team",
      url: appUrl,
    },
    description: "Modern project management platform with glassmorphism design",
    image: `${appUrl}/og-image.png`,
  };

  return (
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <head>
        {/* Preload critical resources */}
        <link
          rel="preconnect"
          href="https://fonts.googleapis.com"
          crossOrigin="anonymous"
        />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          rel="dns-prefetch"
          href={apiBaseUrl}
        />
        {/* Preconnect to API for faster first request */}
        <link
          rel="preconnect"
          href={apiBaseUrl}
          crossOrigin="anonymous"
        />
        {/* Preconnect to common image sources */}
        <link
          rel="preconnect"
          href="https://res.cloudinary.com"
          crossOrigin="anonymous"
        />
        <link
          rel="preconnect"
          href="https://ui-avatars.com"
          crossOrigin="anonymous"
        />

        {/* JSON-LD Structured Data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />

        {/* Theme initialization script - prevents flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var storageKey = 'insight-flow-theme';
                  var defaultTheme = 'dark';
                  var theme = defaultTheme;
                  var stored = localStorage.getItem(storageKey);

                  if (stored) {
                    try {
                      var parsed = JSON.parse(stored);
                      if (parsed && parsed.state && parsed.state.theme) {
                        theme = parsed.state.theme;
                      }
                    } catch (e) {}
                  }

                  var shouldBeDark = theme === 'dark';

                  if (theme === 'system') {
                    shouldBeDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  }

                  // Apply theme class
                  document.documentElement.classList.remove('light', 'dark');
                  if (shouldBeDark) {
                    document.documentElement.classList.add('dark');
                    document.documentElement.style.colorScheme = 'dark';
                  } else {
                    document.documentElement.classList.add('light');
                    document.documentElement.style.colorScheme = 'light';
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body
        className={`${inter.variable} font-sans antialiased`}
        suppressHydrationWarning
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-background focus:text-foreground focus:top-0 focus:left-0 transition-all"
        >
          Skip to content
        </a>
        <QueryProvider>
          {/* HydrationWrapper removed to prevent flash */}
          <ThemeProvider>
            <ErrorBoundary>
              {children}
              <Toaster
                position="bottom-right"
                richColors
                theme="system"
                className="font-sans"
                toastOptions={{
                  classNames: {
                    title: "text-sm font-semibold",
                    description: "text-xs text-muted-foreground",
                    actionButton: "bg-primary text-primary-foreground",
                    cancelButton: "bg-muted text-muted-foreground",
                  },
                  style: {
                    background: "rgba(23, 23, 23, 0.8)", // Glassmorphism base
                    backdropFilter: "blur(12px)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    color: "white",
                  },
                }}
              />
              <AuthInitializer />
              <WebVitalsReporter />
              <ServiceWorkerRegistration />
            </ErrorBoundary>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
