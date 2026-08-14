"use client";

import type { ReactNode } from "react";
import { useElementOnScreen } from "@/hooks/use-element-on-screen";

interface ScrollRevealProps {
  children: ReactNode;
  className: string;
}

export function ScrollReveal({ children, className }: Readonly<ScrollRevealProps>) {
  const [ref, isVisible] = useElementOnScreen({ threshold: 0.1 });

  return (
    <div
      ref={ref}
      className={`${className} duration-700 transition-all ${
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"
      }`}
    >
      {children}
    </div>
  );
}
