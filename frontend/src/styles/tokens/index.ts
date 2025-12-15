/**
 * Insight Flow Design Tokens - Main Index
 * รวมทุก design tokens ของโปรเจกต์ Insight Flow
 */

// Import all token modules
export * from "./colors";
export * from "./typography";
export * from "./spacing";
export * from "./shadows";
export * from "./animations";

// Import individual token modules for re-export
import { colors } from "./colors";
import { typography } from "./typography";
import { spacingTokens } from "./spacing";
import { shadows } from "./shadows";
import { animations } from "./animations";

// Main design tokens object
export const designTokens = {
  colors,
  typography,
  spacing: spacingTokens,
  shadows,
  animations,
} as const;

// CSS Custom Properties Generator
export const generateCSSVariables = () => {
  const cssVars: Record<string, string> = {};

  // Color variables
  Object.entries(colors.primary).forEach(([key, value]) => {
    if (key !== "DEFAULT") {
      cssVars[`--color-primary-${key}`] = value;
    } else {
      cssVars["--color-primary"] = value;
    }
  });

  Object.entries(colors.secondary).forEach(([key, value]) => {
    if (key !== "DEFAULT") {
      cssVars[`--color-secondary-${key}`] = value;
    } else {
      cssVars["--color-secondary"] = value;
    }
  });

  Object.entries(colors.success).forEach(([key, value]) => {
    if (key !== "DEFAULT") {
      cssVars[`--color-success-${key}`] = value;
    } else {
      cssVars["--color-success"] = value;
    }
  });

  Object.entries(colors.warning).forEach(([key, value]) => {
    if (key !== "DEFAULT") {
      cssVars[`--color-warning-${key}`] = value;
    } else {
      cssVars["--color-warning"] = value;
    }
  });

  Object.entries(colors.error).forEach(([key, value]) => {
    if (key !== "DEFAULT") {
      cssVars[`--color-error-${key}`] = value;
    } else {
      cssVars["--color-error"] = value;
    }
  });

  // Glass colors
  Object.entries(colors.glass).forEach(([key, value]) => {
    cssVars[`--glass-${key}`] = value;
  });

  // Status colors
  Object.entries(colors.status).forEach(([key, value]) => {
    cssVars[`--status-${key}`] = value;
  });

  // Priority colors
  Object.entries(colors.priority).forEach(([key, value]) => {
    cssVars[`--priority-${key}`] = value;
  });

  // Semantic colors
  Object.entries(colors.semantic).forEach(([key, value]) => {
    cssVars[`--${key}`] = value;
  });

  // Gradients
  Object.entries(colors.gradients).forEach(([key, value]) => {
    cssVars[`--gradient-${key}`] = value;
  });

  // Spacing variables
  Object.entries(spacingTokens.spacing).forEach(([key, value]) => {
    cssVars[`--spacing-${key}`] = value;
  });

  // Typography variables
  Object.entries(typography.fontSizes).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      cssVars[`--font-size-${key}`] = value[0];
      cssVars[`--line-height-${key}`] = value[1].lineHeight || value[1];
    }
  });

  Object.entries(typography.fontWeights).forEach(([key, value]) => {
    cssVars[`--font-weight-${key}`] = value;
  });

  Object.entries(typography.lineHeights).forEach(([key, value]) => {
    cssVars[`--line-height-${key}`] = value;
  });

  Object.entries(typography.letterSpacings).forEach(([key, value]) => {
    cssVars[`--letter-spacing-${key}`] = value;
  });

  // Shadow variables
  Object.entries(shadows.base).forEach(([key, value]) => {
    cssVars[`--shadow-${key}`] = value;
  });

  Object.entries(shadows.glass).forEach(([key, value]) => {
    cssVars[`--shadow-glass-${key}`] = value;
  });

  Object.entries(shadows.card).forEach(([key, value]) => {
    cssVars[`--shadow-card-${key}`] = value;
  });

  Object.entries(shadows.button).forEach(([key, value]) => {
    cssVars[`--shadow-button-${key}`] = value;
  });

  // Animation variables
  Object.entries(animations.durations).forEach(([key, value]) => {
    cssVars[`--duration-${key}`] = value;
  });

  Object.entries(animations.timingFunctions).forEach(([key, value]) => {
    cssVars[`--timing-${key}`] = value;
  });

  return cssVars;
};

// CSS String Generator
export const generateCSSString = () => {
  const cssVars = generateCSSVariables();
  const cssString = Object.entries(cssVars)
    .map(([key, value]) => `  ${key}: ${value};`)
    .join("\n");

  return `:root {\n${cssString}\n}`;
};

// Theme variants generator
export const generateThemeVariants = () => {
  return {
    light: {
      colors: {
        background: colors.semantic.background,
        foreground: colors.semantic.foreground,
        card: colors.semantic.card,
        cardForeground: colors.semantic.cardForeground,
        popover: colors.semantic.popover,
        popoverForeground: colors.semantic.popoverForeground,
        primary: colors.primary.DEFAULT,
        primaryForeground: colors.primary.foreground,
        secondary: colors.secondary.DEFAULT,
        secondaryForeground: colors.secondary.foreground,
        muted: colors.semantic.muted,
        mutedForeground: colors.semantic.mutedForeground,
        accent: colors.semantic.accent,
        accentForeground: colors.semantic.accentForeground,
        destructive: colors.semantic.destructive,
        destructiveForeground: colors.semantic.destructiveForeground,
        border: colors.semantic.border,
        input: colors.semantic.input,
        ring: colors.semantic.ring,
      },
    },
    dark: {
      colors: {
        background: "hsl(222.2 84% 4.9%)",
        foreground: "hsl(210 40% 98%)",
        card: "hsl(222.2 84% 4.9%)",
        cardForeground: "hsl(210 40% 98%)",
        popover: "hsl(222.2 84% 4.9%)",
        popoverForeground: "hsl(210 40% 98%)",
        primary: "hsl(239 84% 67%)", // Indigo 500
        primaryForeground: "hsl(210 40% 98%)",
        secondary: "hsl(215 28% 17%)", // Slate 900ish
        secondaryForeground: "hsl(210 40% 98%)",
        muted: "hsl(215 28% 17%)",
        mutedForeground: "hsl(215 20.2% 65.1%)",
        accent: "hsl(215 28% 17%)",
        accentForeground: "hsl(210 40% 98%)",
        destructive: "hsl(0 84% 60%)",
        destructiveForeground: "hsl(210 40% 98%)",
        border: "hsl(215 28% 17%)",
        input: "hsl(215 28% 17%)",
        ring: "hsl(239 84% 67%)",
      },
    },
  } as const;
};

// Utility functions for design tokens
export const tokenUtils = {
  // Get color value
  getColor: (path: string) => {
    const keys = path.split(".");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = colors;

    for (const key of keys) {
      value = value?.[key];
    }

    return value;
  },

  // Get spacing value
  getSpacing: (key: string) => {
    return spacingTokens.spacing[key as keyof typeof spacingTokens.spacing];
  },

  // Get typography value
  getTypography: (path: string) => {
    const keys = path.split(".");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = typography;

    for (const key of keys) {
      value = value?.[key];
    }

    return value;
  },

  // Get shadow value
  getShadow: (path: string) => {
    const keys = path.split(".");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = shadows;

    for (const key of keys) {
      value = value?.[key];
    }

    return value;
  },

  // Get animation value
  getAnimation: (path: string) => {
    const keys = path.split(".");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = animations;

    for (const key of keys) {
      value = value?.[key];
    }

    return value;
  },

  // Generate responsive spacing
  getResponsiveSpacing: (
    base: string,
    sm?: string,
    md?: string,
    lg?: string,
    xl?: string,
  ) => {
    return {
      base: spacingTokens.spacing[base as keyof typeof spacingTokens.spacing],
      sm: sm
        ? spacingTokens.spacing[sm as keyof typeof spacingTokens.spacing]
        : undefined,
      md: md
        ? spacingTokens.spacing[md as keyof typeof spacingTokens.spacing]
        : undefined,
      lg: lg
        ? spacingTokens.spacing[lg as keyof typeof spacingTokens.spacing]
        : undefined,
      xl: xl
        ? spacingTokens.spacing[xl as keyof typeof spacingTokens.spacing]
        : undefined,
    };
  },

  // Generate color palette
  generateColorPalette: (baseColor: string) => {
    // This would typically use a color manipulation library
    // For now, return a basic palette
    return {
      50: `${baseColor}05`,
      100: `${baseColor}10`,
      200: `${baseColor}20`,
      300: `${baseColor}30`,
      400: `${baseColor}40`,
      500: baseColor,
      600: `${baseColor}60`,
      700: `${baseColor}70`,
      800: `${baseColor}80`,
      900: `${baseColor}90`,
    };
  },
} as const;

// Export types
export type DesignTokens = typeof designTokens;
export type ColorToken = typeof colors;
export type TypographyToken = typeof typography;
export type SpacingToken = typeof spacingTokens;
export type ShadowToken = typeof shadows;
export type AnimationToken = typeof animations;
export type ThemeVariant = keyof ReturnType<typeof generateThemeVariants>;
export type TokenUtils = typeof tokenUtils;

// Default export
export default designTokens;
