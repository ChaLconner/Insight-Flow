"use client";

import { Suspense, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { useSearchParams, useRouter } from "next/navigation";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { User, Bell, Shield, Palette, Database, Loader2, Receipt } from "lucide-react";

// Direct import for LCP optimization (Profile is default tab)
import { ProfileSettings } from "./components/profile-settings";

// Dynamic imports for other tabs to reduce initial bundle size
const NotificationsSettings = dynamic(
  () =>
    import("./components/notifications-settings").then(
      (mod) => mod.NotificationsSettings,
    ),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-muted rounded-xl" />
    ),
  },
);
const SecuritySettings = dynamic(
  () =>
    import("./components/security-settings").then(
      (mod) => mod.SecuritySettings,
    ),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-muted rounded-xl" />
    ),
  },
);
const AppearanceSettings = dynamic(
  () =>
    import("./components/appearance-settings").then(
      (mod) => mod.AppearanceSettings,
    ),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-muted rounded-xl" />
    ),
  },
);
const BillingSettings = dynamic(
  () =>
    import("./components/billing-settings").then((mod) => mod.BillingSettings),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-muted rounded-xl" />
    ),
  },
);
const PaymentHistorySettings = dynamic(
  () =>
    import("./components/payment-history-settings").then((mod) => mod.PaymentHistorySettings),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-muted rounded-xl" />
    ),
  },
);

const VALID_TABS = ["profile", "notifications", "security", "appearance", "billing", "history"] as const;

type SettingsTab = (typeof VALID_TABS)[number];

const SETTINGS_TABS: Array<{
  id: SettingsTab;
  label: string;
  icon: typeof User;
}> = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: Shield },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "billing", label: "Billing", icon: Database },
  { id: "history", label: "Payment History", icon: Receipt },
];

function isSettingsTab(tab: string | null): tab is SettingsTab {
  return VALID_TABS.includes(tab as SettingsTab);
}

function SettingsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const activeTab = useMemo<SettingsTab>(() => {
    const tabFromUrl = searchParams.get("tab");
    if (isSettingsTab(tabFromUrl)) {
      return tabFromUrl;
    }
    return "profile";
  }, [searchParams]);

  // Update URL when tab changes
  const handleTabChange = useCallback((tab: SettingsTab) => {
    if (tab === activeTab) {
      return;
    }
    router.replace(`/settings?tab=${tab}`, { scroll: false });
  }, [activeTab, router]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">
            Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your account settings and preferences
          </p>
        </div>
      </div>

      <div className="flex flex-col lg:grid lg:gap-8 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <Card className="bg-card border-border lg:sticky lg:top-24 overflow-hidden">
            <CardContent className="p-2">
              <nav className="flex flex-row lg:flex-col gap-2 lg:gap-0 lg:space-y-1 overflow-x-auto pb-2 lg:pb-0 scrollbar-hide">
                {SETTINGS_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`flex-shrink-0 lg:flex-shrink lg:w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
                      activeTab === tab.id
                        ? "bg-primary text-primary-foreground shadow-md"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    }`}
                  >
                    <tab.icon className="h-4 w-4 flex-shrink-0" />
                    {tab.label}
                  </button>
                ))}
              </nav>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            {activeTab === "profile" && (
              <ProfileSettings />
            )}
            {activeTab === "notifications" && (
              <NotificationsSettings />
            )}
            {activeTab === "security" && (
              <SecuritySettings />
            )}
            {activeTab === "appearance" && (
              <AppearanceSettings />
            )}
            {activeTab === "billing" && <BillingSettings />}
            {activeTab === "history" && <PaymentHistorySettings />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedLayout>
      <Suspense fallback={
        <div className="flex items-center justify-center p-12">
           <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      }>
        <SettingsContent />
      </Suspense>
    </ProtectedLayout>
  );
}
