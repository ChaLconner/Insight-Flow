/**
 * Insight Flow Design Tokens - Shadows
 * ระบบเงาที่ใช้ในโปรเจกต์ Insight Flow
 */

// เงาพื้นฐาน (Base Shadows)
export const baseShadows = {
  none: "none",
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  DEFAULT: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
  inner: "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)",
} as const;

// เงาสำหรับ Glass Morphism
export const glassShadows = {
  glass: "0 8px 32px 0 rgba(31, 38, 135, 0.37)",
  glassInset: "inset 0 1px 0 0 rgba(255, 255, 255, 0.05)",
  glassSubtle: "0 4px 16px 0 rgba(31, 38, 135, 0.2)",
  glassMedium: "0 8px 24px 0 rgba(31, 38, 135, 0.3)",
  glassStrong: "0 12px 40px 0 rgba(31, 38, 135, 0.5)",
  glassNav: "0 8px 32px 0 rgba(31, 38, 135, 0.2)",
  glassCard: "0 8px 32px 0 rgba(31, 38, 135, 0.37)",
  glassModal: "0 16px 40px 0 rgba(31, 38, 135, 0.5)",
  glassButton: "0 4px 16px 0 rgba(31, 38, 135, 0.2)",
  glassButtonHover: "0 8px 24px 0 rgba(31, 38, 135, 0.4)",
} as const;

// เงาสำหรับ Cards
export const cardShadows = {
  card: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
  cardHover:
    "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  cardElevated:
    "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  cardSoft:
    "0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)",
  cardElegant:
    "0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  cardGlow: "0 0 20px rgba(59, 130, 246, 0.15)",
  cardGlowHover: "0 0 30px rgba(59, 130, 246, 0.25)",
} as const;

// เงาสำหรับ Buttons
export const buttonShadows = {
  button: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  buttonHover:
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  buttonActive:
    "0 1px 2px 0 rgba(0, 0, 0, 0.05), inset 0 1px 2px 0 rgba(0, 0, 0, 0.1)",
  buttonDisabled: "none",
  buttonPrimary: "0 4px 14px 0 rgba(59, 130, 246, 0.3)",
  buttonPrimaryHover: "0 6px 20px 0 rgba(59, 130, 246, 0.4)",
  buttonSecondary: "0 2px 8px 0 rgba(0, 0, 0, 0.1)",
  buttonSecondaryHover: "0 4px 12px 0 rgba(0, 0, 0, 0.15)",
} as const;

// เงาสำหรับ Modals & Popovers
export const modalShadows = {
  modal: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
  modalOverlay: "0 0 0 1000px rgba(0, 0, 0, 0.5)",
  popover:
    "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  tooltip:
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  dropdown:
    "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
} as const;

// เงาสำหรับ Navigation
export const navigationShadows = {
  navbar: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
  sidebar:
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  tab: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  tabActive: "0 2px 4px 0 rgba(0, 0, 0, 0.1)",
  breadcrumb: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
} as const;

// เงาสำหรับ Forms
export const formShadows = {
  input: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  inputFocus:
    "0 0 0 3px rgba(59, 130, 246, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  inputError:
    "0 0 0 3px rgba(239, 68, 68, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  inputSuccess:
    "0 0 0 3px rgba(34, 197, 94, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  select: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
  checkbox: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  radio: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
} as const;

// เงาสำหรับ Status & Indicators
export const statusShadows = {
  success: "0 0 0 3px rgba(34, 197, 94, 0.1)",
  warning: "0 0 0 3px rgba(245, 158, 11, 0.1)",
  error: "0 0 0 3px rgba(239, 68, 68, 0.1)",
  info: "0 0 0 3px rgba(59, 130, 246, 0.1)",
  online: "0 0 0 2px rgba(34, 197, 94, 0.2)",
  offline: "0 0 0 2px rgba(156, 163, 175, 0.2)",
  busy: "0 0 0 2px rgba(239, 68, 68, 0.2)",
} as const;

// เงาสำหรับ Decorative Elements
export const decorativeShadows = {
  glow: "0 0 20px rgba(59, 130, 246, 0.3)",
  glowLarge: "0 0 40px rgba(59, 130, 246, 0.4)",
  glowSoft: "0 0 10px rgba(59, 130, 246, 0.2)",
  glowColored: {
    blue: "0 0 20px rgba(59, 130, 246, 0.3)",
    green: "0 0 20px rgba(34, 197, 94, 0.3)",
    red: "0 0 20px rgba(239, 68, 68, 0.3)",
    yellow: "0 0 20px rgba(245, 158, 11, 0.3)",
    purple: "0 0 20px rgba(147, 51, 234, 0.3)",
  },
  neon: {
    blue: "0 0 10px rgba(59, 130, 246, 0.8), 0 0 20px rgba(59, 130, 246, 0.6), 0 0 30px rgba(59, 130, 246, 0.4)",
    green:
      "0 0 10px rgba(34, 197, 94, 0.8), 0 0 20px rgba(34, 197, 94, 0.6), 0 0 30px rgba(34, 197, 94, 0.4)",
    red: "0 0 10px rgba(239, 68, 68, 0.8), 0 0 20px rgba(239, 68, 68, 0.6), 0 0 30px rgba(239, 68, 68, 0.4)",
    yellow:
      "0 0 10px rgba(245, 158, 11, 0.8), 0 0 20px rgba(245, 158, 11, 0.6), 0 0 30px rgba(245, 158, 11, 0.4)",
    purple:
      "0 0 10px rgba(147, 51, 234, 0.8), 0 0 20px rgba(147, 51, 234, 0.6), 0 0 30px rgba(147, 51, 234, 0.4)",
  },
} as const;

// เงาสำหรับ Dark Mode
export const darkModeShadows = {
  card: "0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px 0 rgba(0, 0, 0, 0.2)",
  cardHover:
    "0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2)",
  modal: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
  button: "0 1px 2px 0 rgba(0, 0, 0, 0.2)",
  buttonHover:
    "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
  input: "0 1px 2px 0 rgba(0, 0, 0, 0.2)",
  inputFocus:
    "0 0 0 3px rgba(59, 130, 246, 0.2), 0 1px 2px 0 rgba(0, 0, 0, 0.2)",
  glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
  glassNav: "0 8px 32px 0 rgba(0, 0, 0, 0.2)",
  glassCard: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
  glassModal: "0 16px 40px 0 rgba(0, 0, 0, 0.5)",
} as const;

// เงาสำหรับ Interactive States
export const interactiveShadows = {
  hover:
    "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  active:
    "0 1px 2px 0 rgba(0, 0, 0, 0.05), inset 0 1px 2px 0 rgba(0, 0, 0, 0.1)",
  focus: "0 0 0 3px rgba(59, 130, 246, 0.1)",
  focusRing:
    "0 0 0 3px rgba(59, 130, 246, 0.1), 0 0 0 1px rgba(59, 130, 246, 0.2)",
  disabled: "none",
  loading: "0 0 0 2px rgba(59, 130, 246, 0.2)",
} as const;

// รวมทุกอย่าง
export const shadows = {
  base: baseShadows,
  glass: glassShadows,
  card: cardShadows,
  button: buttonShadows,
  modal: modalShadows,
  navigation: navigationShadows,
  form: formShadows,
  status: statusShadows,
  decorative: decorativeShadows,
  darkMode: darkModeShadows,
  interactive: interactiveShadows,
} as const;

// ประเภทของเงา
export type ShadowToken = typeof shadows;
export type BaseShadow = keyof typeof baseShadows;
export type GlassShadow = keyof typeof glassShadows;
export type CardShadow = keyof typeof cardShadows;
export type ButtonShadow = keyof typeof buttonShadows;
export type ModalShadow = keyof typeof modalShadows;
export type NavigationShadow = keyof typeof navigationShadows;
export type FormShadow = keyof typeof formShadows;
export type StatusShadow = keyof typeof statusShadows;
export type DecorativeShadow = keyof typeof decorativeShadows;
export type DarkModeShadow = keyof typeof darkModeShadows;
export type InteractiveShadow = keyof typeof interactiveShadows;
