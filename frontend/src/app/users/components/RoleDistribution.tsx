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
  { key: "viewers", label: "Viewers", icon: User, color: "text-zinc-400" },
] as const;

export function RoleDistribution({ stats }: RoleDistributionProps) {
  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-white">
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
                className="flex items-center justify-between p-4 rounded-lg bg-white/5"
              >
                <div className="flex items-center gap-3">
                  <IconComponent
                    className={`h-5 w-5 ${item.color}`}
                    aria-hidden="true"
                  />
                  <span className="text-zinc-300">{item.label}</span>
                </div>
                <span className="text-white font-semibold">{count}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
