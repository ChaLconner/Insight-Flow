"use client";

import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface UserPaginationProps {
  page: number;
  pageSize: number;
  totalUsers: number;
  currentCount: number;
  hasMore: boolean;
  isLoading: boolean;
  onPageChange: (page: number) => void;
}

export function UserPagination({
  page,
  pageSize,
  totalUsers,
  currentCount,
  hasMore,
  isLoading,
  onPageChange,
}: UserPaginationProps) {
  const startIndex = (page - 1) * pageSize + 1;
  const endIndex = startIndex + currentCount - 1;

  return (
    <div className="flex items-center justify-between p-4 border-t border-border">
      <div className="text-sm text-muted-foreground">
        {totalUsers > 0 ? (
          <>
            Showing{" "}
            <span className="font-medium text-foreground">
              {startIndex}-{endIndex}
            </span>{" "}
            of <span className="font-medium text-foreground">{totalUsers}</span>{" "}
            users
          </>
        ) : (
          `Page ${page}`
        )}
      </div>
      <div
        className="flex items-center gap-2"
        role="navigation"
        aria-label="Pagination"
      >
        <Button
          variant="outline"
          size="sm"
          className="border-border text-foreground hover:bg-accent disabled:opacity-50"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1 || isLoading}
          aria-label="Go to previous page"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </Button>
        <span className="text-sm text-muted-foreground px-2">Page {page}</span>
        <Button
          variant="outline"
          size="sm"
          className="border-border text-foreground hover:bg-accent disabled:opacity-50"
          onClick={() => onPageChange(page + 1)}
          disabled={!hasMore || isLoading}
          aria-label="Go to next page"
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
