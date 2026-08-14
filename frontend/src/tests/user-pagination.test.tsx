import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UserPagination } from "@/app/users/components/UserPagination";

describe("UserPagination", () => {
  it("shows the global total for an unfiltered list", () => {
    render(
      <UserPagination
        page={1}
        pageSize={10}
        totalUsers={21}
        currentCount={10}
        hasMore
        isLoading={false}
        onPageChange={vi.fn()}
      />,
    );

    expect(screen.getByText("21")).toBeInTheDocument();
    expect(screen.getByText("1-10")).toBeInTheDocument();
  });

  it("does not display the unfiltered total for filtered results", () => {
    render(
      <UserPagination
        page={1}
        pageSize={10}
        totalUsers={21}
        currentCount={2}
        hasMore={false}
        isLoading={false}
        isFiltered
        onPageChange={vi.fn()}
      />,
    );

    expect(screen.getByText("1-2")).toBeInTheDocument();
    expect(screen.queryByText("21")).not.toBeInTheDocument();
  });
});
