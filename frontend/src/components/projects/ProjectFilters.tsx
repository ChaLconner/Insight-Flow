import { useId, forwardRef } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
import { ProjectStatus } from "@/types";

type ProjectStatusFilter = ProjectStatus | "all";
type ProjectSort = "newest" | "oldest" | "name";

interface ProjectFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  statusFilter: ProjectStatusFilter;
  onStatusFilterChange: (value: ProjectStatusFilter) => void;
  sortBy: ProjectSort;
  onSortChange: (value: ProjectSort) => void;
  onClear: () => void;
}

export const ProjectFilters = forwardRef<HTMLInputElement, ProjectFiltersProps>(
  (
    {
      searchQuery,
      onSearchChange,
      statusFilter,
      onStatusFilterChange,
      sortBy,
      onSortChange,
      onClear,
    },
    ref
  ) => {
    const id = useId();
    const hasActiveFilters =
      searchQuery || statusFilter !== "all" || sortBy !== "newest";

    return (
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400"
              aria-hidden="true"
            />
            <Input
              ref={ref}
              id={`${id}-search`}
              name={`project-search-${id}`}
              type="search"
              role="searchbox"
              placeholder="Search projects... (Press / to focus)"
              aria-label="Search projects"
              aria-describedby={`${id}-search-hint`}
              autoComplete="off"
              aria-autocomplete="none"
              data-1p-ignore="true"
              data-lpignore="true"
              data-protonpass-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 pr-10 bg-background border-border text-foreground placeholder:text-muted-foreground h-10"
            />
            <span id={`${id}-search-hint`} className="sr-only">
              Press forward slash key to focus this search field from anywhere on the page
            </span>
            {!searchQuery && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                <kbd
                  className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-xs text-muted-foreground bg-muted rounded border border-border"
                  aria-hidden="true"
                >
                  /
                </kbd>
              </div>
            )}
            {searchQuery && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                 <button
                    onClick={() => onSearchChange("")}
                    className="text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary rounded"
                    aria-label="Clear search"
                    type="button"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
              </div>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <CustomSelect
              value={statusFilter}
              onChange={(value) =>
                onStatusFilterChange(value as ProjectStatus | "all")
              }
              options={[
                { value: "all", label: "All Status" },
                { value: ProjectStatus.ACTIVE, label: "Active" },
                { value: ProjectStatus.ARCHIVED, label: "Archived" },
                { value: ProjectStatus.SUSPENDED, label: "Suspended" },
              ]}
              className="w-full sm:w-[140px]"
              triggerClassName="h-10"
            />
            <CustomSelect
              value={sortBy}
              onChange={(value) =>
                onSortChange(value as "newest" | "oldest" | "name")
              }
              options={[
                { value: "newest", label: "Newest" },
                { value: "oldest", label: "Oldest" },
                { value: "name", label: "Name" },
              ]}
              className="w-full sm:w-[140px]"
              triggerClassName="h-10"
            />
            {hasActiveFilters && (
              <Button
                variant="ghost"
                onClick={onClear}
                className="text-muted-foreground hover:text-foreground cursor-pointer h-10"
              >
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }
);
ProjectFilters.displayName = "ProjectFilters";
