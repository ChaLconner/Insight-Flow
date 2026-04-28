import type { TooltipValueType } from "recharts";

export const analyticsTooltipStyle = {
  backgroundColor: "rgba(24, 24, 27, 0.95)",
  borderColor: "rgba(255,255,255,0.1)",
  color: "#fff",
  borderRadius: "8px",
  boxShadow:
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
};

export const analyticsTooltipTextStyle = { color: "#fff" };

export function formatAnalyticsTooltip(
  value: TooltipValueType | undefined,
  name: string | number | undefined,
): [TooltipValueType, string | number] {
  return [value ?? 0, name ?? ""];
}
