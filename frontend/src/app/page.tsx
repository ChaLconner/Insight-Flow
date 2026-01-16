"use client";

import { LandingNavbar } from "@/components/landing/landing-navbar";
import { HeroSection } from "@/components/landing/hero-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { PricingSection } from "@/components/landing/pricing-section";
import { SiteFooter } from "@/components/landing/site-footer";

export default function LandingPage() {
  return (
    // Force dark mode wrapper
    <div className="dark">
      <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-indigo-500/30">
        {/* Dynamic Background */}
        <div className="fixed inset-0 z-[-1] pointer-events-none">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-500/20 rounded-full blur-[128px] mix-blend-screen" />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[128px] mix-blend-screen" />
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
