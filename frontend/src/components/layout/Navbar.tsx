"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";
export function Navbar() {

  return (
    <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-background/50 backdrop-blur-xl supports-[backdrop-filter]:bg-background/20">
      <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tight hover:opacity-80 transition-opacity">
          <Image src="/icon.svg" alt="Insight Flow Logo" width={32} height={32} className="w-8 h-8 rounded-lg" priority />
          <span className="hidden xs:inline">Insight Flow</span>
        </Link>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
          <Link 
            href="/#features" 
            className="hover:text-foreground transition-colors"
          >
            Features
          </Link>
          <Link 
            href="/#pricing" 
            className="hover:text-foreground transition-colors"
          >
            Pricing
          </Link>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <Link 
            href="/auth/login" 
            className="text-sm font-medium hover:text-indigo-400 transition-colors"
          >
            Log In
          </Link>
          <Link 
            href="/auth/register" 
            className="group px-3 md:px-5 py-2 md:py-2.5 bg-white text-black hover:bg-indigo-50 text-sm font-semibold rounded-full transition-all hover:shadow-[0_0_20px_-5px_rgba(255,255,255,0.5)] flex items-center gap-2"
          >
            Get Started
            <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </div>
    </nav>
  );
}
