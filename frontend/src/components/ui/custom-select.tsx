import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Option {
    value: string;
    label: string;
}

interface CustomSelectProps {
    value: string;
    onChange: (value: string) => void;
    options: Option[];
    className?: string;
    size?: "default" | "sm" | "lg" | "icon";
}

export function CustomSelect({ value, onChange, options, className, size = "default" }: CustomSelectProps) {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const selectedLabel = options.find(opt => opt.value === value)?.label || value;

    const sizeClasses = {
        default: "h-9 px-3 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-8",
        icon: "h-9 w-9",
    };

    return (
        <div className={cn("relative min-w-[140px]", className)} ref={containerRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    "flex items-center justify-between w-full rounded-lg glass border border-white/10 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
                    sizeClasses[size],
                    size === "default" && "text-sm",
                )}
            >
                <span className="truncate">{selectedLabel}</span>
                <ChevronDown className={cn("ml-2 opacity-50 transition-transform", isOpen && "transform rotate-180", size === "sm" ? "h-3 w-3" : "h-4 w-4")} />
            </button>

            {isOpen && (
                <div className="absolute z-50 mt-1 w-full rounded-md border border-white/10 bg-zinc-950/90 backdrop-blur-xl shadow-xl animate-in fade-in zoom-in-95 duration-100">
                    <div className="py-1 max-h-60 overflow-auto custom-scrollbar">
                        {options.map((option) => (
                            <button
                                key={option.value}
                                onClick={() => {
                                    onChange(option.value);
                                    setIsOpen(false);
                                }}
                                className={cn(
                                    "flex w-full items-center px-3 py-2 text-zinc-300 hover:bg-white/10 hover:text-white transition-colors text-left",
                                    size === "sm" ? "text-xs" : "text-sm",
                                    value === option.value && "bg-indigo-500/20 text-indigo-300"
                                )}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
