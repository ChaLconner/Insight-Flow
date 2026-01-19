"use client";

import Link from "next/link";
import Image from "next/image";
import { Lock, Zap, BarChart3, ArrowDown } from "lucide-react";
import React, { useState, useEffect } from "react";
import { useAuthStore } from "@/stores/auth-store";

// Static counter that doesn't animate - much faster
const Counter = ({ value }: { value: number }) => {
  return <span className="tabular-nums font-bold text-foreground">{value.toLocaleString()}</span>;
};


const heroImages = [
  { src: "/images/dashboard-preview.png", alt: "Dashboard Overview" },
  { src: "/images/projects-preview.png", alt: "Project Management" },
  { src: "/images/analytics-preview.png", alt: "Analytics & Insights" },
  { src: "/images/users-preview.png", alt: "Team Management" },
];

// Optimized Slideshow - Static first, then animates
const HeroImageSlideshow = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [slideshowStarted, setSlideshowStarted] = useState(false);

  // Delay slideshow start to prioritize LCP
  useEffect(() => {
    // Start slideshow after initial render is complete (2.5s delay)
    const startTimer = setTimeout(() => {
      setSlideshowStarted(true);
    }, 2500);
    
    return () => clearTimeout(startTimer);
  }, []);

  // Handle slideshow transitions
  useEffect(() => {
    if (!slideshowStarted) {
      return;
    }

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % heroImages.length);
    }, 4000);
    
    return () => clearInterval(interval);
  }, [slideshowStarted]);

  // Always show first image immediately for fast LCP
  // Only show other images after slideshow has started
  const imagesToRender = slideshowStarted 
    ? heroImages 
    : [heroImages[0]];

  return (
    <div className="relative w-full h-full">
      {imagesToRender.map((image, index) => {
        const actualIndex = slideshowStarted ? index : 0;
        const isVisible = actualIndex === currentIndex;
        
        return (
          <div
            key={image.src}
            className="absolute inset-0"
            style={{ 
              opacity: isVisible ? 1 : 0,
              transition: slideshowStarted ? 'opacity 800ms ease-out' : 'none',
              zIndex: isVisible ? 10 : 0
            }}
          >
            <Image
              src={image.src}
              alt={image.alt}
              fill
              className="object-cover"
              priority={index === 0}
              loading={index === 0 ? "eager" : "lazy"}
              sizes="(max-width: 768px) 100vw, 672px"
              quality={index === 0 ? 85 : 75}
            />
          </div>
        );
      })}
      <div className="absolute inset-x-0 bottom-0 h-1/4 bg-gradient-to-t from-black/90 via-black/50 to-transparent pointer-events-none z-20" />
    </div>
  );
};

// Pure CSS animated dots - no JS needed
const ScatteredDots = React.memo(() => {
  return (
    <div className="absolute -inset-20 overflow-visible pointer-events-none z-10">
      <div className="absolute top-[5%] left-[15%] w-1.5 h-1.5 rounded-full bg-indigo-400 opacity-60" />
      <div className="absolute top-[10%] right-[20%] w-1 h-1 rounded-full bg-purple-400 opacity-50" />
      <div className="absolute top-[25%] left-[5%] w-2 h-2 rounded-full bg-cyan-400 opacity-40" />
      <div className="absolute top-[35%] right-[8%] w-1.5 h-1.5 rounded-full bg-pink-400 opacity-50" />
      <div className="absolute top-[50%] left-[3%] w-1 h-1 rounded-full bg-indigo-300 opacity-60" />
      <div className="absolute top-[65%] right-[12%] w-2 h-2 rounded-full bg-purple-300 opacity-40" />
      <div className="absolute top-[75%] left-[10%] w-1 h-1 rounded-full bg-cyan-300 opacity-50" />
      <div className="absolute top-[85%] right-[18%] w-1.5 h-1.5 rounded-full bg-emerald-400 opacity-45" />
    </div>
  );
});

ScatteredDots.displayName = "ScatteredDots";

export function HeroSection() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div 
      className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center mb-20 overflow-visible" 
      style={{ contain: 'layout style' }}
    >
      {/* Left content - CSS animations only */}
      <div className="flex flex-col gap-6 animate-fade-in">
        <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.1]">
          Manage projects with <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
            Superhuman Speed
          </span>
        </h1>

        <p className="text-lg text-muted-foreground leading-relaxed max-w-xl">
          Insight Flow is the intelligent workspace that adapts to your
          team. Streamline tasks, automate workflows, and gain real-time
          insights without the clutter.
        </p>

        <div className="flex flex-wrap items-center gap-4 pt-2">
          <Link
            href={mounted && isAuthenticated ? "/dashboard" : "/auth/register"}
            className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-full transition-all hover:scale-105 active:scale-95 shadow-lg shadow-indigo-600/25"
          >
            Start for free
          </Link>
          <Link
            href="#features"
            className="px-8 py-3.5 bg-secondary hover:bg-secondary/80 text-foreground font-semibold rounded-full transition-all flex items-center gap-2 border border-border"
          >
            <ArrowDown size={20} />
            Explore Features
          </Link>
        </div>

        <div className="pt-8 flex items-center gap-6 text-sm text-muted-foreground">
          <div className="flex -space-x-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="w-8 h-8 rounded-full border-2 border-background bg-zinc-800 flex items-center justify-center text-[10px] text-white overflow-hidden relative z-0 transition-transform duration-300 hover:scale-110 hover:z-10 cursor-pointer"
              >
                <img
                  src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${i * 123}`}
                  alt="User"
                  loading="lazy"
                />
              </div>
            ))}
          </div>
          <div className="flex flex-col">
            <div className="flex gap-1 text-amber-400">★★★★★</div>
            <div className="flex items-center gap-1 font-medium">
              <span>Trusted by</span>
              <Counter value={10000} />
              <span>+ teams</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Hero visual */}
      <div className="relative lg:h-[650px] flex items-center justify-center overflow-visible animate-fade-in">
        {/* Scattered dots - desktop only */}
        <div className="absolute inset-0 z-0 overflow-visible hidden lg:block">
          <ScatteredDots />
        </div>

        {/* Background glow - desktop only, reduced blur */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none hidden lg:block">
          <div className="w-[400px] h-[400px] bg-indigo-600/30 rounded-full blur-[40px] opacity-70" />
          <div className="absolute w-[300px] h-[300px] bg-purple-500/20 rounded-full blur-[30px] translate-x-32" />
        </div>

        {/* Floating orbs - CSS animation, desktop only */}
        <div className="hidden lg:block">
          <div className="absolute -top-5 right-10 w-24 h-24 rounded-full bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-90 shadow-[0_0_40px_rgba(139,92,246,0.4)] animate-float" />
          <div className="absolute bottom-20 -left-10 w-16 h-16 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 opacity-80 shadow-[0_0_30px_rgba(34,211,238,0.3)] animate-float-delayed" />
        </div>

        {/* Main browser mockup */}
        <div 
          className="relative w-full max-w-2xl mx-auto z-10"
          style={{ perspective: "1200px" }}
        >
          {/* Glowing border - desktop only, CSS animation */}
          <div className="absolute -inset-[2px] rounded-[18px] overflow-hidden hidden md:block">
            <div className="absolute inset-[-100%] bg-[conic-gradient(from_0deg,transparent_0%,transparent_40%,#818cf8_45%,#c084fc_50%,#f472b6_55%,transparent_60%,transparent_100%)] animate-spin-slow" />
          </div>
          <div className="absolute inset-0 rounded-[16px] bg-[#0a0a0f]" />

          <div className="relative rounded-2xl overflow-hidden shadow-[0_60px_120px_-20px_rgba(0,0,0,0.9),0_40px_80px_-30px_rgba(99,102,241,0.4)] border border-white/20 bg-[#0a0a0f]">
            {/* Browser bar */}
            <div className="flex items-center gap-2 px-5 py-3.5 bg-zinc-900/90 border-b border-white/10">
              <div className="flex gap-2">
                <div className="w-3.5 h-3.5 rounded-full bg-red-500" />
                <div className="w-3.5 h-3.5 rounded-full bg-yellow-500" />
                <div className="w-3.5 h-3.5 rounded-full bg-green-500" />
              </div>
              <div className="flex-1 mx-6">
                <div className="bg-zinc-800/80 rounded-xl px-5 py-2 text-sm text-zinc-300 flex items-center gap-3 border border-white/5">
                  <Lock size={12} className="text-green-400" />
                  <span className="font-medium">insightflow</span>
                </div>
              </div>
            </div>

            {/* Dashboard image */}
            <div className="relative aspect-[16/10] overflow-hidden">
              <HeroImageSlideshow />
            </div>
          </div>

          {/* Reflection */}
          <div className="absolute inset-x-4 -bottom-16 h-16 bg-gradient-to-b from-zinc-900/40 to-transparent blur-2xl opacity-60 rounded-full" style={{ transform: 'scaleY(-1)' }} />
        </div>

        {/* Floating card - System Optimized - desktop only */}
        <div className="absolute -right-24 top-1/3 w-60 p-5 bg-zinc-900/98 backdrop-blur-xl rounded-2xl border border-white/15 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.8)] overflow-hidden z-20 hidden lg:block animate-float transition-transform duration-300 hover:scale-105">
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-400 to-transparent" />
          <div className="flex items-center gap-4 mb-2">
            <div className="p-2.5 bg-amber-500/20 rounded-xl text-amber-400">
              <Zap size={20} fill="currentColor" />
            </div>
            <div>
              <div className="text-base font-bold text-white">System Optimized</div>
              <div className="text-xs text-zinc-400">AI Auto-Scale</div>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs mt-2">
            <span className="text-zinc-400">Performance</span>
            <span className="text-green-400 font-bold">+400% 🚀</span>
          </div>
          <div className="w-full h-1 bg-zinc-800 rounded-full mt-2 overflow-hidden">
            <div className="h-full w-full bg-gradient-to-r from-amber-400 to-orange-500 animate-progress" />
          </div>
        </div>

        {/* Floating card - Team Velocity - desktop only */}
        <div className="absolute -left-24 bottom-1/3 w-56 p-5 bg-zinc-900/98 backdrop-blur-xl rounded-2xl border border-white/15 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.8)] overflow-hidden z-20 hidden lg:block animate-float-delayed transition-transform duration-300 hover:scale-105">
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent" />
          <div className="flex items-center gap-4 mb-2">
            <div className="p-2.5 bg-emerald-500/20 rounded-xl text-emerald-400">
              <BarChart3 size={20} />
            </div>
            <div>
              <div className="text-base font-bold text-white">Team Velocity</div>
              <div className="text-sm text-zinc-400">All-time High 🔥</div>
            </div>
          </div>
          <div className="flex items-end justify-between h-8 mt-2 gap-1 px-1">
            {[40, 65, 45, 80, 55, 90, 100].map((h, i) => (
              <div
                key={i}
                className="w-full bg-gradient-to-t from-emerald-900/50 to-emerald-400 rounded-t-sm opacity-80 animate-bar"
                style={{ 
                  height: `${h}%`,
                  animationDelay: `${i * 0.1}s`
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
