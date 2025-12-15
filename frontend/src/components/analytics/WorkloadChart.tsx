"use client";

import React, { memo, useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  Users,
  SortAsc,
  SortDesc,
} from "lucide-react";
import type {
  TeamWorkloadPaginatedResponse,
  TeamWorkloadParams,
} from "@/app/analytics/types";

interface WorkloadChartProps {
  data: { name: string; avatar?: string; tasks: number }[];
  // New props for paginated mode
  usePagination?: boolean;
  paginatedData?: TeamWorkloadPaginatedResponse | null;
  onPageChange?: (params: TeamWorkloadParams) => void;
  isLoading?: boolean;
}

// Memoized tooltip styles
const TOOLTIP_CONTENT_STYLE = {
  backgroundColor: "rgba(24, 24, 27, 0.95)",
  borderColor: "rgba(139, 92, 246, 0.3)",
  color: "#fff",
  borderRadius: "12px",
  boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
  padding: "12px 16px",
} as const;

const WorkloadChartComponent: React.FC<WorkloadChartProps> = ({
  data = [],
  usePagination = false,
  paginatedData,
  onPageChange,
  isLoading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Trigger API call when params change
  useEffect(() => {
    if (usePagination && onPageChange) {
      onPageChange({
        page: currentPage,
        pageSize: 10,
        search: debouncedSearch || undefined,
        sortBy: "tasks",
        sortOrder: sortOrder,
      });
    }
  }, [usePagination, onPageChange, currentPage, debouncedSearch, sortOrder]);

  const handlePrevPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  }, []);

  const handleNextPage = useCallback(() => {
    if (paginatedData?.has_next) {
      setCurrentPage((prev) => prev + 1);
    }
  }, [paginatedData?.has_next]);

  const toggleSortOrder = useCallback(() => {
    setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));
    setCurrentPage(1); // Reset to first page on sort change
  }, []);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(e.target.value);
      setCurrentPage(1); // Reset to first page on search
    },
    [],
  );

  // Determine which data to display
  const displayData =
    usePagination && paginatedData ? paginatedData.items : data;

  const totalCount =
    usePagination && paginatedData ? paginatedData.total : data.length;

  // Empty state
  if (!displayData || displayData.length === 0) {
    return (
      <Card className="border-white/10 bg-white/5 backdrop-blur-sm h-full flex flex-col">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-violet-400" />
            Team Workload
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Users className="w-12 h-12 mx-auto text-zinc-600 mb-3" />
            <p className="text-zinc-500">No workload data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-violet-400" />
            Team Workload
            {totalCount > 0 && (
              <span className="text-sm font-normal text-zinc-400 ml-2">
                ({totalCount.toLocaleString()} members)
              </span>
            )}
          </CardTitle>

          {/* Controls for pagination mode */}
          {usePagination && (
            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <Input
                  type="text"
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={handleSearchChange}
                  className="pl-8 w-36 h-8 text-sm bg-white/5 border-white/10 text-white placeholder:text-zinc-500 focus:border-violet-500"
                />
              </div>

              {/* Sort Toggle */}
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSortOrder}
                className="h-8 px-2 text-zinc-400 hover:text-white hover:bg-white/10"
                title={
                  sortOrder === "desc"
                    ? "Sort: Highest First"
                    : "Sort: Lowest First"
                }
              >
                {sortOrder === "desc" ? (
                  <SortDesc className="w-4 h-4" />
                ) : (
                  <SortAsc className="w-4 h-4" />
                )}
              </Button>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col">
        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
            <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Chart */}
        <div className="flex-1 min-h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={displayData}
              margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                horizontal={false}
                stroke="rgba(255,255,255,0.1)"
              />
              <XAxis
                type="number"
                stroke="#a1a1aa"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => value.toLocaleString()}
              />
              <YAxis
                dataKey="name"
                type="category"
                stroke="#a1a1aa"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                width={80}
                tickFormatter={(value) =>
                  value.length > 12 ? `${value.substring(0, 12)}...` : value
                }
              />
              <Tooltip
                cursor={{ fill: "rgba(139, 92, 246, 0.1)" }}
                contentStyle={TOOLTIP_CONTENT_STYLE}
                itemStyle={{ color: "#fff" }}
                formatter={(value: number) => [value.toLocaleString(), "Tasks"]}
                labelFormatter={(label) => `👤 ${label}`}
              />
              <Bar dataKey="tasks" radius={[0, 6, 6, 0]}>
                {displayData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={`rgba(139, 92, 246, ${0.6 + (index < 3 ? (3 - index) * 0.13 : 0)})`}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pagination Controls */}
        {usePagination && paginatedData && paginatedData.total_pages > 1 && (
          <div className="flex items-center justify-between pt-4 mt-2 border-t border-white/10">
            <span className="text-sm text-zinc-400">
              Page {paginatedData.page} of{" "}
              {paginatedData.total_pages.toLocaleString()}
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePrevPage}
                disabled={!paginatedData.has_prev || isLoading}
                className="h-8 px-3 text-zinc-400 hover:text-white hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Prev
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={handleNextPage}
                disabled={!paginatedData.has_next || isLoading}
                className="h-8 px-3 text-zinc-400 hover:text-white hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* Info for large datasets */}
        {usePagination && paginatedData && paginatedData.total > 100 && (
          <p className="text-xs text-zinc-500 mt-2 text-center">
            💡 Use search to find specific team members
          </p>
        )}
      </CardContent>
    </Card>
  );
};

// Export with memo for performance optimization
export const WorkloadChart = memo(WorkloadChartComponent);
