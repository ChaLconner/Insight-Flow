import { memo } from "react";
import { Button } from "@/components/ui/button";
import { Plus, LayoutGrid, ListTodo } from "lucide-react";

interface ProjectHeaderProps {
  activeTab: "projects" | "tasks";
  onTabChange: (tab: "projects" | "tasks") => void;
  onRefresh: () => void;
  onCreateProject: () => void;
  isRefetching: boolean;
}

export const ProjectHeader = memo(function ProjectHeader({
  activeTab,
  onTabChange,
  onRefresh: _onRefresh,
  onCreateProject,
  isRefetching: _isRefetching,
}: ProjectHeaderProps) {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            {activeTab === "projects" ? "Projects" : "My Tasks"}
          </h2>
          <p className="mt-1 text-muted-foreground">
            {activeTab === "projects"
              ? "Manage and organize your projects in one place."
              : "Manage and track all your tasks across projects."}
          </p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          {activeTab === "projects" && (
            <Button
              onClick={onCreateProject}
              className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 rounded-xl bg-secondary p-1 w-fit">
        <button type="button"
          onClick={() => onTabChange("projects")}
          className={`
            flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer
            ${
              activeTab === "projects"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }
          `}
        >
          <LayoutGrid className="h-4 w-4" />
          Projects
        </button>
        <button type="button"
          onClick={() => onTabChange("tasks")}
          className={`
            flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer
            ${
              activeTab === "tasks"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }
          `}
        >
          <ListTodo className="h-4 w-4" />
          My Tasks
        </button>
      </div>
    </div>
  );
});
