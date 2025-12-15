import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        success:
          "border-transparent bg-green-500 text-white hover:bg-green-500/80",
        warning:
          "border-transparent bg-yellow-500 text-white hover:bg-yellow-500/80",
        error: "border-transparent bg-red-500 text-white hover:bg-red-500/80",
        // Glassmorphism variants
        glass: "glass text-foreground border-white/30 backdrop-blur-sm",
        "glass-primary":
          "backdrop-blur-lg bg-blue-500/20 text-blue-600 border-blue-500/30",
        "glass-success":
          "backdrop-blur-lg bg-green-500/20 text-green-600 border-green-500/30",
        "glass-warning":
          "backdrop-blur-lg bg-yellow-500/20 text-yellow-600 border-yellow-500/30",
        "glass-error":
          "backdrop-blur-lg bg-red-500/20 text-red-600 border-red-500/30",
        "glass-secondary":
          "backdrop-blur-lg bg-gray-500/20 text-gray-600 border-gray-500/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends
    React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
