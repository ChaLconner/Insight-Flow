"use client";

import { useState, useRef, useMemo, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, Folder, CheckSquare, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { projectsApi, tasksApi } from "@/lib/api-endpoints";
import type { Project, Task } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";
import { useClickOutside } from "@/hooks/use-click-outside";

interface GlobalSearchProps {
  className?: string;
  onSelect?: () => void;
}

interface SearchResults {
  projects: Project[];
  tasks: Task[];
}

const SEARCH_DEBOUNCE_MS = 250;
const SEARCH_CACHE_TTL_MS = 30_000;
const SEARCH_CACHE_MAX_SIZE = 50;
const searchCache = new Map<
  string,
  { expiresAt: number; data: { projects: Project[]; tasks: Task[] } }
>();

// Evict expired entries to prevent unbounded memory growth
function evictExpiredSearchCache() {
  const now = Date.now();
  for (const [key, entry] of searchCache) {
    if (entry.expiresAt <= now) {
      searchCache.delete(key);
    }
  }
  // If still over limit after TTL eviction, remove oldest entries
  if (searchCache.size > SEARCH_CACHE_MAX_SIZE) {
    const keysToDelete = [...searchCache.keys()].slice(
      0,
      searchCache.size - SEARCH_CACHE_MAX_SIZE,
    );
    for (const key of keysToDelete) {
      searchCache.delete(key);
    }
  }
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
  const requestIdRef = useRef(0);

  const closeDropdown = useCallback(() => setIsOpen(false), []);
  useClickOutside(containerRef, closeDropdown);

  const handleFocus = () => {
    if (query.trim()) {
      setIsOpen(true);
    }
  };

  useEffect(() => {
    const trimmedQuery = query.trim();
    if (!isAuthenticated || trimmedQuery.length < 2) {
      requestIdRef.current += 1;
      setCachedData(null);
      setLoading(false);
      return;
    }

    const cacheKey = trimmedQuery.toLowerCase();
    const cached = searchCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) {
      setCachedData(cached.data);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    const timeoutId = window.setTimeout(async () => {
      setLoading(true);
      try {
        const [projectsData, tasksData] = await Promise.all([
          projectsApi.getProjects(0, 5, false, trimmedQuery),
          tasksApi.getMyTasks(0, 5, trimmedQuery),
        ]);

        if (cancelled || requestId !== requestIdRef.current) {
          return;
        }

        const projects = projectsData;
        const tasks = Array.isArray(tasksData) ? tasksData : tasksData.items;

        const data = {
          projects: Array.from(new Map(projects.map((p) => [p.id, p])).values()),
          tasks: Array.from(new Map(tasks.map((t) => [t.id, t])).values()),
        };

        evictExpiredSearchCache();
        searchCache.set(cacheKey, {
          data,
          expiresAt: Date.now() + SEARCH_CACHE_TTL_MS,
        });
        setCachedData(data);
      } catch (error) {
        if (!cancelled && requestId === requestIdRef.current) {
          console.error("Failed to load search data:", error);
          setCachedData({ projects: [], tasks: [] });
        }
      } finally {
        if (!cancelled && requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [query, isAuthenticated]);

  // Filter results based on query
  const results = useMemo<SearchResults>(() => {
    if (!query.trim() || !cachedData) {
      return { projects: [], tasks: [] };
    }

    return {
      projects: cachedData.projects.slice(0, 5),
      tasks: cachedData.tasks.slice(0, 5),
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
          setIsOpen(newValue.trim().length >= 2);
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
        aria-busy={loading}
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
