import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { ThemeProvider } from "@/components/providers/theme-provider";
import { HydrationWrapper } from "@/components/providers/ssr-safe-provider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Insight Flow",
  description: "Modern project management platform with glassmorphism design",
  keywords: ["project management", "task management", "team collaboration", "productivity"],
  authors: [{ name: "Insight Flow Team" }],
  creator: "Insight Flow",
  publisher: "Insight Flow",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    type: "website",
    locale: "en_US",
    url: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
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
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} font-sans antialiased`}
        suppressHydrationWarning
      >
        <HydrationWrapper>
          <ThemeProvider>
            {children}
          </ThemeProvider>
        </HydrationWrapper>
      </body>
    </html>
  );
}
