"use client";

import Link from "next/link";
import Image from "next/image";
import { motion, animate } from "framer-motion";
import { 
  ArrowRight, 
  BarChart3, 
  Users, 
  Zap, 
  CheckCircle2,
  Layout,
  GitBranch,
  Lock,
  ArrowDown
} from "lucide-react";
import { useRef, useState, useEffect } from "react";

const Counter = ({ value }: { value: number }) => {
  const ref = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    const node = ref.current;
    if (!node) {return;}

    const controls = animate(0, value, {
      duration: 2.5,
      ease: [0.25, 0.1, 0.25, 1], // Cubic bezier for a smooth "landing"
      onUpdate(val) {
        node.textContent = Math.floor(val).toLocaleString();
      }
    });

    return () => controls.stop();
  }, [value]);

  return <span ref={ref} className="tabular-nums font-bold text-foreground" />;
};

// Hero Image Slideshow Component
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
            scale: index === currentIndex ? 1 : 1.1
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
          />
        </motion.div>
      ))}
      {/* Holographic scan line effect */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
         <motion.div 
           animate={{ y: ["-100%", "200%"] }}
           transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
           className="absolute inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent blur-[1px]"
         />
      </div>
      {/* Bottom fade */}
      <div className="absolute inset-x-0 bottom-0 h-1/4 bg-gradient-to-t from-black/90 via-black/50 to-transparent pointer-events-none" />
    </div>
  );
};

// Scattered Dots Component - Static dots around the browser mockup
const ScatteredDots = () => {
  // Pre-computed positions for consistent rendering
  const dots = [
    { top: '5%', left: '15%', size: 'w-1.5 h-1.5', color: 'bg-indigo-400', opacity: 'opacity-60' },
    { top: '10%', right: '20%', size: 'w-1 h-1', color: 'bg-purple-400', opacity: 'opacity-50' },
    { top: '25%', left: '5%', size: 'w-2 h-2', color: 'bg-cyan-400', opacity: 'opacity-40' },
    { top: '35%', right: '8%', size: 'w-1.5 h-1.5', color: 'bg-pink-400', opacity: 'opacity-50' },
    { top: '50%', left: '3%', size: 'w-1 h-1', color: 'bg-indigo-300', opacity: 'opacity-60' },
    { top: '65%', right: '12%', size: 'w-2 h-2', color: 'bg-purple-300', opacity: 'opacity-40' },
    { top: '75%', left: '10%', size: 'w-1 h-1', color: 'bg-cyan-300', opacity: 'opacity-50' },
    { top: '85%', right: '18%', size: 'w-1.5 h-1.5', color: 'bg-emerald-400', opacity: 'opacity-45' },
    { top: '15%', left: '25%', size: 'w-1 h-1', color: 'bg-blue-400', opacity: 'opacity-55' },
    { top: '45%', right: '5%', size: 'w-1 h-1', color: 'bg-violet-400', opacity: 'opacity-50' },
    { bottom: '20%', left: '8%', size: 'w-1.5 h-1.5', color: 'bg-rose-400', opacity: 'opacity-45' },
    { bottom: '30%', right: '15%', size: 'w-1 h-1', color: 'bg-amber-400', opacity: 'opacity-40' },
    { top: '55%', left: '18%', size: 'w-1 h-1', color: 'bg-teal-400', opacity: 'opacity-50' },
    { top: '20%', right: '25%', size: 'w-1 h-1', color: 'bg-sky-400', opacity: 'opacity-55' },
    // +3 more dots (20% increase)
    { top: '8%', left: '35%', size: 'w-1 h-1', color: 'bg-fuchsia-400', opacity: 'opacity-45' },
    { top: '70%', right: '22%', size: 'w-1.5 h-1.5', color: 'bg-lime-400', opacity: 'opacity-40' },
    { bottom: '15%', left: '22%', size: 'w-1 h-1', color: 'bg-orange-400', opacity: 'opacity-50' },
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
            right: dot.right 
          }}
        />
      ))}
    </div>
  );
};



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

interface FeatureData {
  title: string;
  description: string;
  icon: React.ReactNode;
  points: string[];
  visual: React.ReactNode;
}

interface PlanData {
  name: string;
  price: string;
  originalPrice?: string;
  description: string;
  features: string[];
  cta: string;
  popular?: boolean;
  badge?: string;
  badgeColor?: string;
}

const FeatureCard = ({ feature, index }: { feature: FeatureData, index: number }) => {
  return (
    <motion.div 
      className="flex-shrink-0 w-[85vw] md:w-[70vw] lg:w-[60vw] snap-center"
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      viewport={{ once: true }}
    >
      <div className="group h-full flex flex-col md:grid md:grid-cols-2 gap-8 md:gap-16 bg-gradient-to-br from-zinc-800/90 via-zinc-900/95 to-zinc-950 border border-zinc-700/50 rounded-[2.5rem] p-8 md:p-12 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] relative overflow-hidden">
        
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
        <div className="flex items-center justify-center z-10 relative group-hover/card">
             {/* Dynamic Back Glow */}
             {/* Diffused Glowing Border Effect */}
             <div className={`absolute -inset-0.5 rounded-[18px] blur-md opacity-60 transition-all duration-500 group-hover:opacity-100 group-hover:blur-xl group-hover:-inset-2 ${
               index % 4 === 0 ? "bg-gradient-to-br from-indigo-600 via-indigo-400 to-blue-500" : 
               index % 4 === 1 ? "bg-gradient-to-br from-purple-600 via-purple-400 to-pink-500" : 
               index % 4 === 2 ? "bg-gradient-to-br from-cyan-600 via-cyan-400 to-teal-500" : 
               "bg-gradient-to-br from-orange-600 via-orange-400 to-red-500"
             }`} />
             
             <motion.div 
               whileHover={{ scale: 1.03, rotateY: 2 }}
               transition={{ type: "spring", stiffness: 200, damping: 25 }}
               className="w-full relative rounded-2xl overflow-hidden shadow-[0_30px_60px_-10px_rgba(0,0,0,0.9)] border border-zinc-500/30 bg-zinc-950/80 backdrop-blur-sm z-10"
             >
                {feature.visual}
                {/* Enhanced Glossy overlay */}
                <div className="absolute inset-0 bg-gradient-to-tr from-white/10 via-white/5 to-transparent pointer-events-none mix-blend-overlay" />
                {/* Border highlight */}
                <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-white/10 pointer-events-none" />
             </motion.div>
        </div>
      </div>
    </motion.div>
  );
};

const PricingCard = ({ plan, index }: { plan: PlanData, index: number }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ delay: index * 0.15, duration: 0.5 }}
      className={`relative p-8 rounded-2xl border transition-all duration-300 flex flex-col ${
        plan.popular 
          ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/20' 
          : 'border-white/10 bg-zinc-900/50 hover:bg-zinc-900/80 hover:border-white/20'
      }`}
    >
      {plan.badge && (
         <div className={`absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide text-white ${plan.badgeColor ?? 'bg-indigo-500'}`}>
            {plan.badge}
         </div>
      )}

      <div className="mb-8">
        <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
        <div className="flex items-baseline gap-1">
          {plan.originalPrice && (
             <span className="text-sm text-muted-foreground line-through decoration-red-500/50">${plan.originalPrice}</span>
          )}
          <span className="text-4xl font-extrabold">${plan.price}</span>
          <span className="text-sm font-medium text-muted-foreground">/mo</span>
        </div>
        <p className="text-sm text-muted-foreground mt-4 leading-relaxed">{plan.description}</p>
      </div>

      <ul className="space-y-4 mb-8 flex-1">
        {plan.features.map((feature: string, i: number) => (
          <li key={i} className="flex items-center gap-3 text-sm text-zinc-300">
            <CheckCircle2 size={18} className={`shrink-0 ${plan.popular ? "text-indigo-400" : "text-zinc-500"}`} />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <Link 
        href={`/auth/register${plan.name !== "Free" ? `?plan=${plan.name.toLowerCase()}` : ""}`}
        className={`w-full inline-flex justify-center items-center px-6 py-3 rounded-full font-semibold transition-all duration-300 ${
          plan.popular 
            ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/25' 
            : plan.name === "Free"
            ? 'bg-zinc-800 hover:bg-zinc-700 text-white border border-white/10'
            : 'bg-zinc-100 text-zinc-900 hover:bg-white' 
        }`}
      >
        {plan.cta}
      </Link>
    </motion.div>
  );
};

export default function LandingPage() {
  const scrollRef = useRef<HTMLDivElement>(null);

  const isPaused = useRef(false);

  // Auto-scroll logic (Continuous "Earth Rotation")
  useEffect(() => {
    let animationFrameId: number;
    
    const scroll = () => {
      if (scrollRef.current && !isPaused.current) {
        const { scrollLeft, scrollWidth } = scrollRef.current;
        
        // Seamless infinite loop: Reset to 0 when we've scrolled past half the content
        if (scrollLeft >= scrollWidth / 2) {
             scrollRef.current.scrollLeft = 0;
        } else {
             scrollRef.current.scrollLeft += 0.5; // Slower, smoother rotation speed
        }
      }
      animationFrameId = requestAnimationFrame(scroll);
    };

    animationFrameId = requestAnimationFrame(scroll);

    return () => cancelAnimationFrame(animationFrameId);
  }, []);

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

  const plans = [
    {
      name: "Free",
      price: "0",
      description: "Perfect for personal projects and small experiments.",
      features: [
        "Up to 2 projects",
        "Up to 3 team members",
        "500 MB storage",
        "Basic analytics",
        "7-day task history"
      ],
      cta: "Start for Free"
    },
    {
      name: "Starter",
      originalPrice: "4.99",
      price: "2.99",
      description: "Great for small teams getting started.",
      badge: "40% OFF",
      badgeColor: "bg-red-500",
      features: [
        "Up to 5 projects",
        "Up to 5 team members",
        "2 GB storage",
        "Standard analytics",
        "30-day task history",
        "Read-only API access",
        "Email support"
      ],
      cta: "Start Free Trial"
    },
    {
      name: "Pro",
      originalPrice: "9.99",
      price: "6.99",
      description: "For growing teams that need more power.",
      popular: true,
      badge: "Popular",
      badgeColor: "bg-gradient-to-r from-purple-500 to-pink-500",
      features: [
        "Up to 15 projects",
        "Up to 15 team members",
        "10 GB storage",
        "Advanced analytics",
        "90-day task history",
        "Full API access",
        "Slack & Webhook integrations",
        "Priority support"
      ],
      cta: "Start Free Trial"
    },
    {
      name: "Enterprise",
      originalPrice: "24.99",
      price: "14.99",
      description: "Ultimate control and support for large organizations.",
      badge: "Best Value",
      badgeColor: "bg-gradient-to-r from-amber-500 to-orange-500",
      features: [
        "Unlimited projects",
        "Unlimited team members",
        "50 GB storage",
        "Custom reports",
        "Unlimited task history",
        "Full API + higher rate limit",
        "SSO integration",
        "Audit logs",
        "24/7 support"
      ],
      cta: "Start Free Trial"
    }
  ];

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-indigo-500/30">
      
      {/* Dynamic Background */}
      <div className="fixed inset-0 z-[-1]">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-500/20 rounded-full blur-[128px] mix-blend-screen animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[128px] mix-blend-screen animate-pulse delay-1000" />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-background/50 backdrop-blur-xl supports-[backdrop-filter]:bg-background/20">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tight hover:opacity-80 transition-opacity">
            <Image src="/icon.svg" alt="Insight Flow Logo" width={32} height={32} className="w-8 h-8 rounded-lg" />
            <span>Insight Flow</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <Link href="#features" className="hover:text-foreground transition-colors" scroll={true}>Features</Link>
            <Link href="#pricing" className="hover:text-foreground transition-colors" scroll={true}>Pricing</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link 
              href="/auth/login" 
              className="text-sm font-medium hover:text-indigo-400 transition-colors"
            >
              Log In
            </Link>
            <Link 
              href="/auth/register" 
              className="group px-5 py-2.5 bg-white text-black hover:bg-indigo-50 text-sm font-semibold rounded-full transition-all hover:shadow-[0_0_20px_-5px_rgba(255,255,255,0.5)] flex items-center gap-2"
            >
              Get Started
              <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </div>
      </nav>

      <main className="pt-32 pb-16 px-6">
        {/* Hero Section */}
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center mb-20 overflow-visible">
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="flex flex-col gap-6"
          >
            {/* Badge Removed */}

            
            <motion.h1 variants={itemVariants} className="text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.1]">
              Manage projects with <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
                Superhuman Speed
              </span>
            </motion.h1>
            
            <motion.p variants={itemVariants} className="text-lg text-muted-foreground leading-relaxed max-w-xl">
              Insight Flow is the intelligent workspace that adapts to your team. Streamline tasks, automate workflows, and gain real-time insights without the clutter.
            </motion.p>
            
            <motion.div variants={itemVariants} className="flex flex-wrap items-center gap-4 pt-2">
              <Link 
                href="/auth/register"
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
            
            <motion.div variants={itemVariants} className="pt-8 flex items-center gap-6 text-sm text-muted-foreground">
              <div className="flex -space-x-2">
                {[1, 2, 3, 4].map((i) => (
                  <motion.div 
                    key={i} 
                    custom={i}
                    initial={{ scale: 0 }}
                    animate={{ 
                      scale: 1, 
                      y: [0, -8, 0],
                      x: [0, i % 2 === 0 ? 3 : -3, 0] 
                    }}
                    whileHover={{ scale: 1.1, zIndex: 10 }}
                    whileTap={{ scale: 1.5, opacity: 0 }}
                    transition={{ 
                      scale: { duration: 0.5, type: "spring" },
                      y: { duration: 2 + (i * 0.5), repeat: Infinity, ease: "easeInOut", delay: i * 0.2 },
                      x: { duration: 2.5 + (i * 0.3), repeat: Infinity, ease: "easeInOut", delay: i * 0.1 }
                    }}
                    className={`w-8 h-8 rounded-full border-2 border-background bg-zinc-800 flex items-center justify-center text-[10px] text-white overflow-hidden relative z-0 cursor-pointer`}
                  >
                     <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${i * 123}`} alt="User" />
                  </motion.div>
                ))}
              </div>
              <div className="flex flex-col">
                 <div className="flex gap-1 text-amber-400">
                   {"★★★★★".split("").map((star, i) => <span key={i}>{star}</span>)}
                 </div>
                 <div className="flex items-center gap-1 font-medium">
                    <span>Trusted by</span>
                    <Counter value={10000} />
                    <span>+ teams</span>
                 </div>
              </div>
            </motion.div>
          </motion.div>

          {/* Hero Visual/Animation */}
          {/* Hero Visual - ULTIMATE Premium 3D Experience */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.5, delay: 0.2 }}
            className="relative lg:h-[650px] flex items-center justify-center overflow-visible"
          >
             {/* Scattered Dots */}
             <div className="absolute inset-0 z-0 overflow-visible">
                <ScatteredDots />
             </div>

             {/* Static Glowing Backdrop */}
             <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-[600px] h-[600px] bg-indigo-600/40 rounded-full blur-[150px]" />
                <div className="absolute w-[400px] h-[400px] bg-purple-500/30 rounded-full blur-[120px] translate-x-32" />
                <div className="absolute w-[300px] h-[300px] bg-cyan-500/20 rounded-full blur-[100px] -translate-x-40 translate-y-20" />
             </div>

             {/* Large Floating Orbs with Enhanced Visuals */}
             <motion.div 
               animate={{ y: [0, -40, 0], x: [0, 20, 0], rotate: [0, 180, 360] }}
               transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
               className="absolute -top-5 right-10 w-24 h-24 rounded-full bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 opacity-90 shadow-[0_0_60px_rgba(139,92,246,0.5)]"
             />
             <motion.div 
               animate={{ y: [0, 30, 0], x: [0, -15, 0] }}
               transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
               className="absolute bottom-20 -left-10 w-16 h-16 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 opacity-80 shadow-[0_0_40px_rgba(34,211,238,0.4)]"
             />
             <motion.div 
               animate={{ y: [0, -20, 0], scale: [1, 1.2, 1] }}
               transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
               className="absolute top-1/4 -left-20 w-10 h-10 rounded-full bg-gradient-to-br from-pink-400 to-rose-500 opacity-70 shadow-[0_0_30px_rgba(244,114,182,0.5)]"
             />
             <motion.div 
               animate={{ y: [0, 25, 0], x: [0, -10, 0] }}
               transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 2 }}
               className="absolute bottom-10 right-20 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 opacity-60 shadow-[0_0_25px_rgba(52,211,153,0.4)]"
             />

             {/* 3D Browser Mockup with Animated Border */}
             <motion.div
               initial={{ y: 60, opacity: 0, rotateX: 20, rotateY: -15 }}
               animate={{ y: 0, opacity: 1, rotateX: [10, 5, 10], rotateY: [-8, -3, -8] }}
               transition={{ 
                 y: { duration: 1, ease: "easeOut" },
                 opacity: { duration: 1 },
                 rotateX: { duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 },
                 rotateY: { duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }
               }}
               style={{ transformStyle: "preserve-3d", perspective: "1200px" }}
               className="relative w-full max-w-2xl mx-auto z-10"
             >
                {/* Flowing Light Border */}
                <div className="absolute -inset-[2px] rounded-[18px] overflow-hidden">
                   <motion.div 
                     animate={{ rotate: 360 }}
                     transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                     className="absolute inset-[-100%] bg-[conic-gradient(from_0deg,transparent_0%,transparent_40%,#818cf8_45%,#c084fc_50%,#f472b6_55%,transparent_60%,transparent_100%)]"
                   />
                </div>
                {/* Inner background to hide center */}
                <div className="absolute inset-0 rounded-[16px] bg-[#0a0a0f]" />
                
                {/* Browser Chrome */}
                <div className="relative rounded-2xl overflow-hidden shadow-[0_60px_120px_-20px_rgba(0,0,0,0.9),0_40px_80px_-30px_rgba(99,102,241,0.4)] border border-white/20 bg-[#0a0a0f]">
                   {/* Browser Header */}
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
                   
                   {/* Browser Content - Image Slideshow */}
                   <div className="relative aspect-[16/10] overflow-hidden">
                      <HeroImageSlideshow />
                   </div>
                </div>

                {/* Reflection */}
                <div className="absolute inset-x-4 -bottom-16 h-16 bg-gradient-to-b from-zinc-900/40 to-transparent blur-2xl opacity-60 transform scale-y-[-1] rounded-full" />
             </motion.div>

             {/* Enhanced Floating Notification Badges */}
             {/* Enhanced Floating Notification Badges - "WOW" Content */}
             <motion.div 
               initial={{ opacity: 0, x: 80, scale: 0.8 }}
               animate={{ opacity: 1, x: 0, scale: 1, y: [0, 12, 0] }}
               transition={{ 
                 opacity: { delay: 0.8, duration: 0.5 },
                 x: { delay: 0.8, duration: 0.6, type: "spring" },
                 scale: { delay: 0.8, duration: 0.5 },
                 y: { duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1.5 }
               }}
               className="absolute -right-24 top-1/3 w-60 p-5 bg-zinc-900/98 backdrop-blur-2xl rounded-2xl border border-white/15 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.8)] overflow-hidden z-20"
             >
                {/* Animated top border glow */}
                <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-400 to-transparent" />
                
                <div className="flex items-center gap-4 mb-2">
                   <motion.div 
                     animate={{ rotate: [0, 15, -15, 0] }}
                     transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                     className="p-2.5 bg-amber-500/20 rounded-xl text-amber-400 shadow-[0_0_20px_rgba(251,191,36,0.3)]"
                   >
                      <Zap size={20} fill="currentColor" />
                   </motion.div>
                   <div>
                      <div className="text-base font-bold text-white">System Optimized</div>
                      <div className="text-xs text-zinc-400">AI Auto-Scale</div>
                   </div>
                </div>
                <div className="flex items-center justify-between text-xs mt-2">
                   <span className="text-zinc-400">Performance</span>
                   <span className="text-green-400 font-bold">+400% 🚀</span>
                </div>
                {/* Mini Progress Bar */}
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
                 y: { duration: 6, repeat: Infinity, ease: "easeInOut", delay: 2 }
               }}
               className="absolute -left-24 bottom-1/3 w-56 p-5 bg-zinc-900/98 backdrop-blur-2xl rounded-2xl border border-white/15 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.8)] overflow-hidden z-20"
             >
                {/* Animated top border glow */}
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
                
                {/* Simulated Chart */}
                <div className="flex items-end justify-between h-8 mt-2 gap-1 px-1">
                   {[40, 65, 45, 80, 55, 90, 100].map((h, i) => (
                      <motion.div 
                        key={i}
                        initial={{ height: "10%" }}
                        animate={{ height: `${h}%` }}
                        transition={{ duration: 1, delay: 2 + (i * 0.1), type: "spring" }}
                        className="w-full bg-gradient-to-t from-emerald-900/50 to-emerald-400 rounded-t-sm opacity-80"
                      />
                   ))}
                </div>
             </motion.div>
          </motion.div>
        </div>


        {/* Features Carousel Section */}
        <div 
          id="features" 
          className="scroll-mt-20 py-20 overflow-hidden relative"
          onMouseDown={() => { isPaused.current = true; }}
          onMouseUp={() => { isPaused.current = false; }}
          onMouseLeave={() => { isPaused.current = false; }}
          onTouchStart={() => { isPaused.current = true; }}
          onTouchEnd={() => { isPaused.current = false; }}
        >
           {/* Aura Background Glow */}
           <div className="absolute inset-0 pointer-events-none overflow-hidden">
              <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/20 rounded-full blur-[150px]" />
              <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-purple-500/15 rounded-full blur-[130px]" />
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-cyan-500/10 rounded-full blur-[120px]" />
           </div>
           <div className="max-w-7xl mx-auto px-6 text-center mb-12">
              <h2 className="text-3xl md:text-5xl font-bold mb-6">Built for high-performance teams</h2>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                We've obsessed over every detail. Swipe to explore how we supercharge your workflow.
              </p>
           </div>
           
           <div 
             ref={scrollRef}
             className="flex overflow-hidden pb-12 gap-6 px-6 pointer-events-none select-none"
           >
             {/* Render double features for seamless infinite loop */}
             {[...features, ...features].map((feature, i) => (
               <FeatureCard key={i} feature={feature} index={i} />
             ))}
             {/* Padding element to allow scrolling to the end comfortably */}
             <div className="w-6 flex-shrink-0" />
           </div>
        </div>

        {/* Pricing Section */}
        <div id="pricing" className="scroll-mt-20 max-w-7xl mx-auto py-20 relative">
            {/* Aura Background Glow for Pricing */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
               <div className="absolute top-0 left-1/3 w-[500px] h-[500px] bg-amber-500/15 rounded-full blur-[140px]" />
               <div className="absolute top-1/2 right-0 -translate-y-1/2 w-[400px] h-[400px] bg-rose-500/12 rounded-full blur-[120px]" />
               <div className="absolute bottom-0 left-0 w-[450px] h-[350px] bg-emerald-500/10 rounded-full blur-[130px]" />
            </div>
            <div className="text-center mb-16">
               <h2 className="text-3xl md:text-5xl font-bold mb-4">Simple, transparent pricing</h2>
               <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                  Choose the plan that's right for your team. All plans include a 14-day free trial.
               </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
               {plans.map((plan, i) => (
                 <PricingCard key={i} plan={plan} index={i} />
               ))}
            </div>
        </div>

        {/* CTA Section Removed */}
      </main>

      <footer className="border-t border-white/10 py-12 bg-zinc-950">
         <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-3 gap-8">
            <div className="col-span-2">
               <div className="flex items-center gap-2 font-bold text-xl tracking-tight mb-4">
                  <Image src="/icon.svg" alt="Insight Flow Logo" width={24} height={24} className="w-6 h-6 rounded" />
                  Insight Flow
               </div>
               <p className="text-muted-foreground max-w-sm">
                 The all-in-one platform for modern engineering teams. Plan, track, and ship world-class software.
               </p>
            </div>
            <div className="md:text-right">
               <h4 className="font-semibold mb-4">Product</h4>
               <ul className="space-y-2 text-sm text-muted-foreground">
                  <li><a href="#features" className="hover:text-white">Features</a></li>
                  <li><a href="#pricing" className="hover:text-white">Pricing</a></li>
               </ul>
            </div>
         </div>
      </footer>
    </div>
  );
}
