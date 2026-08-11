"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trash2, Star } from "lucide-react";
import type { PaymentMethod } from "@/types";

// Card brand logos/colors
const CARD_BRANDS: Record<string, { bg: string; text: string; label: string }> = {
  visa: { bg: "from-blue-600 to-blue-700", text: "VISA", label: "Visa" },
  mastercard: { bg: "from-red-500 to-orange-500", text: "MC", label: "Mastercard" },
  amex: { bg: "from-blue-400 to-blue-600", text: "AMEX", label: "American Express" },
  discover: { bg: "from-orange-500 to-orange-600", text: "DISC", label: "Discover" },
  diners: { bg: "from-gray-600 to-gray-700", text: "DC", label: "Diners Club" },
  jcb: { bg: "from-green-600 to-green-700", text: "JCB", label: "JCB" },
  unionpay: { bg: "from-red-600 to-red-700", text: "UP", label: "UnionPay" },
  unknown: { bg: "from-gray-500 to-gray-600", text: "CARD", label: "Card" },
};

interface PaymentMethodCardProps {
  method: PaymentMethod;
  onSetDefault?: (id: string) => void;
  onDelete?: (id: string) => void;
  isLoading?: boolean;
}

export function PaymentMethodCard({
  method,
  onSetDefault,
  onDelete,
  isLoading = false,
}: Readonly<PaymentMethodCardProps>) {
  // Early return if method is undefined or null
  if (!method) {
    return null;
  }

  const cardBrand = method.cardBrand ?? "unknown";
  const brand = CARD_BRANDS[cardBrand.toLowerCase()] ?? CARD_BRANDS.unknown;
  const cardLast4 = method.cardLast4 ?? "****";
  const cardExpMonth = method.cardExpMonth ?? 1;
  const cardExpYear = method.cardExpYear ?? 2030;

  return (
    <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-accent/10 hover:bg-accent/20 transition-all duration-300 hover:shadow-md hover:scale-[1.01]">
      <div className="flex items-center gap-4">
        {/* Card Brand Visual */}
        <div
          className={`h-10 w-14 bg-gradient-to-br ${brand.bg} rounded-lg flex flex-col items-center justify-center text-white shadow-md relative overflow-hidden`}
        >
          <span className="text-[10px] font-bold tracking-tighter">
            {brand.text}
          </span>
          <div className="absolute right-[-10px] bottom-[-10px] h-12 w-12 bg-white/10 rounded-full" />
        </div>

        {/* Card Details */}
        <div>
          <div className="flex items-center gap-2">
            <p className="text-foreground font-semibold">
              •••• •••• •••• {cardLast4}
            </p>
            {method.isDefault && (
              <Badge className="bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30 border-none text-xs">
                Default
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground text-xs font-medium">
            {brand.label} • Expires {String(cardExpMonth).padStart(2, "0")}/{String(cardExpYear).slice(-2)}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {!method.isDefault && onSetDefault && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSetDefault(method.id)}
            disabled={isLoading}
            className="text-muted-foreground hover:text-foreground"
            title="Set as default"
          >
            <Star className="h-4 w-4" />
          </Button>
        )}
        {onDelete && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(method.id)}
            disabled={isLoading}
            className="text-muted-foreground hover:text-destructive disabled:opacity-50"
            title="Delete card"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}

export default PaymentMethodCard;
