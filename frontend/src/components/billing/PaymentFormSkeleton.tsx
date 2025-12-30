"use client";

/**
 * PaymentFormSkeleton - Beautiful loading skeleton for payment form
 * Shows while Stripe Elements are loading or setup intent is being created
 */
export function PaymentFormSkeleton() {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Card Element Skeleton */}
      <div className="space-y-4">
        {/* Tabs skeleton */}
        <div className="flex gap-2">
          <div className="h-10 w-24 rounded-lg bg-accent/50 skeleton-pulse" />
          <div className="h-10 w-24 rounded-lg bg-accent/30 skeleton-pulse animation-delay-100" />
        </div>
        
        {/* Card number field */}
        <div className="space-y-2">
          <div className="h-4 w-24 rounded bg-accent/40 skeleton-pulse" />
          <div className="h-11 w-full rounded-lg bg-accent/30 skeleton-pulse animation-delay-200" />
        </div>
        
        {/* Expiry and CVC row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="h-4 w-20 rounded bg-accent/40 skeleton-pulse animation-delay-300" />
            <div className="h-11 w-full rounded-lg bg-accent/30 skeleton-pulse animation-delay-400" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-12 rounded bg-accent/40 skeleton-pulse animation-delay-300" />
            <div className="h-11 w-full rounded-lg bg-accent/30 skeleton-pulse animation-delay-400" />
          </div>
        </div>
        
        {/* Card name field */}
        <div className="space-y-2">
          <div className="h-4 w-20 rounded bg-accent/40 skeleton-pulse animation-delay-500" />
          <div className="h-11 w-full rounded-lg bg-accent/30 skeleton-pulse animation-delay-600" />
        </div>
        
        {/* Legal text skeleton */}
        <div className="pt-2 border-t border-border/50">
          <div className="h-3 w-full rounded bg-accent/20 skeleton-pulse animation-delay-700" />
          <div className="h-3 w-3/4 rounded bg-accent/20 mt-1 skeleton-pulse animation-delay-800" />
        </div>
      </div>

      {/* Action Buttons skeleton */}
      <div className="flex gap-3 pt-2">
        <div className="flex-1 h-10 rounded-md bg-accent/30 skeleton-pulse" />
        <div className="flex-1 h-10 rounded-md bg-primary/30 skeleton-pulse animation-delay-100" />
      </div>

      {/* Secure payment text */}
      <div className="flex items-center justify-center gap-1.5">
        <div className="h-3 w-3 rounded bg-accent/30 skeleton-pulse" />
        <div className="h-3 w-36 rounded bg-accent/20 skeleton-pulse animation-delay-200" />
      </div>

      <style jsx>{`
        .skeleton-pulse {
          animation: skeleton-pulse 1.5s ease-in-out infinite;
        }
        .animation-delay-100 {
          animation-delay: 0.1s;
        }
        .animation-delay-200 {
          animation-delay: 0.2s;
        }
        .animation-delay-300 {
          animation-delay: 0.3s;
        }
        .animation-delay-400 {
          animation-delay: 0.4s;
        }
        .animation-delay-500 {
          animation-delay: 0.5s;
        }
        .animation-delay-600 {
          animation-delay: 0.6s;
        }
        .animation-delay-700 {
          animation-delay: 0.7s;
        }
        .animation-delay-800 {
          animation-delay: 0.8s;
        }
        @keyframes skeleton-pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.4;
          }
        }
      `}</style>
    </div>
  );
}

export default PaymentFormSkeleton;
