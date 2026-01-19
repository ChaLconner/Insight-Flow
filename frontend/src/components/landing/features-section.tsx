"use client";

import Image from "next/image";
import { Layout, GitBranch, BarChart3, Users } from "lucide-react";
import { useMemo } from "react";

interface FeatureData {
  title: string;
  description: string;
  icon: React.ReactNode;
  points: string[];
  visual: React.ReactNode;
}

const FeatureCard = ({
  feature,
  index,
}: {
  feature: FeatureData;
  index: number;
}) => {
  const glowColors = [
    "from-indigo-600 via-indigo-400 to-blue-500",
    "from-purple-600 via-purple-400 to-pink-500",
    "from-cyan-600 via-cyan-400 to-teal-500",
    "from-orange-600 via-orange-400 to-red-500",
  ];

  return (
    <div className="flex-shrink-0 w-[85vw] md:w-[70vw] lg:w-[60vw] snap-center">
      <div 
        className="group h-full flex flex-col md:grid md:grid-cols-2 gap-8 md:gap-16 bg-gradient-to-br from-zinc-800/90 via-zinc-900/95 to-zinc-950 border border-zinc-700/50 rounded-[2.5rem] p-8 md:p-12 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] relative overflow-hidden" 
        style={{ contain: 'layout paint' }}
      >
        {/* Top highlight line */}
        <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-zinc-500/50 to-transparent" />

        {/* Text Content */}
        <div className="flex flex-col justify-center space-y-8 z-10">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-zinc-700 to-zinc-800 border border-zinc-600/50 flex items-center justify-center text-indigo-400 shadow-lg">
            {feature.icon}
          </div>

          <div className="space-y-4">
            <h3 className="text-3xl md:text-5xl font-black tracking-tight text-white leading-tight drop-shadow-[0_2px_10px_rgba(255,255,255,0.1)]">
              {feature.title}
            </h3>
            <p className="text-lg md:text-xl text-zinc-300 leading-relaxed font-light">
              {feature.description}
            </p>
          </div>
        </div>

        {/* Visual Content */}
        <div className="flex items-center justify-center z-10 relative">
          {/* Diffused Glowing Border Effect - Hidden on mobile */}
          <div
            className={`absolute inset-0 rounded-[18px] blur-md opacity-40 transition-opacity duration-500 group-hover:opacity-80 hidden md:block bg-gradient-to-br ${glowColors[index % 4]}`}
          />

          <div className="w-full relative rounded-2xl overflow-hidden shadow-[0_30px_60px_-10px_rgba(0,0,0,0.9)] border border-zinc-500/30 bg-zinc-950/80 z-10 transition-transform duration-300 hover:scale-[1.02]">
            {feature.visual}
            {/* Enhanced Glossy overlay */}
            <div className="absolute inset-0 bg-gradient-to-tr from-white/10 via-white/5 to-transparent pointer-events-none mix-blend-overlay" />
            {/* Border highlight */}
            <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-white/10 pointer-events-none" />
          </div>
        </div>
      </div>
    </div>
  );
};

import { useElementOnScreen } from "@/hooks/use-element-on-screen";

// ... feature data interface and FeatureCard component ...

export function FeaturesSection() {
  const [ref, isVisible] = useElementOnScreen({ threshold: 0.1 });
  
  const features = useMemo(() => [
    {
      title: "Centralized Dashboard",
      description:
        "Get a bird's-eye view of your entire operation. Track active tasks, pending reviews, and team velocity in one place.",
      icon: <Layout size={24} />,
      points: [
        "Real-time overview",
        "Task status tracking",
        "Team velocity metrics",
      ],
      visual: (
        <div className="w-full h-auto">
          <Image
            src="/images/dashboard-preview.png"
            alt="Insight Flow Dashboard"
            width={1200}
            height={800}
            className="w-full h-auto rounded-xl shadow-2xl"
            sizes="(max-width: 768px) 85vw, (max-width: 1200px) 50vw, 33vw"
            loading="lazy"
          />
        </div>
      ),
    },
    {
      title: "Smart Project Management",
      description:
        "Organize chaos into clarity. Filter, sort, and manage multiple projects with intuitive status tracking.",
      icon: <GitBranch size={24} />,
      points: ["Project filtering", "Status indicators", "Member assignment"],
      visual: (
        <div className="w-full h-auto">
          <Image
            src="/images/projects-preview.png"
            alt="Insight Flow Projects"
            width={1200}
            height={800}
            className="w-full h-auto rounded-xl shadow-2xl"
            sizes="(max-width: 768px) 85vw, (max-width: 1200px) 50vw, 33vw"
            loading="lazy"
          />
        </div>
      ),
    },
    {
      title: "Deep Analytics",
      description:
        "Data-driven decisions made easy. Visualize completion rates, velocity trends, and team performance metrics.",
      icon: <BarChart3 size={24} />,
      points: [
        "Visual progress charts",
        "Completion rate tracking",
        "Velocity analysis",
      ],
      visual: (
        <div className="w-full h-auto">
          <Image
            src="/images/analytics-preview.png"
            alt="Insight Flow Analytics"
            width={1200}
            height={800}
            className="w-full h-auto rounded-xl shadow-2xl"
            sizes="(max-width: 768px) 85vw, (max-width: 1200px) 50vw, 33vw"
            loading="lazy"
          />
        </div>
      ),
    },
    {
      title: "Team Management",
      description:
        "Manage your growing team efficiently. Handle roles, permissions, and status with a robust user system.",
      icon: <Users size={24} />,
      points: ["Role-based access", "User status monitoring", "Admin controls"],
      visual: (
        <div className="w-full h-auto">
          <Image
            src="/images/users-preview.png"
            alt="Insight Flow Users"
            width={1200}
            height={800}
            className="w-full h-auto rounded-xl shadow-2xl"
            sizes="(max-width: 768px) 85vw, (max-width: 1200px) 50vw, 33vw"
            loading="lazy"
          />
        </div>
      ),
    },
  ], []);

  return (
    <div
      id="features"
      className="scroll-mt-20 py-20 overflow-hidden relative"
      style={{ contain: 'layout style' }}
      ref={ref}
    >
      {/* Aura Background Glow - Hidden on mobile */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden hidden md:block">
        <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[60px]" />
        <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-[60px]" />
      </div>
      
      <div className={`max-w-7xl mx-auto px-6 text-center mb-12 duration-700 transition-all ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
        <h2 className="text-3xl md:text-5xl font-bold mb-6">
          Built for high-performance teams
        </h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          We've obsessed over every detail. Swipe to explore how we
          supercharge your workflow.
        </p>
      </div>

      <div className="relative w-full overflow-hidden mask-gradient-x">
         {/* Gradient Masks for smooth fade edges */}
        <div className="absolute left-0 top-0 bottom-0 w-20 z-10 bg-gradient-to-r from-background to-transparent pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-20 z-10 bg-gradient-to-l from-background to-transparent pointer-events-none" />
        
        <div className="flex w-max gap-6 animate-infinite-scroll hover:pause will-change-transform">
          {/* Double mapping for seamless infinite loop */}
          {[...features, ...features].map((feature, i) => (
            <FeatureCard key={i} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
