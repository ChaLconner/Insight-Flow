"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Palette, Sun, Moon, Monitor } from "lucide-react";

interface AppearanceSettingsProps {
    theme: string;
    setTheme: (theme: string) => void;
}

export function AppearanceSettings({ theme, setTheme }: AppearanceSettingsProps) {
    return (
        <div className="space-y-6">
            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                        <Palette className="h-5 w-5" />
                        Theme
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                            { id: 'light', label: 'Light', icon: Sun, color: 'bg-zinc-100' },
                            { id: 'dark', label: 'Dark', icon: Moon, color: 'bg-zinc-900' },
                            { id: 'system', label: 'Auto', icon: Monitor, color: 'bg-gradient-to-br from-zinc-100 to-zinc-900' },
                        ].map((option) => (
                            <div
                                key={option.id}
                                onClick={() => setTheme(option.id)}
                                className={`group relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-300 ${theme === option.id
                                    ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/10'
                                    : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                                    }`}
                            >
                                <div className={`h-16 w-full rounded-lg mb-3 ${option.color} opacity-80 group-hover:opacity-100 transition-opacity`} />
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <option.icon className={`h-4 w-4 ${theme === option.id ? 'text-indigo-400' : 'text-zinc-400 group-hover:text-white'}`} />
                                        <span className={`font-medium ${theme === option.id ? 'text-white' : 'text-zinc-400 group-hover:text-white'}`}>
                                            {option.label}
                                        </span>
                                    </div>
                                    {theme === option.id && (
                                        <div className="h-2 w-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
