"use client";

import { useTheme } from "@/hooks/use-theme";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Palette, Sun, Moon, Monitor, Check } from "lucide-react";

export function AppearanceSettings() {
  const { currentTheme, setTheme } = useTheme();

  const themes = [
    {
      id: "light",
      label: "Light",
      icon: Sun,
      description: "Clean and bright",
    },
    {
      id: "dark",
      label: "Dark",
      icon: Moon,
      description: "Easy on the eyes",
    },
    {
      id: "system",
      label: "System",
      icon: Monitor,
      description: "Syncs with device",
    },
  ] as const;

  return (
    <div className="space-y-6">
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Palette className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-foreground">Appearance</CardTitle>
              <CardDescription>
                Customize how Insight Flow limits looks on your device
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <Label className="text-foreground">Theme Preference</Label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {themes.map((theme) => {
                const isActive = currentTheme === theme.id;
                return (
                  <button
                    key={theme.id}
                    onClick={() => setTheme(theme.id)}
                    className={`
                      relative flex flex-col items-center justify-between p-4 rounded-xl border-2 transition-all duration-200 outline-none
                      ${
                        isActive
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-muted hover:border-muted-foreground/50 hover:bg-muted/50 bg-card"
                      }
                    `}
                  >
                    <div className="flex flex-col items-center gap-3 w-full pt-2">
                       {/* Preview Icon */}
                      <div className={`p-3 rounded-full ${isActive ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
                        <theme.icon className="h-6 w-6" />
                      </div>

                      <div className="text-center">
                        <div className={`font-medium ${isActive ? "text-primary" : "text-foreground"}`}>
                          {theme.label}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {theme.description}
                        </div>
                      </div>
                    </div>

                    {/* Active Checkmark */}
                    {isActive && (
                      <div className="absolute top-3 right-3 text-primary">
                        <Check className="h-4 w-4" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="rounded-lg bg-muted/50 p-4 border border-border">
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-full bg-background border border-border">
                <Sun className="h-4 w-4 text-foreground" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Theme Info</p>
                <p className="text-xs text-muted-foreground">
                  Light mode is now fully supported. Your preference will be saved automatically for this browser.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
