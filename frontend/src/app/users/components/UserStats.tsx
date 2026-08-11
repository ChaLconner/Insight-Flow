"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users as UsersIcon, UserCheck, MailIcon, Shield } from "lucide-react";

interface UserStatsProps {
  stats: {
    total: number;
    active: number;
    verified: number;
    admins: number;
    managers: number;
    members: number;
    viewers: number;
  };
}

export function UserStats({ stats }: Readonly<UserStatsProps>) {
  const activePercentage =
    stats.total > 0 ? Math.round((stats.active / stats.total) * 100) : 0;
  const verifiedPercentage =
    stats.total > 0 ? Math.round((stats.verified / stats.total) * 100) : 0;

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Card className="border-border bg-card backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Users
          </CardTitle>
          <UsersIcon className="h-4 w-4 text-blue-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">{stats.total}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {stats.active} active members
          </p>
        </CardContent>
      </Card>

      <Card className="border-border bg-card backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Active Users
          </CardTitle>
          <UserCheck className="h-4 w-4 text-emerald-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">{stats.active}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {activePercentage}% of total
          </p>
        </CardContent>
      </Card>

      <Card className="border-border bg-card backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Verified Email
          </CardTitle>
          <MailIcon className="h-4 w-4 text-amber-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">{stats.verified}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {verifiedPercentage}% verified
          </p>
        </CardContent>
      </Card>

      <Card className="border-border bg-card backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Admins
          </CardTitle>
          <Shield className="h-4 w-4 text-purple-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">{stats.admins}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {stats.managers} managers total
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
