import React, { memo } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, BarChart3 } from "lucide-react";
import type { AnalyticsProject } from "@/app/analytics/types";
import { getVelocityBadge } from "@/utils/analytics-helpers";

interface ProjectListProps {
  projects: AnalyticsProject[];
}

const ProjectListComponent: React.FC<ProjectListProps> = ({ projects }) => {
  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm flex flex-col h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold text-white">
          Project Performance
        </CardTitle>
        <Link href="/projects">
          <Button
            variant="ghost"
            size="sm"
            className="text-zinc-400 hover:text-white hover:bg-white/10 h-8 text-xs"
          >
            View All <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        {projects.length > 0 ? (
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {projects.map((project: AnalyticsProject, index: number) => (
              <Link
                key={index}
                href={`/projects/${project.id}`}
                className="block w-full"
              >
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-white">{project.name}</h4>
                      {getVelocityBadge(project.velocity)}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-zinc-400">
                      <span>
                        {project.completed}/{project.tasks} tasks
                      </span>
                      <span>{project.progress}% complete</span>
                    </div>
                    <div className="h-2 w-full bg-white/10 rounded-full mt-2">
                      <div
                        className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                        style={{ width: `${project.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-[200px] text-zinc-500">
            <BarChart3 className="h-12 w-12 mb-3 opacity-20" />
            <p>No active projects found</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Export with memo for performance optimization
export const ProjectList = memo(ProjectListComponent);
