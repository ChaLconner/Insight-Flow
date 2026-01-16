"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { useState, useEffect, useMemo } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useBillingData } from "@/hooks/useBillingData";

interface PlanData {
  id: string;
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

const PricingCard = ({ plan, index }: { plan: PlanData; index: number }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const getHref = () => {
    if (mounted && isAuthenticated) {
      return "/settings?tab=billing";
    }
    return `/auth/register${
      plan.name !== "Free" ? `?plan=${plan.name.toLowerCase()}` : ""
    }`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ delay: index * 0.15, duration: 0.5 }}
      className={`relative p-8 rounded-2xl border transition-all duration-300 flex flex-col ${
        plan.popular
          ? "border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/20"
          : "border-white/10 bg-zinc-900/50 hover:bg-zinc-900/80 hover:border-white/20"
      }`}
    >
      {plan.badge && (
        <div
          className={`absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide text-white ${
            plan.badgeColor ?? "bg-indigo-500"
          }`}
        >
          {plan.badge}
        </div>
      )}

      <div className="mb-8">
        <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
        <div className="flex items-baseline gap-1">
          {plan.originalPrice && (
            <span className="text-sm text-muted-foreground line-through decoration-red-500/50">
              ${plan.originalPrice}
            </span>
          )}
          <span className="text-4xl font-extrabold">${plan.price}</span>
          <span className="text-sm font-medium text-muted-foreground">/mo</span>
        </div>
        <p className="text-sm text-muted-foreground mt-4 leading-relaxed">
          {plan.description}
        </p>
      </div>

      <ul className="space-y-4 mb-8 flex-1">
        {plan.features.map((feature: string, i: number) => (
          <li key={i} className="flex items-center gap-3 text-sm text-zinc-300">
            <CheckCircle2
              size={18}
              className={`shrink-0 ${
                plan.popular ? "text-indigo-400" : "text-zinc-500"
              }`}
            />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <Link
        href={getHref()}
        className={`w-full inline-flex justify-center items-center px-6 py-3 rounded-full font-semibold transition-all duration-300 ${
          plan.popular
            ? "bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/25"
            : plan.name === "Free"
            ? "bg-zinc-800 hover:bg-zinc-700 text-white border border-white/10"
            : "bg-zinc-100 text-zinc-900 hover:bg-white"
        }`}
      >
        {plan.cta}
      </Link>
    </motion.div>
  );
};

export function PricingSection() {
  const { plans: fetchedPlans } = useBillingData({ silent: true });

  const plans = useMemo(() => {
    const staticPlans: PlanData[] = [
      {
        id: "free",
        name: "Free",
        price: "0",
        description: "Perfect for personal projects and small experiments.",
        features: [], // Will be populated from API
        cta: "Start for Free",
      },
      {
        id: "starter",
        name: "Starter",
        originalPrice: "4.99",
        price: "2.99",
        description: "Great for small teams getting started.",
        badge: "40% OFF",
        badgeColor: "bg-red-500",
        features: [],
        cta: "Start Free Trial",
      },
      {
        id: "pro",
        name: "Pro",
        originalPrice: "9.99",
        price: "6.99",
        description: "For growing teams that need more power.",
        popular: true,
        badge: "Popular",
        badgeColor: "bg-gradient-to-r from-purple-500 to-pink-500",
        features: [],
        cta: "Start Free Trial",
      },
      {
        id: "enterprise",
        name: "Enterprise",
        originalPrice: "24.99",
        price: "14.99",
        description: "Ultimate control and support for large organizations.",
        badge: "Best Value",
        badgeColor: "bg-gradient-to-r from-amber-500 to-orange-500",
        features: [],
        cta: "Start Free Trial",
      }
    ];

    // Merge API data if available
    if (Object.keys(fetchedPlans).length > 0) {
      return staticPlans.map(p => {
        const apiPlan = fetchedPlans[p.id];
        if (apiPlan) {
          return {
            ...p,
            price: apiPlan.price_monthly.toString(),
            originalPrice: apiPlan.original_price ? apiPlan.original_price.toString() : undefined,
            features: [
              `${apiPlan.project_limit > 1000 ? "Unlimited" : `Up to ${apiPlan.project_limit}`} projects`,
              `${apiPlan.member_limit > 1000 ? "Unlimited" : `Up to ${apiPlan.member_limit}`} team members`
            ],
          };
        }
        return p;
      });
    }

    // Fallback if API not loaded yet (use hardcoded features to avoid empty list)
    return [
      {
         ...staticPlans[0],
         features: ["Up to 2 projects", "Up to 3 team members"]
      },
      {
         ...staticPlans[1],
         features: ["Up to 5 projects", "Up to 5 team members"]
      },
      {
         ...staticPlans[2],
         features: ["Up to 15 projects", "Up to 15 team members"]
      },
      {
         ...staticPlans[3],
         features: ["Unlimited projects", "Unlimited team members"]
      }
    ];
  }, [fetchedPlans]);

  return (
    <div
      id="pricing"
      className="scroll-mt-20 max-w-7xl mx-auto py-20 relative"
    >
      {/* Aura Background Glow for Pricing */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/3 w-[500px] h-[500px] bg-amber-500/15 rounded-full blur-[140px]" />
        <div className="absolute top-1/2 right-0 -translate-y-1/2 w-[400px] h-[400px] bg-rose-500/12 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 left-0 w-[450px] h-[350px] bg-emerald-500/10 rounded-full blur-[130px]" />
      </div>
      <div className="text-center mb-16">
        <h2 className="text-3xl md:text-5xl font-bold mb-4">
          Simple, transparent pricing
        </h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Choose the plan that's right for your team. All plans include a
          14-day free trial.
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        {plans.map((plan, i) => (
          <PricingCard key={i} plan={plan} index={i} />
        ))}
      </div>
    </div>
  );
}
