import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Option {
    value: string;
    label: string;
    description?: string;
    color?: string; // Optional color for the label
}

interface CustomSelectProps {
    value: string;
    onChange: (value: string) => void;
    options: Option[];
    className?: string;
    size?: "default" | "sm" | "lg" | "icon";
    placeholder?: string;
}

export function CustomSelect({ value, onChange, options, className, size = "default", placeholder }: CustomSelectProps) {
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

    const selectedOption = options.find(opt => opt.value === value);
    const selectedLabel = selectedOption?.label || value || placeholder || "Select...";

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
                aria-haspopup="listbox"
                aria-expanded={isOpen}
                aria-label={placeholder || "Select option"}
                className={cn(
                    "flex items-center justify-between w-full rounded-lg glass border border-white/10 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50 cursor-pointer relative z-20",
                    sizeClasses[size],
                    size === "default" && "text-sm",
                )}
            >
                <span className={cn("truncate", selectedOption?.color)}>{selectedLabel}</span>
                <ChevronDown className={cn("ml-2 opacity-50 transition-transform", isOpen && "transform rotate-180", size === "sm" ? "h-3 w-3" : "h-4 w-4")} />
            </button>

            {isOpen && (
                <div className="absolute z-50 mt-1 w-full rounded-md border border-white/10 bg-zinc-900/95 backdrop-blur-xl shadow-xl animate-in fade-in zoom-in-95 duration-100">
                    <div className="py-1 max-h-60 overflow-auto custom-scrollbar" role="listbox">
                        {options.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                role="option"
                                aria-selected={value === option.value}
                                onClick={() => {
                                    onChange(option.value);
                                    setIsOpen(false);
                                }}
                                className={cn(
                                    "flex w-full flex-col items-start px-3 py-2 text-left transition-colors hover:bg-white/10 cursor-pointer",
                                    value === option.value ? "bg-indigo-600/30" : "",
                                )}
                            >
                                <span className={cn(
                                    "font-medium",
                                    size === "sm" ? "text-xs" : "text-sm",
                                    option.color || (value === option.value ? "text-indigo-200" : "text-zinc-200")
                                )}>
                                    {option.label}
                                </span>
                                {option.description && (
                                    <span className="text-xs text-zinc-500 mt-0.5">
                                        {option.description}
                                    </span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
