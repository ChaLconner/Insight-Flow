"use client";

import Image from "next/image";

export function Footer() {
  return (
    <footer className="border-t border-white/10 py-12 bg-zinc-950">
       <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-3 gap-8">
          <div className="col-span-2">
             <div className="flex items-center gap-2 font-bold text-xl tracking-tight mb-4">
                <Image src="/icon.svg" alt="Insight Flow Logo" width={24} height={24} className="w-6 h-6 rounded" />
                Insight Flow
             </div>
             <p className="text-muted-foreground max-w-sm">
                The intelligent workspace for high-performance teams.
             </p>
          </div>
          <div>
             <h4 className="font-semibold mb-4 text-white">Product</h4>
             <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="/#features" className="hover:text-indigo-400">Features</a></li>
                <li><a href="/#pricing" className="hover:text-indigo-400">Pricing</a></li>
                <li><a href="/auth/login" className="hover:text-indigo-400">Log In</a></li>
             </ul>
          </div>
       </div>
       <div className="max-w-7xl mx-auto px-6 mt-12 pt-8 border-t border-white/5 text-sm text-zinc-500 flex justify-between">
          <p>© 2024 Insight Flow. All rights reserved.</p>
          <div className="flex gap-4">
             <a href="#" className="hover:text-zinc-300">Privacy</a>
             <a href="#" className="hover:text-zinc-300">Terms</a>
          </div>
       </div>
    </footer>
  );
}
