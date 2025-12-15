/**
 * Insight Flow Design Tokens - Colors
 * ระบบสีที่ใช้ในโปรเจกต์ Insight Flow
 */

// สีหลัก (Primary Colors) - Indigo Palette (Premium)
export const primaryColors = {
  50: "#eef2ff",
  100: "#e0e7ff",
  200: "#c7d2fe",
  300: "#a5b4fc",
  400: "#818cf8",
  500: "#6366f1",
  600: "#4f46e5",
  700: "#4338ca",
  800: "#3730a3",
  900: "#312e81",
  950: "#1e1b4b",
  DEFAULT: "hsl(239 84% 67%)", // Indigo 500
  foreground: "hsl(210 40% 98%)",
} as const;

// สีรอง (Secondary Colors) - Slate Palette (Cool Neutral)
export const secondaryColors = {
  50: "#f8fafc",
  100: "#f1f5f9",
  200: "#e2e8f0",
  300: "#cbd5e1",
  400: "#94a3b8",
  500: "#64748b",
  600: "#475569",
  700: "#334155",
  800: "#1e293b",
  900: "#0f172a",
  950: "#020617",
  DEFAULT: "hsl(215 16% 47%)", // Slate 500
  foreground: "hsl(222.2 84% 4.9%)",
} as const;

// สีสำเร็จ (Success Colors) - Emerald Palette
export const successColors = {
  50: "#ecfdf5",
  100: "#d1fae5",
  200: "#a7f3d0",
  300: "#6ee7b7",
  400: "#34d399",
  500: "#10b981",
  600: "#059669",
  700: "#047857",
  800: "#065f46",
  900: "#064e3b",
  DEFAULT: "hsl(151 65% 39%)", // Emerald 600
} as const;

// สีเตือน (Warning Colors) - Amber Palette
export const warningColors = {
  50: "#fff7ed",
  100: "#ffedd5",
  200: "#fed7aa",
  300: "#fdba74",
  400: "#fb923c",
  500: "#f97316",
  600: "#ea580c",
  700: "#c2410c",
  800: "#9a3412",
  900: "#7c2d12",
  DEFAULT: "hsl(27 96% 61%)", // Orange 500
} as const;

// สีข้อผิดพลาด (Error Colors) - Red Palette
export const errorColors = {
  50: "#fef2f2",
  100: "#fee2e2",
  200: "#fecaca",
  300: "#fca5a5",
  400: "#f87171",
  500: "#ef4444",
  600: "#dc2626",
  700: "#b91c1c",
  800: "#991b1b",
  900: "#7f1d1d",
  DEFAULT: "hsl(0 84% 60%)", // Red 500
} as const;

// สีข้อมูล (Info Colors) - Sky Palette
export const infoColors = {
  50: "#f0f9ff",
  100: "#e0f2fe",
  200: "#bae6fd",
  300: "#7dd3fc",
  400: "#38bdf8",
  500: "#0ea5e9",
  600: "#0284c7",
  700: "#0369a1",
  800: "#075985",
  900: "#0c4a6e",
  DEFAULT: "hsl(199 89% 48%)", // Sky 500
} as const;

// สี Glass Morphism - Refined Translucency
export const glassColors = {
  light: "rgba(255, 255, 255, 0.03)",
  medium: "rgba(255, 255, 255, 0.07)",
  dark: "rgba(0, 0, 0, 0.2)",
  border: "rgba(255, 255, 255, 0.08)",
  borderLight: "rgba(255, 255, 255, 0.04)",
} as const;

// สีสถานะ (Status Colors)
export const statusColors = {
  online: "#10b981", // Emerald 500
  offline: "#94a3b8", // Slate 400
  busy: "#ef4444", // Red 500
  away: "#f59e0b", // Amber 500
} as const;

// สีความสำคัญ (Priority Colors)
export const priorityColors = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#10b981",
} as const;

// สีพื้นหลังและข้อความ (Background & Text Colors)
export const semanticColors = {
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  card: "hsl(var(--card))",
  cardForeground: "hsl(var(--card-foreground))",
  popover: "hsl(var(--popover))",
  popoverForeground: "hsl(var(--popover-foreground))",
  muted: "hsl(var(--muted))",
  mutedForeground: "hsl(var(--muted-foreground))",
  accent: "hsl(var(--accent))",
  accentForeground: "hsl(var(--accent-foreground))",
  destructive: "hsl(var(--destructive))",
  destructiveForeground: "hsl(var(--destructive-foreground))",
  border: "hsl(var(--border))",
  input: "hsl(var(--input))",
  ring: "hsl(var(--ring))",
} as const;

// ไล่สี (Gradients)
export const gradients = {
  primary: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)", // Indigo to Purple
  secondary: "linear-gradient(135deg, #3b82f6 0%, #2dd4bf 100%)", // Blue to Teal
  success: "linear-gradient(135deg, #10b981 0%, #34d399 100%)", // Emerald to Green
  warning: "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)", // Amber
  error: "linear-gradient(135deg, #ef4444 0%, #f87171 100%)", // Red
  glass:
    "linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%)",
  heroPattern:
    "radial-gradient(circle at 1px 1px, rgba(99, 102, 241, 0.15) 1px, transparent 0)",
} as const;

// รวมทุกสี
export const colors = {
  primary: primaryColors,
  secondary: secondaryColors,
  success: successColors,
  warning: warningColors,
  error: errorColors,
  info: infoColors,
  glass: glassColors,
  status: statusColors,
  priority: priorityColors,
  semantic: semanticColors,
  gradients,
} as const;

// ประเภทของสี
export type ColorToken = typeof colors;
export type PrimaryColor = keyof typeof primaryColors;
export type SecondaryColor = keyof typeof secondaryColors;
export type StatusColor = keyof typeof statusColors;
export type PriorityColor = keyof typeof priorityColors;
export type GradientType = keyof typeof gradients;
