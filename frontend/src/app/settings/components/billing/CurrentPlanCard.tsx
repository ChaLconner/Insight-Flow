"use client";

import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Zap, CheckCircle2 } from "lucide-react";
import type { PlanInfo, Subscription } from "@/types";

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  "active": { label: "Active", className: "bg-emerald-500/20 text-emerald-500" },
  "canceled": { label: "Canceled", className: "bg-red-500/20 text-red-500" },
  "past_due": { label: "Past Due", className: "bg-orange-500/20 text-orange-500" },
  "trialing": { label: "Trial", className: "bg-blue-500/20 text-blue-500" },
  "unpaid": { label: "Unpaid", className: "bg-red-500/20 text-red-500" },
  "incomplete": { label: "Incomplete", className: "bg-yellow-500/20 text-yellow-500" },
};

interface CurrentPlanCardProps {
  subscription: Subscription | null;
  planConfig: PlanInfo;
  isLoading: boolean;
  onChangePlan: () => void;
  onCancelSubscription: () => void;
  onResumeSubscription: () => void;
}

export function CurrentPlanCard({
  subscription,
  planConfig,
  isLoading,
  onChangePlan,
  onCancelSubscription,
  onResumeSubscription,
}: CurrentPlanCardProps) {
  const statusConfig = subscription?.status 
    ? STATUS_BADGE[subscription.status] 
    : STATUS_BADGE["active"];

  // Helper to extract color name safely
  const getColorName = (colorClass: string) => {
    const parts = colorClass.split('-');
    return parts.length > 1 ? parts[1] : 'gray';
  };

  const themeColor = getColorName(planConfig.color);

  return (
    <Card className={`border-border bg-card relative overflow-hidden transition-all duration-300 hover:shadow-lg border-l-4`} style={{ borderLeftColor: `var(--${themeColor}-500, currentColor)` }}>
      {/* Background Gradient Effect - using inline style for safety or standardized classes */}
      <div className={`absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-primary/5 to-transparent rounded-bl-full pointer-events-none opacity-50`} />

      <CardHeader>
        <div className="flex items-center gap-3 relative z-10">
          <div className={`p-2 rounded-lg bg-emerald-500/10 ${planConfig.color}`}>
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-foreground">Current Plan</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your subscription and billing cycle
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 relative z-10">
        {isLoading ? (
          <div className="flex items-center justify-between p-6 rounded-xl bg-accent/20 border border-border">
            <div className="space-y-3 w-full">
              <div className="flex items-center gap-2">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-6 w-20 rounded-full" />
              </div>
              <div className="flex items-baseline gap-2">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-4 w-24" />
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Skeleton className="h-4 w-4 rounded-full" />
                <Skeleton className="h-4 w-40" />
              </div>
            </div>
            <div className="hidden sm:block">
              <Skeleton className="h-16 w-16 rounded-full" />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between p-6 rounded-xl bg-accent/20 border border-border backdrop-blur-sm">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className={`text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-foreground to-muted-foreground ${planConfig.color}`}>
                  {planConfig.name}
                </h3>
                <Badge className={`${statusConfig.className} hover:${statusConfig.className} border-none shadow-sm`}>
                  {statusConfig.label}
                </Badge>
                {planConfig.discount_percent > 0 && (
                  <Badge className="bg-red-500 text-white hover:bg-red-500 text-xs animate-pulse">
                    {planConfig.discount_percent}% OFF
                  </Badge>
                )}
              </div>
              <div className="flex items-baseline gap-2 mt-2">
                {planConfig.original_price && planConfig.original_price > planConfig.price_monthly && (
                  <span className="text-muted-foreground line-through text-md">
                    ${planConfig.original_price.toFixed(2)}
                  </span>
                )}
                <span className="text-3xl font-bold tracking-tight">
                  {planConfig.price_monthly > 0 ? `$${planConfig.price_monthly.toFixed(2)}` : 'Free'}
                  <span className="text-lg font-normal text-muted-foreground ml-1">/mo</span>
                </span>
              </div>
              {subscription?.currentPeriodEnd && (
                <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground bg-background/50 py-1 px-3 rounded-full w-fit">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>
                    {subscription.cancelAtPeriodEnd ? "Cancels on: " : "Next billing: "}
                    {new Date(subscription.currentPeriodEnd).toLocaleDateString('en-GB')}
                  </span>
                </div>
              )}
            </div>
            <div className="hidden sm:block">
              <div className={`p-4 rounded-full bg-background/80 shadow-lg border backdrop-blur-md ${planConfig.color.replace("text-", "border-")}/20`}>
                <Zap className={`h-8 w-8 ${planConfig.color}`} />
              </div>
            </div>
          </div>
        )}
      </CardContent>
      <CardFooter className="border-t border-border pt-6 flex gap-3 bg-accent/5 relative z-10">
        <Button 
          variant="outline" 
          className="border-border hover:bg-accent hover:shadow-sm transition-all"
          onClick={onChangePlan}
          disabled={isLoading}
        >
          Change Plan
        </Button>
        {subscription && subscription.plan !== "free" && !subscription.cancelAtPeriodEnd && (
          <Button 
            variant="ghost" 
            className="text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
            onClick={onCancelSubscription}
          >
            Cancel Subscription
          </Button>
        )}
        {subscription && subscription.plan !== "free" && subscription.cancelAtPeriodEnd && (
          <Button 
            variant="outline" 
            className="text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 hover:border-emerald-300 transition-colors"
            onClick={onResumeSubscription}
          >
            Turn on Auto-renew
          </Button>
        )}
      </CardFooter>
      
      {/* Explicit Auto-Renew Status Indicator */}
      {subscription && subscription.plan !== "free" && (
        <div className="absolute top-4 right-4 z-20">
           <Badge variant={subscription.cancelAtPeriodEnd ? "destructive" : "outline"} className={`
             ${subscription.cancelAtPeriodEnd 
               ? "bg-red-500/10 text-red-500 border-red-500/20" 
               : "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"}
             backdrop-blur-md
           `}>
             {subscription.cancelAtPeriodEnd ? "Auto-renew: OFF" : "Auto-renew: ON"}
           </Badge>
        </div>
      )}
    </Card>
  );
}

export default CurrentPlanCard;
