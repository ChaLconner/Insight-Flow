"use client";

import Link from "next/link";
import Image from "next/image";
import { motion, animate } from "framer-motion";
import { ArrowDown, Lock, Zap, BarChart3 } from "lucide-react";
import React, { useRef, useState, useEffect } from "react";
import { useAuthStore } from "@/stores/auth-store";

const Counter = ({ value }: { value: number }) => {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }

    const controls = animate(0, value, {
      duration: 2.5,
      ease: [0.25, 0.1, 0.25, 1], // Cubic bezier for a smooth "landing"
      onUpdate(val) {
        node.textContent = Math.floor(val).toLocaleString();
      },
    });

    return () => controls.stop();
  }, [value]);

  return <span ref={ref} className="tabular-nums font-bold text-foreground" />;
};

const heroImages = [
  { src: "/images/dashboard-preview.png", alt: "Dashboard Overview" },
  { src: "/images/projects-preview.png", alt: "Project Management" },
  { src: "/images/analytics-preview.png", alt: "Analytics & Insights" },
  { src: "/images/users-preview.png", alt: "Team Management" },
];

const HeroImageSlideshow = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % heroImages.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full h-full">
      {heroImages.map((image, index) => (
        <motion.div
          key={image.src}
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{
            opacity: index === currentIndex ? 1 : 0,
            scale: index === currentIndex ? 1 : 1.1,
          }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          className="absolute inset-0"
        >
          <Image
            src={image.src}
            alt={image.alt}
            fill
            className="object-cover"
            priority={index === 0}
            sizes="(max-width: 768px) 100vw, 672px"
          />
        </motion.div>
      ))}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <motion.div
          animate={{ y: ["-100%", "200%"] }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          className="absolute inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent blur-[1px]"
        />
      </div>
      <div className="absolute inset-x-0 bottom-0 h-1/4 bg-gradient-to-t from-black/90 via-black/50 to-transparent pointer-events-none" />
    </div>
  );
};

const ScatteredDots = React.memo(() => {
  const dots = [
    { top: "5%", left: "15%", size: "w-1.5 h-1.5", color: "bg-indigo-400", opacity: "opacity-60" },
    { top: "10%", right: "20%", size: "w-1 h-1", color: "bg-purple-400", opacity: "opacity-50" },
    { top: "25%", left: "5%", size: "w-2 h-2", color: "bg-cyan-400", opacity: "opacity-40" },
    { top: "35%", right: "8%", size: "w-1.5 h-1.5", color: "bg-pink-400", opacity: "opacity-50" },
    { top: "50%", left: "3%", size: "w-1 h-1", color: "bg-indigo-300", opacity: "opacity-60" },
    { top: "65%", right: "12%", size: "w-2 h-2", color: "bg-purple-300", opacity: "opacity-40" },
    { top: "75%", left: "10%", size: "w-1 h-1", color: "bg-cyan-300", opacity: "opacity-50" },
    { top: "85%", right: "18%", size: "w-1.5 h-1.5", color: "bg-emerald-400", opacity: "opacity-45" },
    { top: "15%", left: "25%", size: "w-1 h-1", color: "bg-blue-400", opacity: "opacity-55" },
    { top: "45%", right: "5%", size: "w-1 h-1", color: "bg-violet-400", opacity: "opacity-50" },
    { bottom: "20%", left: "8%", size: "w-1.5 h-1.5", color: "bg-rose-400", opacity: "opacity-45" },
    { bottom: "30%", right: "15%", size: "w-1 h-1", color: "bg-amber-400", opacity: "opacity-40" },
    { top: "55%", left: "18%", size: "w-1 h-1", color: "bg-teal-400", opacity: "opacity-50" },
    { top: "20%", right: "25%", size: "w-1 h-1", color: "bg-sky-400", opacity: "opacity-55" },
    { top: "8%", left: "35%", size: "w-1 h-1", color: "bg-fuchsia-400", opacity: "opacity-45" },
    { top: "70%", right: "22%", size: "w-1.5 h-1.5", color: "bg-lime-400", opacity: "opacity-40" },
    { bottom: "15%", left: "22%", size: "w-1 h-1", color: "bg-orange-400", opacity: "opacity-50" },
  ];

  return (
    <div className="absolute -inset-20 overflow-visible pointer-events-none z-10">
      {dots.map((dot, i) => (
        <div
          key={i}
          className={`absolute rounded-full ${dot.size} ${dot.color} ${dot.opacity}`}
          style={{
            top: dot.top,
            bottom: dot.bottom,
            left: dot.left,
            right: dot.right,
          }}
        />
      ))}
    </div>
  );
});

ScatteredDots.displayName = "ScatteredDots";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3,
    },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 100,
    },
  },
};

export function HeroSection() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center mb-20 overflow-visible">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="flex flex-col gap-6"
      >
        <motion.h1
          variants={itemVariants}
          className="text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.1]"
        >
          Manage projects with <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
            Superhuman Speed
          </span>
        </motion.h1>

        <motion.p
          variants={itemVariants}
          className="text-lg text-muted-foreground leading-relaxed max-w-xl"
        >
          Insight Flow is the intelligent workspace that adapts to your
          team. Streamline tasks, automate workflows, and gain real-time
          insights without the clutter.
        </motion.p>

        <motion.div
          variants={itemVariants}
          className="flex flex-wrap items-center gap-4 pt-2"
        >
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
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="pt-8 flex items-center gap-6 text-sm text-muted-foreground"
        >
          <div className="flex -space-x-2">
            {[1, 2, 3, 4].map((i) => (
              <motion.div
                key={i}
                custom={i}
                initial={{ scale: 0 }}
                animate={{
                  scale: 1,
                  y: [0, -8, 0],
                  x: [0, i % 2 === 0 ? 3 : -3, 0],
                }}
                whileHover={{ scale: 1.1, zIndex: 10 }}
                whileTap={{ scale: 1.5, opacity: 0 }}
                transition={{
                  scale: { duration: 0.5, type: "spring" },
                  y: {
                    duration: 2 + i * 0.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 0.2,
                  },
                  x: {
                    duration: 2.5 + i * 0.3,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 0.1,
                  },
                }}
                className={`w-8 h-8 rounded-full border-2 border-background bg-zinc-800 flex items-center justify-center text-[10px] text-white overflow-hidden relative z-0 cursor-pointer`}
              >
                <img
                  src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${
                    i * 123
                  }`}
                  alt="User"
                />
              </motion.div>
            ))}
          </div>
          <div className="flex flex-col">
            <div className="flex gap-1 text-amber-400">
              {"★★★★★".split("").map((star, i) => (
                <span key={i}>{star}</span>
              ))}
            </div>
            <div className="flex items-center gap-1 font-medium">
              <span>Trusted by</span>
              <Counter value={10000} />
              <span>+ teams</span>
            </div>
          </div>
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.5, delay: 0.2 }}
        className="relative lg:h-[650px] flex items-center justify-center overflow-visible"
      >
        <div className="absolute inset-0 z-0 overflow-visible">
          <ScatteredDots />
        </div>

        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[600px] h-[600px] bg-indigo-600/40 rounded-full blur-[150px]" />
          <div className="absolute w-[400px] h-[400px] bg-purple-500/30 rounded-full blur-[120px] translate-x-32" />
          <div className="absolute w-[300px] h-[300px] bg-cyan-500/20 rounded-full blur-[100px] -translate-x-40 translate-y-20" />
        </div>

        <motion.div
          animate={{ y: [0, -40, 0], x: [0, 20, 0], rotate: [0, 180, 360] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -top-5 right-10 w-24 h-24 rounded-full bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-90 shadow-[0_0_60px_rgba(139,92,246,0.5)]"
        />
        <motion.div
          animate={{ y: [0, 30, 0], x: [0, -15, 0] }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1,
          }}
          className="absolute bottom-20 -left-10 w-16 h-16 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 opacity-80 shadow-[0_0_40px_rgba(34,211,238,0.4)]"
        />
        <motion.div
          animate={{ y: [0, -20, 0], scale: [1, 1.2, 1] }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 0.5,
          }}
          className="absolute top-1/4 -left-20 w-10 h-10 rounded-full bg-gradient-to-br from-pink-400 to-rose-500 opacity-70 shadow-[0_0_30px_rgba(244,114,182,0.5)]"
        />
        <motion.div
          animate={{ y: [0, 25, 0], x: [0, -10, 0] }}
          transition={{
            duration: 7,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2,
          }}
          className="absolute bottom-10 right-20 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 opacity-60 shadow-[0_0_25px_rgba(52,211,153,0.4)]"
        />

        <motion.div
          initial={{ y: 60, opacity: 0, rotateX: 20, rotateY: -15 }}
          animate={{
            y: 0,
            opacity: 1,
            rotateX: [10, 5, 10],
            rotateY: [-8, -3, -8],
          }}
          transition={{
            y: { duration: 1, ease: "easeOut" },
            opacity: { duration: 1 },
            rotateX: {
              duration: 10,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1,
            },
            rotateY: {
              duration: 10,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1,
            },
          }}
          style={{ transformStyle: "preserve-3d", perspective: "1200px" }}
          className="relative w-full max-w-2xl mx-auto z-10"
        >
          <div className="absolute -inset-[2px] rounded-[18px] overflow-hidden">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
              className="absolute inset-[-100%] bg-[conic-gradient(from_0deg,transparent_0%,transparent_40%,#818cf8_45%,#c084fc_50%,#f472b6_55%,transparent_60%,transparent_100%)]"
            />
          </div>
          <div className="absolute inset-0 rounded-[16px] bg-[#0a0a0f]" />

          <div className="relative rounded-2xl overflow-hidden shadow-[0_60px_120px_-20px_rgba(0,0,0,0.9),0_40px_80px_-30px_rgba(99,102,241,0.4)] border border-white/20 bg-[#0a0a0f]">
            <div className="flex items-center gap-2 px-5 py-3.5 bg-zinc-900/90 border-b border-white/10">
              <div className="flex gap-2">
                <div className="w-3.5 h-3.5 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                <div className="w-3.5 h-3.5 rounded-full bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]" />
                <div className="w-3.5 h-3.5 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]" />
              </div>
              <div className="flex-1 mx-6">
                <div className="bg-zinc-800/80 rounded-xl px-5 py-2 text-sm text-zinc-300 flex items-center gap-3 border border-white/5">
                  <Lock size={12} className="text-green-400" />
                  <span className="font-medium">insightflow</span>
                </div>
              </div>
            </div>

            <div className="relative aspect-[16/10] overflow-hidden">
              <HeroImageSlideshow />
            </div>
          </div>

          <div className="absolute inset-x-4 -bottom-16 h-16 bg-gradient-to-b from-zinc-900/40 to-transparent blur-2xl opacity-60 transform scale-y-[-1] rounded-full" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 80, scale: 0.8 }}
          animate={{ opacity: 1, x: 0, scale: 1, y: [0, 12, 0] }}
          transition={{
            opacity: { delay: 0.8, duration: 0.5 },
            x: { delay: 0.8, duration: 0.6, type: "spring" },
            scale: { delay: 0.8, duration: 0.5 },
            y: {
              duration: 5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1.5,
            },
          }}
          className="absolute -right-24 top-1/3 w-60 p-5 bg-zinc-900/98 backdrop-blur-2xl rounded-2xl border border-white/15 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.8)] overflow-hidden z-20"
        >
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-400 to-transparent" />

          <div className="flex items-center gap-4 mb-2">
            <motion.div
              animate={{ rotate: [0, 15, -15, 0] }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="p-2.5 bg-amber-500/20 rounded-xl text-amber-400 shadow-[0_0_20px_rgba(251,191,36,0.3)]"
            >
              <Zap size={20} fill="currentColor" />
            </motion.div>
            <div>
              <div className="text-base font-bold text-white">
                System Optimized
              </div>
              <div className="text-xs text-zinc-400">AI Auto-Scale</div>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs mt-2">
            <span className="text-zinc-400">Performance</span>
            <span className="text-green-400 font-bold">+400% 🚀</span>
          </div>
          <div className="w-full h-1 bg-zinc-800 rounded-full mt-2 overflow-hidden">
            <motion.div
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration: 1.5, ease: "easeOut", delay: 2 }}
              className="h-full bg-gradient-to-r from-amber-400 to-orange-500"
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: -80, scale: 0.8 }}
          animate={{ opacity: 1, x: 0, scale: 1, y: [0, -18, 0] }}
          transition={{
            opacity: { delay: 1.1, duration: 0.5 },
            x: { delay: 1.1, duration: 0.6, type: "spring" },
            scale: { delay: 1.1, duration: 0.5 },
            y: {
              duration: 6,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 2,
            },
          }}
          className="absolute -left-24 bottom-1/3 w-56 p-5 bg-zinc-900/98 backdrop-blur-2xl rounded-2xl border border-white/15 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.8)] overflow-hidden z-20"
        >
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent" />

          <div className="flex items-center gap-4 mb-2">
            <div className="p-2.5 bg-emerald-500/20 rounded-xl text-emerald-400 shadow-[0_0_20px_rgba(52,211,153,0.3)]">
              <BarChart3 size={20} />
            </div>
            <div>
              <div className="text-base font-bold text-white">Team Velocity</div>
              <div className="text-sm text-zinc-400">All-time High 🔥</div>
            </div>
          </div>

          <div className="flex items-end justify-between h-8 mt-2 gap-1 px-1">
            {[40, 65, 45, 80, 55, 90, 100].map((h, i) => (
              <motion.div
                key={i}
                initial={{ height: "10%" }}
                animate={{ height: `${h}%` }}
                transition={{
                  duration: 1,
                  delay: 2 + i * 0.1,
                  type: "spring",
                }}
                className="w-full bg-gradient-to-t from-emerald-900/50 to-emerald-400 rounded-t-sm opacity-80"
              />
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
