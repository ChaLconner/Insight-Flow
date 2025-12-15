"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Search, ChevronDown, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
import { ProjectStatus } from "@/types";

interface ProjectFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  statusFilter: ProjectStatus | "all";
  onStatusFilterChange: (value: ProjectStatus | "all") => void;
  showFilters: boolean;
  onToggleFilters: () => void;
  sortBy: "newest" | "oldest" | "name";
  onSortChange: (value: "newest" | "oldest" | "name") => void;
  onClear: () => void;
}

export function ProjectFilters({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  showFilters,
  onToggleFilters,
  sortBy,
  onSortChange,
  onClear,
}: ProjectFiltersProps) {
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
            placeholder="Search projects..."
            aria-label="Search projects"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
          />
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
          />
          <Button
            variant="ghost"
            className={`glass border border-white/10 text-white hover:bg-white/10 hover:text-white cursor-pointer ${
              showFilters ? "bg-white/10 ring-1 ring-indigo-500/50" : ""
            }`}
            onClick={onToggleFilters}
          >
            <ChevronDown
              className={`h-4 w-4 mr-2 transition-transform ${showFilters ? "rotate-180" : ""}`}
            />
            More Filters
          </Button>
          {hasActiveFilters && (
            <Button
              variant="ghost"
              onClick={onClear}
              className="text-zinc-400 hover:text-white cursor-pointer"
            >
              <X className="h-4 w-4 mr-2" />
              Clear
            </Button>
          )}
        </div>
      </div>

      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-4 mb-6">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                <div className="space-y-1.5 flex-1">
                  <label className="text-xs font-medium text-zinc-400">
                    Sort By
                  </label>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onSortChange("newest")}
                      className={`text-xs cursor-pointer ${
                        sortBy === "newest"
                          ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                          : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      Newest
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onSortChange("oldest")}
                      className={`text-xs cursor-pointer ${
                        sortBy === "oldest"
                          ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                          : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      Oldest
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onSortChange("name")}
                      className={`text-xs cursor-pointer ${
                        sortBy === "name"
                          ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                          : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      Name
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
