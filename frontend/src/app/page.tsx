"use client";

import dynamic from "next/dynamic";
import { LandingNavbar } from "@/components/landing/landing-navbar";
import { HeroSection } from "@/components/landing/hero-section";
import { SiteFooter } from "@/components/landing/site-footer";

// Dynamic imports for below-the-fold sections to improve LCP
const FeaturesSection = dynamic(
  () => import("@/components/landing/features-section").then(mod => ({ default: mod.FeaturesSection })),
  { 
    loading: () => <div className="min-h-[400px]" />,
    ssr: true 
  }
);

const PricingSection = dynamic(
  () => import("@/components/landing/pricing-section").then(mod => ({ default: mod.PricingSection })),
  { 
    loading: () => <div className="min-h-[400px]" />,
    ssr: true 
  }
);

export default function LandingPage() {
  return (
    // Force dark mode wrapper
    <div className="dark">
      <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-indigo-500/30">
        {/* Dynamic Background - Hidden on mobile for performance */}
        <div className="fixed inset-0 z-[-1] pointer-events-none transform-gpu hidden md:block">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-500/20 rounded-full blur-[64px] mix-blend-screen" />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[64px] mix-blend-screen" />
        </div>

        <LandingNavbar />

        <main className="pt-32 pb-16 px-6">
          <HeroSection />
          <FeaturesSection />
          <PricingSection />
        </main>

        <SiteFooter />
      </div>
    </div>
  );
}
