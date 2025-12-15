import React, { memo } from "react";


interface AnalyticsHeaderProps {
  onRefresh: () => void;
  isRefetching: boolean;
}

const AnalyticsHeaderComponent: React.FC<AnalyticsHeaderProps> = ({
  onRefresh: _onRefresh,
  isRefetching: _isRefetching,
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">
          Analytics
        </h2>
        <p className="mt-1 text-zinc-400">
          Insights and performance metrics for your projects and team.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 w-full sm:w-auto"></div>
    </div>
  );
};

// Export with memo for performance optimization
export const AnalyticsHeader = memo(AnalyticsHeaderComponent);
