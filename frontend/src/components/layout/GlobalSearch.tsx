"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Search, Folder, CheckSquare, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { projectsApi, tasksApi } from "@/lib/api-endpoints";
import type { Project, Task } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

interface GlobalSearchProps {
  className?: string;
  onSelect?: () => void;
}

interface SearchResults {
  projects: Project[];
  tasks: Task[];
}

export function GlobalSearch({ className, onSelect }: GlobalSearchProps) {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(true); // Prevents browser autofill

  // Cache data to avoid re-fetching on every keystroke
  const [cachedData, setCachedData] = useState<{
    projects: Project[];
    tasks: Task[];
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Fetch data on focus if not already cached
  const handleFocus = async () => {
    if (query.trim()) {
      setIsOpen(true);
    }
    // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
    if (cachedData || loading || !isAuthenticated) {
      return;
    }

    setLoading(true);
    try {
      const [projectsData, tasksData] = await Promise.all([
        projectsApi.getProjects(0, 100),
        tasksApi.getTasks(0, 100),
      ]);

      // Normalize data to ensure we have arrays, handling both direct arrays and paginated responses
      const projects = Array.isArray(projectsData)
        ? projectsData
        : ((projectsData as Record<string, unknown>).items as Project[]) ?? [];
      const tasks = Array.isArray(tasksData)
        ? tasksData
        : ((tasksData as Record<string, unknown>).items as Task[]) ?? [];

      setCachedData({
        projects: Array.from(new Map(projects.map(p => [p.id, p])).values()),
        tasks: Array.from(new Map(tasks.map(t => [t.id, t])).values())
      });
    } catch (error) {
      console.error("Failed to load search data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Filter results based on query
  const results = useMemo<SearchResults>(() => {
    if (!query.trim() || !cachedData) {
      return { projects: [], tasks: [] };
    }

    const lowerQuery = query.toLowerCase();

    return {
      projects: cachedData.projects
        .filter(
          (p) =>
            p.name.toLowerCase().includes(lowerQuery) ||
            p.description?.toLowerCase().includes(lowerQuery),
        )
        .slice(0, 5),
      tasks: cachedData.tasks
        .filter(
          (t) =>
            t.title.toLowerCase().includes(lowerQuery) ||
            t.description?.toLowerCase().includes(lowerQuery),
        )
        .slice(0, 5),
    };
  }, [query, cachedData]);

  const handleSelectProject = (project: Project) => {
    setIsOpen(false);
    setQuery("");
    router.push(`/projects/${project.id}`);
    onSelect?.();
  };

  const handleSelectTask = (task: Task) => {
    setIsOpen(false);
    setQuery("");
    // Redirect to task details if possible, or specialized view
    if (task.projectId) {
      router.push(`/projects/${task.projectId}/tasks/${task.id}`);
    } else {
       // Fallback for tasks with no project (if any)
       router.push(`/projects?tab=tasks&search=${encodeURIComponent(task.title)}`);
    }
    onSelect?.();
  };

  const clearSearch = () => {
    setQuery("");
    setIsOpen(false);
  };

  return (
    <div
      className={cn("relative w-full md:w-80", className)}
      ref={containerRef}
    >
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={query}
        onChange={(e) => {
          const newValue = e.target.value;
          setQuery(newValue);
          setIsOpen(!!newValue.trim());
        }}
        onFocus={() => {
          setIsReadOnly(false);
          handleFocus();
        }}
        onBlur={() => {
          // Re-enable readonly when not focused to prevent future autofills
          if (!query) {
            setIsReadOnly(true);
          }
        }}
        readOnly={isReadOnly}
        placeholder="Search projects, tasks..."
        type="search"
        role="searchbox"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        name="global-search"
        id="global-search-input"
        aria-autocomplete="none"
        data-1p-ignore="true"
        data-lpignore="true"
        data-protonpass-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-dashlane-rid="disabled"
        className="h-10 rounded-full border-border bg-background pl-10 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:bg-background focus:ring-0 transition-all duration-200 [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden [&::-ms-clear]:hidden"
      />
      {query && (
        <button
          onClick={clearSearch}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" />
        </button>
      )}

      {/* Dropdown Results */}
      {isOpen && query && cachedData && (
        <div className="absolute top-full mt-2 w-full overflow-hidden rounded-xl border border-border bg-popover/80 p-2 shadow-xl backdrop-blur-xl backdrop-saturate-[1.8] animate-in fade-in zoom-in-95 duration-200 z-50">
          {results.projects.length === 0 && results.tasks.length === 0 ? (
            <div className="py-4 text-center text-sm text-muted-foreground">
              {query ? "No results found." : "Type to search..."}
            </div>
          ) : (
            <div className="space-y-2">
              {/* Projects Section */}
              {results.projects.length > 0 && (
                <div>
                  <div className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Projects
                  </div>
                  {results.projects.map((project) => (
                    <button
                      key={project.id}
                      onClick={() => handleSelectProject(project)}
                      className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-foreground hover:bg-accent transition-colors group cursor-pointer"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-500/10 text-indigo-500 group-hover:bg-indigo-500/20 transition-colors">
                        <Folder className="h-4 w-4" />
                      </div>
                      <span className="truncate flex-1">{project.name}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Tasks Section */}
              {results.projects.length > 0 && results.tasks.length > 0 && (
                <div className="my-1 border-t border-border" />
              )}

              {results.tasks.length > 0 && (
                <div>
                  <div className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Tasks
                  </div>
                  {results.tasks.map((task) => (
                    <button
                      key={task.id}
                      onClick={() => handleSelectTask(task)}
                      className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-foreground hover:bg-accent transition-colors group cursor-pointer"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-500 group-hover:bg-emerald-500/20 transition-colors">
                        <CheckSquare className="h-4 w-4" />
                      </div>
                      <div className="flex flex-col min-w-0 flex-1">
                        <span className="truncate">{task.title}</span>
                        {task.project && (
                          <span className="text-xs text-muted-foreground truncate">
                            {task.project.name}
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
