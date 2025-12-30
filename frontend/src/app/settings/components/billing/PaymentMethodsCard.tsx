"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CreditCard, Plus, Loader2 } from "lucide-react";
import { PaymentMethodCard } from "@/components/billing/PaymentMethodCard";
import type { PaymentMethod } from "@/types";

interface PaymentMethodsCardProps {
  methods: PaymentMethod[];
  isLoading: boolean;
  setupLoading: boolean;
  onAddCard: () => void;
  onSetDefault: (id: string) => void;
  onDelete: (id: string) => void;
}

export function PaymentMethodsCard({
  methods,
  isLoading,
  setupLoading,
  onAddCard,
  onSetDefault,
  onDelete,
}: PaymentMethodsCardProps) {
  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-blue-500" />
            Payment Methods
          </CardTitle>
          <Button
            size="sm"
            onClick={onAddCard}
            disabled={setupLoading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {setupLoading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            Add Card
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            {[1].map((i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-lg border border-border bg-card">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-14 rounded" />
                  <div className="space-y-1">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                <Skeleton className="h-8 w-8 rounded mr-2" />
              </div>
            ))}
          </div>
        ) : methods.length === 0 ? (
          <div className="text-center py-8">
            <CreditCard className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
            <p className="text-muted-foreground">No cards added yet</p>
            <p className="text-sm text-muted-foreground/70 mt-1">
              Add a card to enable paid subscriptions
            </p>
          </div>
        ) : (
          methods.filter(Boolean).map((method) => (
            <PaymentMethodCard
              key={method.id}
              method={method}
              onSetDefault={onSetDefault}
              onDelete={onDelete}
              isLoading={isLoading}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}

export default PaymentMethodsCard;
