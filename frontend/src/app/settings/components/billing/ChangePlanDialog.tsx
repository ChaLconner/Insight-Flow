"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RadioGroup, RadioGroupItem } from "@/components/ui";
import { Label } from "@/components/ui/label";
import { 
  Zap, CheckCircle2, Loader2, ArrowUp, ArrowDown, 
  TrendingUp, TrendingDown, AlertTriangle, CreditCard 
} from "lucide-react";
import type { PlanInfo, PaymentMethod } from "@/types";
import { apiClient } from "@/lib/api-client";
import { registerAuthenticatedCacheClearer } from "@/lib/auth-cache";
import { toast } from "sonner";

interface DowngradeWarning {
  type: string;
  message: string;
  action_required: string;
}

const DOWNGRADE_ELIGIBILITY_CACHE_TTL_MS = 30_000;
const DOWNGRADE_ELIGIBILITY_CACHE_MAX_ENTRIES = 8;
let downgradeEligibilityCacheGeneration = 0;

type DowngradeEligibilityCacheEntry = {
  canDowngrade: boolean;
  warnings: DowngradeWarning[];
  timestamp: number;
};

const downgradeEligibilityCache = new Map<string, DowngradeEligibilityCacheEntry>();

function pruneDowngradeEligibilityCache(): void {
  for (const [key, value] of downgradeEligibilityCache.entries()) {
    if (!hasFreshDowngradeEligibilityCache(value)) {
      downgradeEligibilityCache.delete(key);
    }
  }

  while (downgradeEligibilityCache.size > DOWNGRADE_ELIGIBILITY_CACHE_MAX_ENTRIES) {
    const oldestKey = downgradeEligibilityCache.keys().next().value;
    if (!oldestKey) {
      break;
    }
    downgradeEligibilityCache.delete(oldestKey);
  }
}

function getDowngradeEligibilityCacheKey(currentPlan: string, targetPlan: string): string {
  return `${currentPlan}:${targetPlan}`;
}

function hasFreshDowngradeEligibilityCache(entry: DowngradeEligibilityCacheEntry): boolean {
  return Date.now() - entry.timestamp < DOWNGRADE_ELIGIBILITY_CACHE_TTL_MS;
}

export function clearDowngradeEligibilityCache(): void {
  downgradeEligibilityCache.clear();
  downgradeEligibilityCacheGeneration += 1;
}

export function __clearDowngradeEligibilityCacheForTests(): void {
  clearDowngradeEligibilityCache();
}

registerAuthenticatedCacheClearer(clearDowngradeEligibilityCache);

interface ChangePlanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentPlan: string;
  planConfig: PlanInfo;
  plans: Record<string, PlanInfo>;
  plansLoading: boolean;
  methods: PaymentMethod[];
  selectedPaymentMethodId: string | null;
  onPaymentMethodChange: (id: string) => void;
  onAddCard: () => void;
  onConfirm: (planKey: string) => Promise<void>;
}

export function ChangePlanDialog({
  open,
  onOpenChange,
  currentPlan,
  planConfig,
  plans,
  plansLoading,
  methods,
  selectedPaymentMethodId,
  onPaymentMethodChange,
  onAddCard,
  onConfirm,
}: ChangePlanDialogProps) {
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [isUpdatingPlan, setIsUpdatingPlan] = useState(false);
  const [downgradeWarnings, setDowngradeWarnings] = useState<DowngradeWarning[]>([]);
  const [isCheckingDowngrade, setIsCheckingDowngrade] = useState(false);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedPlan(null);
      setDowngradeWarnings([]);
    }
  }, [open]);

  const handleSelectPlan = async (planKey: string) => {
    const planOrder = ['free', 'starter', 'pro', 'enterprise'];
    const currentIndex = planOrder.indexOf(currentPlan);
    const targetIndex = planOrder.indexOf(planKey);
    
    // If downgrading, check eligibility first
    if (targetIndex < currentIndex) {
      const cacheKey = getDowngradeEligibilityCacheKey(currentPlan, planKey);
      const cachedEligibility = downgradeEligibilityCache.get(cacheKey);

      if (cachedEligibility && hasFreshDowngradeEligibilityCache(cachedEligibility)) {
        setDowngradeWarnings(cachedEligibility.canDowngrade ? [] : cachedEligibility.warnings);
        setSelectedPlan(planKey);
        return;
      }

      setIsCheckingDowngrade(true);
      const cacheGeneration = downgradeEligibilityCacheGeneration;
      try {
        const { data } = await apiClient.get(`/payment/plans/check-downgrade/${planKey}`);
        if (cacheGeneration !== downgradeEligibilityCacheGeneration) {
          return;
        }
        downgradeEligibilityCache.set(cacheKey, {
          canDowngrade: Boolean(data.can_downgrade),
          warnings: data.warnings ?? [],
          timestamp: Date.now(),
        });
        pruneDowngradeEligibilityCache();
        if (!data.can_downgrade) {
          setDowngradeWarnings(data.warnings ?? []);
        } else {
          setDowngradeWarnings([]);
        }
      } catch {
        // Silently fail - user can still proceed
        setDowngradeWarnings([]);
      } finally {
        setIsCheckingDowngrade(false);
      }
    } else {
      setDowngradeWarnings([]);
    }
    
    setSelectedPlan(planKey);
  };

  const handleConfirmPlanChange = async (planKey: string) => {
    // Block if downgrade warnings exist
    if (downgradeWarnings.length > 0) {
      toast.error("Cannot downgrade", {
        description: "Please resolve the usage issues mentioned before downgrading.",
      });
      return;
    }
    
    if (planKey !== 'free' && methods.length === 0) {
      onOpenChange(false);
      setSelectedPlan(null);
      toast.info("Payment method required", {
        description: "Please add a payment card before upgrading to a paid plan.",
      });
      onAddCard();
      return;
    }

    setIsUpdatingPlan(true);
    try {
      await onConfirm(planKey);
      onOpenChange(false);
      setSelectedPlan(null);
      setDowngradeWarnings([]);
    } catch {
      // Error handled by parent via toast
    } finally {
      setIsUpdatingPlan(false);
    }
  };

  const planOrder = ['free', 'starter', 'pro', 'enterprise'];
  const currentIndex = planOrder.indexOf(currentPlan);
  const targetIndex = selectedPlan ? planOrder.indexOf(selectedPlan) : -1;
  const isUpgrade = targetIndex > currentIndex;
  const isDowngrade = targetIndex < currentIndex;

  return (
    <Dialog open={open} onOpenChange={(newOpen) => {
      if (!isUpdatingPlan) {
        onOpenChange(newOpen);
      }
    }}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-indigo-500" />
            {selectedPlan ? "Confirm Plan Change" : "Choose Your Plan"}
          </DialogTitle>
          {!selectedPlan && (
            <p className="text-sm text-muted-foreground mt-1">
              Select a plan that best fits your needs. You can upgrade or downgrade anytime.
            </p>
          )}
        </DialogHeader>
        
        {/* Plan Selection Grid */}
        {!selectedPlan && (
          <div className="grid gap-4 py-4 md:grid-cols-2">
            {plansLoading ? (
              [1, 2, 3, 4].map(i => <Skeleton key={i} className="h-64 rounded-xl" />)
            ) : Object.entries(plans).map(([key, plan]) => {
              const isActive = key === currentPlan;
              const targetIdx = planOrder.indexOf(key);
              const isPlanUpgrade = targetIdx > currentIndex;
              const isPlanDowngrade = targetIdx < currentIndex;
              const priceDiff = plan.price_monthly - planConfig.price_monthly;
              
              return (
                <div 
                  key={key} 
                  className={`
                    relative rounded-xl border p-4 cursor-pointer transition-all duration-200
                    ${isActive 
                      ? 'border-blue-500 bg-blue-500/5 ring-1 ring-blue-500 cursor-default' 
                      : 'border-border bg-card hover:border-primary/50 hover:shadow-md hover:scale-[1.02]'
                    }
                  `}
                  onClick={() => !isActive && handleSelectPlan(key)}
                >
                  {/* Badges */}
                  <div className="absolute -top-2 -right-2 flex gap-1">
                    {isActive && (
                      <Badge className="bg-blue-500 text-white hover:bg-blue-500 text-xs shadow-sm">
                        Current
                      </Badge>
                    )}
                    {!isActive && isPlanUpgrade && (
                      <Badge className="bg-emerald-500 text-white hover:bg-emerald-500 text-xs shadow-sm">
                        Upgrade
                      </Badge>
                    )}
                    {!isActive && isPlanDowngrade && (
                      <Badge className="bg-orange-500 text-white hover:bg-orange-500 text-xs shadow-sm">
                        Downgrade
                      </Badge>
                    )}
                    {plan.badge && !isActive && (
                      <Badge className={`text-white text-xs shadow-sm ${plan.badge_color ?? 'bg-red-500'}`}>
                        {plan.badge}
                      </Badge>
                    )}
                  </div>
                  
                  <div className="flex justify-between items-start mb-3">
                    <h4 className={`font-semibold text-lg ${plan.color}`}>{plan.name}</h4>
                    {isActive && <CheckCircle2 className="h-5 w-5 text-blue-500" />}
                  </div>
                  
                  <div className="mb-3">
                    {plan.original_price && plan.original_price > plan.price_monthly && (
                      <p className="text-sm text-muted-foreground line-through">
                        ${plan.original_price.toFixed(2)}/mo
                      </p>
                    )}
                    <p className="text-2xl font-bold text-foreground">
                      ${plan.price_monthly > 0 ? plan.price_monthly.toFixed(2) : 'Free'}
                      {plan.price_monthly > 0 && <span className="text-sm font-normal text-muted-foreground">/mo</span>}
                    </p>
                    {!isActive && priceDiff !== 0 && (
                      <p className={`text-xs mt-0.5 ${priceDiff > 0 ? 'text-orange-500' : 'text-emerald-500'}`}>
                        {priceDiff > 0 ? `+$${priceDiff.toFixed(2)}` : `-$${Math.abs(priceDiff).toFixed(2)}`} from current
                      </p>
                    )}
                    {plan.is_limited_offer && !isActive && (
                      <p className="text-xs text-red-500 font-medium mt-1 flex items-center gap-1">
                        <span className="inline-block w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></span>
                        Limited Time Offer
                      </p>
                    )}
                  </div>
                  
                  <ul className="text-sm text-muted-foreground space-y-1.5">
                    <li className="flex items-center gap-2">
                      <div className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-blue-500' : 'bg-muted-foreground/50'}`} />
                      {plan.project_limit > 1000 ? "Unlimited" : `Up to ${plan.project_limit}`} projects
                    </li>
                    <li className="flex items-center gap-2">
                      <div className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-blue-500' : 'bg-muted-foreground/50'}`} />
                      {plan.member_limit > 1000 ? "Unlimited" : `${plan.member_limit}`} team members
                    </li>
                  </ul>
                  
                  {!isActive && (
                    <Button 
                      variant={isPlanUpgrade ? "default" : "outline"}
                      size="sm" 
                      className={`w-full mt-4 ${isPlanUpgrade ? 'bg-primary hover:bg-primary/90' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectPlan(key);
                      }}
                    >
                      {isPlanUpgrade ? 'Upgrade' : isPlanDowngrade ? 'Downgrade' : 'Select'}
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        )}
        
        {/* Confirmation View */}
        {selectedPlan && (
          <ConfirmationView
            selectedPlan={selectedPlan}
            targetPlan={plans[selectedPlan]}
            currentPlan={currentPlan}
            planConfig={planConfig}
            isUpgrade={isUpgrade}
            isDowngrade={isDowngrade}
            downgradeWarnings={downgradeWarnings}
            methods={methods}
            selectedPaymentMethodId={selectedPaymentMethodId}
            onPaymentMethodChange={onPaymentMethodChange}
            onAddCard={onAddCard}
            onBack={() => {
              setSelectedPlan(null);
              setDowngradeWarnings([]);
            }}
            onConfirm={() => handleConfirmPlanChange(selectedPlan)}
            isUpdatingPlan={isUpdatingPlan}
            isCheckingDowngrade={isCheckingDowngrade}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

interface ConfirmationViewProps {
  selectedPlan: string;
  targetPlan: PlanInfo;
  currentPlan: string;
  planConfig: PlanInfo;
  isUpgrade: boolean;
  isDowngrade: boolean;
  downgradeWarnings: DowngradeWarning[];
  methods: PaymentMethod[];
  selectedPaymentMethodId: string | null;
  onPaymentMethodChange: (id: string) => void;
  onAddCard: () => void;
  onBack: () => void;
  onConfirm: () => void;
  isUpdatingPlan: boolean;
  isCheckingDowngrade: boolean;
}

function ConfirmationView({
  selectedPlan,
  targetPlan,
  planConfig,
  isUpgrade,
  isDowngrade,
  downgradeWarnings,
  methods,
  selectedPaymentMethodId,
  onPaymentMethodChange,
  onAddCard,
  onBack,
  onConfirm,
  isUpdatingPlan,
  isCheckingDowngrade,
}: ConfirmationViewProps) {
  if (!targetPlan) {return null;}

  const priceDiff = targetPlan.price_monthly - planConfig.price_monthly;

  return (
    <div className="py-4 space-y-6">
      {/* Plan Comparison */}
      <div className="flex items-center justify-center gap-4">
        <div className="text-center p-4 rounded-lg bg-muted/50 flex-1">
          <p className="text-xs text-muted-foreground mb-1">Current Plan</p>
          <p className={`font-semibold ${planConfig.color}`}>{planConfig.name}</p>
          <p className="text-lg font-bold">
            ${planConfig.price_monthly > 0 ? planConfig.price_monthly.toFixed(2) : '0'}
            <span className="text-xs font-normal">/mo</span>
          </p>
        </div>
        
        <div className={`p-2 rounded-full ${isUpgrade ? 'bg-emerald-500/10' : 'bg-orange-500/10'}`}>
          {isUpgrade ? (
            <ArrowUp className="h-5 w-5 text-emerald-500" />
          ) : (
            <ArrowDown className="h-5 w-5 text-orange-500" />
          )}
        </div>
        
        <div className="text-center p-4 rounded-lg bg-primary/5 border border-primary/20 flex-1">
          <p className="text-xs text-muted-foreground mb-1">New Plan</p>
          <p className={`font-semibold ${targetPlan.color}`}>{targetPlan.name}</p>
          {targetPlan.original_price && targetPlan.original_price > targetPlan.price_monthly && (
            <p className="text-xs text-muted-foreground line-through">
              ${targetPlan.original_price.toFixed(2)}/mo
            </p>
          )}
          <p className="text-lg font-bold">
            ${targetPlan.price_monthly > 0 ? targetPlan.price_monthly.toFixed(2) : '0'}
            <span className="text-xs font-normal">/mo</span>
          </p>
          {targetPlan.discount_percent > 0 && (
            <Badge className="bg-red-500 text-white hover:bg-red-500 text-xs mt-1">
              {targetPlan.discount_percent}% OFF
            </Badge>
          )}
        </div>
      </div>
      
      {/* Price Change Info */}
      <div className={`p-4 rounded-lg border ${isUpgrade ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-orange-500/5 border-orange-500/20'}`}>
        <div className="flex items-center gap-3">
          {isUpgrade ? (
            <TrendingUp className="h-5 w-5 text-emerald-500 flex-shrink-0" />
          ) : (
            <TrendingDown className="h-5 w-5 text-orange-500 flex-shrink-0" />
          )}
          <div>
            <p className={`font-medium ${isUpgrade ? 'text-emerald-600 dark:text-emerald-400' : 'text-orange-600 dark:text-orange-400'}`}>
              {isUpgrade ? 'Upgrade' : 'Downgrade'} to {targetPlan.name}
            </p>
            <p className="text-sm text-muted-foreground">
              {priceDiff > 0 
                ? `Your billing will increase by $${priceDiff.toFixed(2)}/month`
                : priceDiff < 0 
                  ? `You'll save $${Math.abs(priceDiff).toFixed(2)}/month`
                  : 'No change in billing'
              }
            </p>
          </div>
        </div>
      </div>
      
      {/* Downgrade Warning */}
      {isDowngrade && (
        <div className="p-4 rounded-lg bg-destructive/5 border border-destructive/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-destructive">
                {downgradeWarnings.length > 0 ? "Cannot Downgrade" : "Downgrade Warning"}
              </p>
              
              {downgradeWarnings.length > 0 ? (
                <div className="mt-2 space-y-3">
                  {downgradeWarnings.map((warning, idx) => (
                    <div key={idx} className="text-sm">
                      <p className="text-destructive font-medium">{warning.message}</p>
                      <p className="text-muted-foreground mt-1">{warning.action_required}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground mt-1">
                    Downgrading may affect your access to certain features:
                  </p>
                  <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                    {planConfig.project_limit > targetPlan.project_limit && (
                      <li>• Project limit will decrease from {planConfig.project_limit > 1000 ? 'unlimited' : planConfig.project_limit} to {targetPlan.project_limit}</li>
                    )}
                    {planConfig.member_limit > targetPlan.member_limit && (
                      <li>• Team member limit will decrease from {planConfig.member_limit > 1000 ? 'unlimited' : planConfig.member_limit} to {targetPlan.member_limit}</li>
                    )}
                  </ul>
                </>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* What's Included */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">What's included in {targetPlan.name}:</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            {targetPlan.project_limit > 1000 ? "Unlimited" : `Up to ${targetPlan.project_limit}`} projects
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            {targetPlan.member_limit > 1000 ? "Unlimited" : `${targetPlan.member_limit}`} team members
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            All {targetPlan.name} features
          </div>
        </div>
      </div>
      
      {/* Payment Method Selection */}
      {selectedPlan !== 'free' && (
        <PaymentMethodSelector
          methods={methods}
          selectedPaymentMethodId={selectedPaymentMethodId}
          onPaymentMethodChange={onPaymentMethodChange}
          onAddCard={onAddCard}
        />
      )}

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 mt-4">
        <Button 
          variant="outline" 
          onClick={onBack}
          disabled={isUpdatingPlan}
        >
          Back
        </Button>
        <Button 
          onClick={onConfirm}
          disabled={isUpdatingPlan || isCheckingDowngrade || downgradeWarnings.length > 0 || (selectedPlan !== 'free' && methods.length === 0)}
          className={`${isUpgrade ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-primary'}`}
        >
          {(isUpdatingPlan || isCheckingDowngrade) && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          {downgradeWarnings.length > 0 ? 'Cannot Proceed' : `Confirm ${isUpgrade ? 'Upgrade' : 'Downgrade'}`}
        </Button>
      </div>
    </div>
  );
}

interface PaymentMethodSelectorProps {
  methods: PaymentMethod[];
  selectedPaymentMethodId: string | null;
  onPaymentMethodChange: (id: string) => void;
  onAddCard: () => void;
}

function PaymentMethodSelector({
  methods,
  selectedPaymentMethodId,
  onPaymentMethodChange,
  onAddCard,
}: PaymentMethodSelectorProps) {
  return (
    <div className={`p-4 rounded-lg border ${methods.length > 0 ? 'bg-muted/50 border-border' : 'bg-amber-500/5 border-amber-500/20'}`}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-full ${methods.length > 0 ? 'bg-muted' : 'bg-amber-500/10'}`}>
          <CreditCard className={`h-5 w-5 ${methods.length > 0 ? 'text-muted-foreground' : 'text-amber-500'}`} />
        </div>
        <div className="flex-1">
          {methods.length > 0 ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-sm font-medium">Payment Method</p>
              </div>
              
              {methods.length > 1 ? (
                <RadioGroup 
                  value={selectedPaymentMethodId ?? ""} 
                  onValueChange={onPaymentMethodChange}
                  className="gap-2 mt-2"
                >
                  {methods.map(method => (
                    <div key={method.id} className="flex items-center space-x-2 border rounded-md p-2 hover:bg-muted/50 transition-colors">
                      <RadioGroupItem value={method.id} id={`r-${method.id}`} />
                      <Label htmlFor={`r-${method.id}`} className="flex-1 flex items-center justify-between cursor-pointer font-normal text-sm">
                        <div className="flex items-center gap-2">
                          <CreditCard className="h-4 w-4 text-muted-foreground" />
                          <span className="capitalize">{method.cardBrand} •••• {method.cardLast4}</span>
                        </div>
                        {method.isDefault && <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded border">Default</span>}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              ) : (
                <p className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                  <span className="capitalize">{methods[0]?.cardBrand}</span>
                  <span>•••• {methods[0]?.cardLast4}</span>
                  {methods[0]?.isDefault && <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded border">Default</span>}
                </p>
              )}
            </div>
          ) : (
            <>
              <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
                Payment method required
              </p>
              <Button 
                variant="link" 
                size="sm" 
                className="h-auto p-0 text-amber-600 dark:text-amber-400 underline"
                onClick={onAddCard}
              >
                Add a card now
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChangePlanDialog;
