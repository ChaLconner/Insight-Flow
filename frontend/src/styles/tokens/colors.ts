/**
 * Insight Flow Design Tokens - Colors
 * ระบบสีที่ใช้ในโปรเจกต์ Insight Flow
 */

// สีหลัก (Primary Colors)
export const primaryColors = {
  50: '#eff6ff',
  100: '#dbeafe',
  200: '#bfdbfe',
  300: '#93c5fd',
  400: '#60a5fa',
  500: '#3b82f6',
  600: '#2563eb',
  700: '#1d4ed8',
  800: '#1e40af',
  900: '#1e3a8a',
  950: '#172554',
  DEFAULT: 'hsl(221.2 83.2% 53.3%)',
  foreground: 'hsl(210 40% 98%)',
} as const;

// สีรอง (Secondary Colors)
export const secondaryColors = {
  50: '#f8fafc',
  100: '#f1f5f9',
  200: '#e2e8f0',
  300: '#cbd5e1',
  400: '#94a3b8',
  500: '#64748b',
  600: '#475569',
  700: '#334155',
  800: '#1e293b',
  900: '#0f172a',
  950: '#020617',
  DEFAULT: 'hsl(210 40% 96%)',
  foreground: 'hsl(222.2 84% 4.9%)',
} as const;

// สีสำเร็จ (Success Colors)
export const successColors = {
  50: '#f0fdf4',
  100: '#dcfce7',
  200: '#bbf7d0',
  300: '#86efac',
  400: '#4ade80',
  500: '#22c55e',
  600: '#16a34a',
  700: '#15803d',
  800: '#166534',
  900: '#14532d',
  DEFAULT: 'hsl(142.1 76.2% 36.3%)',
} as const;

// สีเตือน (Warning Colors)
export const warningColors = {
  50: '#fffbeb',
  100: '#fef3c7',
  200: '#fde68a',
  300: '#fcd34d',
  400: '#fbbf24',
  500: '#f59e0b',
  600: '#d97706',
  700: '#b45309',
  800: '#92400e',
  900: '#78350f',
  DEFAULT: 'hsl(47.9 95.8% 53.1%)',
} as const;

// สีข้อผิดพลาด (Error Colors)
export const errorColors = {
  50: '#fef2f2',
  100: '#fee2e2',
  200: '#fecaca',
  300: '#fca5a5',
  400: '#f87171',
  500: '#ef4444',
  600: '#dc2626',
  700: '#b91c1c',
  800: '#991b1b',
  900: '#7f1d1d',
  DEFAULT: 'hsl(0 84.2% 60.2%)',
} as const;

// สีข้อมูล (Info Colors)
export const infoColors = {
  50: '#eff6ff',
  100: '#dbeafe',
  200: '#bfdbfe',
  300: '#93c5fd',
  400: '#60a5fa',
  500: '#3b82f6',
  600: '#2563eb',
  700: '#1d4ed8',
  800: '#1e40af',
  900: '#1e3a8a',
  DEFAULT: 'hsl(221.2 83.2% 53.3%)',
} as const;

// สี Glass Morphism
export const glassColors = {
  light: 'rgba(255, 255, 255, 0.05)',
  medium: 'rgba(255, 255, 255, 0.1)',
  dark: 'rgba(0, 0, 0, 0.05)',
  border: 'rgba(255, 255, 255, 0.2)',
  borderLight: 'rgba(255, 255, 255, 0.1)',
} as const;

// สีสถานะ (Status Colors)
export const statusColors = {
  online: '#22c55e',
  offline: '#9ca3af',
  busy: '#ef4444',
  away: '#f59e0b',
} as const;

// สีความสำคัญ (Priority Colors)
export const priorityColors = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
} as const;

// สีพื้นหลังและข้อความ (Background & Text Colors)
export const semanticColors = {
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',
  card: 'hsl(var(--card))',
  cardForeground: 'hsl(var(--card-foreground))',
  popover: 'hsl(var(--popover))',
  popoverForeground: 'hsl(var(--popover-foreground))',
  muted: 'hsl(var(--muted))',
  mutedForeground: 'hsl(var(--muted-foreground))',
  accent: 'hsl(var(--accent))',
  accentForeground: 'hsl(var(--accent-foreground))',
  destructive: 'hsl(var(--destructive))',
  destructiveForeground: 'hsl(var(--destructive-foreground))',
  border: 'hsl(var(--border))',
  input: 'hsl(var(--input))',
  ring: 'hsl(var(--ring))',
} as const;

// ไล่สี (Gradients)
export const gradients = {
  primary: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  secondary: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  success: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  warning: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  error: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  glass: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%)',
  heroPattern: 'radial-gradient(circle at 1px 1px, rgba(59, 130, 246, 0.15) 1px, transparent 0)',
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