import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AnalyticsLoading from "@/app/analytics/loading";

vi.mock("@/components/layout/DashboardLayout", () => ({
  DashboardLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
}));

vi.mock("@/components/analytics/AnalyticsSkeletons", () => ({
  AnalyticsPageSkeleton: () => <div data-testid="analytics-page-skeleton" />,
}));

describe("AnalyticsLoading", () => {
  it("keeps dashboard shell around analytics route fallback", () => {
    render(<AnalyticsLoading />);

    expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();
    expect(screen.getByTestId("analytics-page-skeleton")).toBeInTheDocument();
  });
});
