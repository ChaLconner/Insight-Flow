"use client";

import { useEffect, useState, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { StripeProvider } from "@/components/providers/StripeProvider";
import { PaymentMethodForm } from "@/components/billing/PaymentMethodForm";
import { PaymentFormSkeleton } from "@/components/billing/PaymentFormSkeleton";
import { usePaymentMethods, useSetupIntent, useSubscription } from "@/hooks/usePayment";
import { useBillingData } from "@/hooks/useBillingData";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/auth-store";
import type { PlanInfo } from "@/types";
import { motion } from "framer-motion";

// Import refactored components
import { 
  CurrentPlanCard, 
  UsageLimitsCard, 
  PaymentMethodsCard, 
  ChangePlanDialog 
} from "./billing";

// Default plan fallback
const getDefaultPlan = (key: string): PlanInfo => ({
  plan: key as PlanInfo["plan"],
  name: key.charAt(0).toUpperCase() + key.slice(1), 
  price_monthly: 0, 
  price_yearly: 0,
  currency: "usd",
  features: [], 
  project_limit: 2,
  member_limit: 3,
  original_price: null, 
  discount_percent: 0, 
  color: "text-gray-500", 
  badge: null,
  badge_color: null,
  is_limited_offer: false,
});

export function BillingSettings() {
  const [isAddCardOpen, setIsAddCardOpen] = useState(false);
  const [isChangePlanOpen, setIsChangePlanOpen] = useState(false);
  const [isDialogReady, setIsDialogReady] = useState(false);
  const [selectedPaymentMethodId, setSelectedPaymentMethodId] = useState<string | null>(null);
  
  // Get user info for pre-filling form
  const { user } = useAuthStore();
  
  // Hooks
  const { methods, isLoading: methodsLoading, fetchMethods, setDefault, deleteMethod } = usePaymentMethods();
  const { subscription, isLoading: subLoading, fetchSubscription, cancelSubscription, updateSubscription, resumeSubscription } = useSubscription();
  const { setupIntent, isLoading: setupLoading, createSetupIntent, reset: resetSetupIntent, isPrefetched } = useSetupIntent();
  const { plans, usageStats, isLoading: billingDataLoading } = useBillingData();

  // Combined Loading State
  const isLoading = methodsLoading || subLoading || billingDataLoading;

  // Load data on mount
  useEffect(() => {
    fetchMethods();
    fetchSubscription();
  }, [fetchMethods, fetchSubscription]);

  // Update selected payment method when methods are loaded
  useEffect(() => {
    if (methods.length > 0 && !selectedPaymentMethodId) {
      const defaultMethod = methods.find(m => m.isDefault) ?? methods[0];
      setSelectedPaymentMethodId(defaultMethod.id);
    }
  }, [methods, selectedPaymentMethodId]);

  // Handle opening add card dialog
  const handleOpenAddCard = useCallback(async () => {
    setIsAddCardOpen(true);
    setIsDialogReady(false);
    
    if (isPrefetched && setupIntent) {
      setIsDialogReady(true);
      return;
    }
    
    const intent = await createSetupIntent();
    if (intent) {
      setIsDialogReady(true);
    } else {
      setIsAddCardOpen(false);
    }
  }, [isPrefetched, setupIntent, createSetupIntent]);

  const handleCardAdded = useCallback(async () => {
    setIsAddCardOpen(false);
    resetSetupIntent();
    await new Promise(resolve => setTimeout(resolve, 1000));
    await fetchMethods();
    
    toast.success("Card added successfully", {
      description: "Your payment card has been linked to your account.",
    });
  }, [resetSetupIntent, fetchMethods]);

  const handleCloseAddCardDialog = useCallback(() => {
    setIsAddCardOpen(false);
    setIsDialogReady(false);
    resetSetupIntent();
  }, [resetSetupIntent]);

  const handleConfirmPlanChange = useCallback(async (planKey: string) => {
    if (planKey === subscription?.plan) {
      return;
    }
    
    const paymentMethodId = planKey !== 'free' ? selectedPaymentMethodId : undefined;
    
    if (planKey !== 'free' && !paymentMethodId) {
      toast.error("No card selected", { description: "Please select a card to proceed." });
      return;
    }

    try {
      await updateSubscription(planKey, paymentMethodId ?? undefined);
      toast.success("Plan updated successfully");
      setIsChangePlanOpen(false);
      // Wait a bit before refreshing to allow backend to process
      setTimeout(() => fetchSubscription(), 1000);
    } catch {
       // Error usually handled by hook
       toast.error("Failed to update plan");
    }
  }, [subscription?.plan, selectedPaymentMethodId, updateSubscription, fetchSubscription]);

  // Resolve Current Plan Config
  const currentPlan = subscription?.plan ?? "free";
  const planConfig = plans[currentPlan] || getDefaultPlan("free");

  return (
    <div className="space-y-6">
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Current Plan */}
        <CurrentPlanCard
          subscription={subscription}
          planConfig={planConfig}
          isLoading={isLoading}
          onChangePlan={() => setIsChangePlanOpen(true)}
          onCancelSubscription={() => cancelSubscription(false)}
          onResumeSubscription={resumeSubscription}
        />
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        {/* Usage Limits */}
        <UsageLimitsCard
          usageStats={usageStats}
          planConfig={planConfig}
        />
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        {/* Payment Methods */}
        <PaymentMethodsCard
          methods={methods}
          isLoading={methodsLoading}
          setupLoading={setupLoading}
          onAddCard={handleOpenAddCard}
          onSetDefault={setDefault}
          onDelete={deleteMethod}
        />
      </motion.div>

      {/* Add Card Dialog */}
      <Dialog open={isAddCardOpen} onOpenChange={handleCloseAddCardDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Card</DialogTitle>
          </DialogHeader>
          {(!isDialogReady || !setupIntent) ? (
            <PaymentFormSkeleton />
          ) : (
            <StripeProvider options={{ clientSecret: setupIntent.client_secret }}>
              <PaymentMethodForm
                clientSecret={setupIntent.client_secret}
                customerId={setupIntent.customer_id}
                onSuccess={handleCardAdded}
                onCancel={handleCloseAddCardDialog}
                defaultName={user?.name ?? ""}
              />
            </StripeProvider>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Change Plan Dialog */}
      <ChangePlanDialog
        open={isChangePlanOpen}
        onOpenChange={setIsChangePlanOpen}
        currentPlan={currentPlan}
        planConfig={planConfig}
        plans={plans}
        plansLoading={billingDataLoading}
        methods={methods}
        selectedPaymentMethodId={selectedPaymentMethodId}
        onPaymentMethodChange={setSelectedPaymentMethodId}
        onAddCard={handleOpenAddCard}
        onConfirm={handleConfirmPlanChange}
      />
    </div>
  );
}

export default BillingSettings;
