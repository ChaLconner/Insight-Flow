"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useClickOutside } from "@/hooks/use-click-outside";

interface PawMenuItem {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  className?: string;
}

interface CatPawMenuProps {
  trigger: React.ReactNode;
  items: PawMenuItem[];
  className?: string;
}

/**
 * CatPawMenu - A radial menu that expands with circular buttons
 * The trigger button opens up menu items that expand outward in an arc
 */
export function CatPawMenu({ trigger, items, className }: Readonly<CatPawMenuProps>) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const closeMenu = useCallback(() => setIsOpen(false), []);
  useClickOutside(containerRef, closeMenu, isOpen);

  // Calculate positions for menu items (arranged in an arc above the trigger)
  const getItemPosition = (index: number, total: number) => {
    const baseAngle = -90; // Start from top (-90 degrees)
    const spreadAngle = 70; // Total spread angle
    const startAngle = baseAngle - (spreadAngle * (total - 1)) / 2;
    const angleStep = total > 1 ? spreadAngle / (total - 1) : 0;
    const angle = startAngle + angleStep * index;
    
    const radius = 48; // Distance from center
    const x = Math.cos((angle * Math.PI) / 180) * radius;
    const y = Math.sin((angle * Math.PI) / 180) * radius;
    
    return { x, y };
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Trigger Button - matches other action buttons */}
      <motion.button
        className={cn(
          "relative z-10 h-8 px-3 rounded-md",
          "bg-transparent border border-border",
          "text-muted-foreground hover:text-foreground",
          "hover:bg-accent transition-colors",
          "flex items-center justify-center cursor-pointer",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        )}
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        whileTap={{ scale: 0.95 }}
        aria-label="More actions"
        aria-expanded={isOpen}
      >
        {trigger}
      </motion.button>

      {/* Menu Items (Circular Buttons) */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Invisible backdrop to catch clicks */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              className="fixed inset-0 z-0"
              onClick={() => setIsOpen(false)}
            />

            {items.map((item, index) => {
              const { x, y } = getItemPosition(index, items.length);
              
              return (
                <motion.button
                  key={`${item.label}-${item.className ?? ""}`}
                  initial={{ 
                    opacity: 0, 
                    scale: 0.8,
                    x: 0,
                    y: 0 
                  }}
                  animate={{ 
                    opacity: 1, 
                    scale: 1,
                    x: x,
                    y: y 
                  }}
                  exit={{ 
                    opacity: 0, 
                    scale: 0.8,
                    x: 0,
                    y: 0 
                  }}
                  transition={{
                    duration: 0.15,
                    ease: "easeOut",
                  }}
                  className={cn(
                    "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20",
                    "h-10 w-10 rounded-full",
                    "bg-background border border-border",
                    "flex items-center justify-center",
                    "shadow-lg",
                    "transition-all duration-100 cursor-pointer",
                    "hover:scale-110",
                    item.className
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    item.onClick();
                    setIsOpen(false);
                  }}
                  whileTap={{ scale: 0.9 }}
                  title={item.label}
                  aria-label={item.label}
                >
                  {item.icon}
                </motion.button>
              );
            })}
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
