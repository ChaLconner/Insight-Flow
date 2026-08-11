"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Crown, Shield, User } from "lucide-react";

interface RoleDistributionProps {
  stats: {
    admins: number;
    managers: number;
    members: number;
    viewers: number;
  };
}

const ROLE_ITEMS = [
  { key: "admins", label: "Admins", icon: Crown, color: "text-purple-400" },
  { key: "managers", label: "Managers", icon: Shield, color: "text-blue-400" },
  { key: "members", label: "Members", icon: User, color: "text-emerald-400" },
  { key: "viewers", label: "Viewers", icon: User, color: "text-muted-foreground" },
] as const;

export function RoleDistribution({ stats }: Readonly<RoleDistributionProps>) {
  return (
    <Card className="border-border bg-card backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-foreground">
          Role Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {ROLE_ITEMS.map((item) => {
            const IconComponent = item.icon;
            const count = stats[item.key];

            return (
              <div
                key={item.key}
                className="flex items-center justify-between p-4 rounded-lg bg-input/20"
              >
                <div className="flex items-center gap-3">
                  <IconComponent
                    className={`h-5 w-5 ${item.color}`}
                    aria-hidden="true"
                  />
                  <span className="text-muted-foreground">{item.label}</span>
                </div>
                <span className="text-foreground font-semibold">{count}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
