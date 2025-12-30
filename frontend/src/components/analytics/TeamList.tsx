import React, { memo } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Activity,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from "lucide-react";
import type { AnalyticsTeamMember } from "@/app/analytics/types";
import { getAvatarUrl } from "@/lib/utils";

interface TeamListProps {
  team: AnalyticsTeamMember[];
}

const TeamListComponent: React.FC<TeamListProps> = ({ team }) => {
  return (
    <Card className="border-border bg-card flex flex-col h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold text-foreground">
          Team Performance
        </CardTitle>
        <Link href="/users">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground hover:bg-accent h-8 text-xs"
          >
            View All <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        {team.length > 0 ? (
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {team.map((member: AnalyticsTeamMember, index: number) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 rounded-lg bg-muted hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-secondary border border-border flex items-center justify-center overflow-hidden shrink-0 relative group">
                    {member.avatar ? (
                      <Image
                        src={getAvatarUrl(member.avatar)}
                        alt={member.name}
                        fill
                        className="object-cover"
                        sizes="40px"
                      />
                    ) : null}
                    <span
                      className={`${member.avatar ? "hidden" : ""} text-sm font-medium text-muted-foreground`}
                    >
                      {member.name && typeof member.name === "string"
                        ? member.name
                            .split(" ")
                            .map((n: string) => n[0])
                            .join("")
                        : ""}
                    </span>
                  </div>
                  <div>
                    <h4 className="font-medium text-foreground">{member.name}</h4>
                    <p className="text-sm text-muted-foreground">
                      {member.completed}/{member.tasks} tasks completed
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2">
                    <div className="text-lg font-semibold text-foreground">
                      {member.efficiency}%
                    </div>
                    {member.efficiency >= 85 ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : member.efficiency >= 70 ? (
                      <Clock className="h-4 w-4 text-amber-400" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
            <Activity className="h-12 w-12 mb-3 opacity-20" />
            <p>No team data available</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Export with memo for performance optimization
export const TeamList = memo(TeamListComponent);
