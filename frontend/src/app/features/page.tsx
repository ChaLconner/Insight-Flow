"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { Layout, GitBranch, BarChart3, Users } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";

interface FeatureData {
  title: string;
  description: string;
  icon: React.ReactNode;
  points: string[];
  visual: React.ReactNode;
}

const FeatureCard = ({ feature, index }: { feature: FeatureData, index: number }) => {
  return (
    <motion.div 
      className="flex-shrink-0 w-[85vw] md:w-[70vw] lg:w-[60vw] snap-center"
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      viewport={{ once: true }}
    >
      <div className="h-full flex flex-col md:grid md:grid-cols-2 gap-8 md:gap-16 bg-gradient-to-br from-[#16161d] to-[#0d0d12] border border-white/15 rounded-[2.5rem] p-6 md:p-12 shadow-2xl shadow-black/50 hover:shadow-indigo-500/10 hover:border-indigo-500/30 transition-all duration-500 group relative overflow-hidden backdrop-blur-sm">
        
        {/* Subtle Glow Background */}
        <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

        {/* Text Content */}
        <div className="flex flex-col justify-start space-y-6 md:space-y-8 z-10">
          <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-[#1E1E24] border border-white/10 flex items-center justify-center text-indigo-400 shadow-[0_8px_16px_-6px_rgba(0,0,0,0.5)] backdrop-blur-sm shrink-0 group-hover:scale-110 transition-transform duration-300">
            {feature.icon}
          </div>
          
          <div className="space-y-3 md:space-y-4">
             <h3 className="text-2xl md:text-4xl lg:text-5xl font-black tracking-tight text-white leading-tight drop-shadow-lg">
               {feature.title}
             </h3>
             <p className="text-base md:text-lg lg:text-xl text-zinc-400 leading-relaxed font-light">
               {feature.description}
             </p>
          </div>
        </div>

        {/* Visual Content */}
        <div className="flex items-center justify-center z-10">
             <div className="w-full relative rounded-2xl overflow-hidden shadow-[0_20px_50px_-12px_rgba(0,0,0,0.9)] border border-white/10 bg-[#050505] group-hover:scale-[1.03] transition-transform duration-500 ease-out">
                {feature.visual}
                {/* Glossy overlay */}
                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent pointer-events-none" />
             </div>
        </div>
      </div>
    </motion.div>
  );
};

export default function FeaturesPage() {
  const features = [
    {
      title: "Centralized Dashboard",
      description: "Get a bird's-eye view of your entire operation. Track active tasks, pending reviews, and team velocity in one place.",
      icon: <Layout size={24} />,
      points: ["Real-time overview", "Task status tracking", "Team velocity metrics"],
      visual: (
        <div className="w-full h-auto">
           <Image 
             src="/images/dashboard-preview.png" 
             alt="Insight Flow Dashboard" 
             width={1200} 
             height={800} 
             className="w-full h-auto rounded-xl shadow-2xl"
           />
        </div>
      )
    },
    {
      title: "Smart Project Management",
      description: "Organize chaos into clarity. Filter, sort, and manage multiple projects with intuitive status tracking.",
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
           />
        </div>
      )
    },
    {
      title: "Deep Analytics",
      description: "Data-driven decisions made easy. Visualize completion rates, velocity trends, and team performance metrics.",
      icon: <BarChart3 size={24} />,
      points: ["Visual progress charts", "Completion rate tracking", "Velocity analysis"],
      visual: (
        <div className="w-full h-auto">
           <Image 
             src="/images/analytics-preview.png" 
             alt="Insight Flow Analytics" 
             width={1200} 
             height={800} 
             className="w-full h-auto rounded-xl shadow-2xl"
           />
        </div>
      )
    },
    {
      title: "Team Management",
      description: "Manage your growing team efficiently. Handle roles, permissions, and status with a robust user system.",
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
           />
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-indigo-500/30">
        {/* Dynamic Background */}
        <div className="fixed inset-0 z-[-1]">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-500/20 rounded-full blur-[128px] mix-blend-screen" />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[128px] mix-blend-screen" />
        </div>

        <Navbar />
        <main className="pt-32 pb-16 px-6 relative">
            {/* Aura Background Glow */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
               <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/20 rounded-full blur-[150px]" />
               <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-purple-500/15 rounded-full blur-[130px]" />
               <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-cyan-500/10 rounded-full blur-[120px]" />
            </div>

            <div className="max-w-7xl mx-auto px-6 text-center mb-12 relative z-10">
               <h1 className="text-4xl md:text-6xl font-bold mb-6">Built for high-performance teams</h1>
               <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                 We've obsessed over every detail. Swipe to explore how we supercharge your workflow.
               </p>
            </div>
            
            <div 
              className="flex overflow-x-auto pb-12 gap-6 px-6 snap-x snap-mandatory"
            >
              {features.map((feature, i) => (
                <FeatureCard key={i} feature={feature} index={i} />
              ))}
            </div>
        </main>
        <Footer />
    </div>
  );
}
