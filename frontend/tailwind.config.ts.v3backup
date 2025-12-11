import type { Config } from "tailwindcss"
import { designTokens } from "./src/styles/tokens"

const config: Config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        // Use design tokens for colors
        primary: designTokens.colors.primary,
        secondary: designTokens.colors.secondary,
        success: designTokens.colors.success,
        warning: designTokens.colors.warning,
        error: designTokens.colors.error,
        info: designTokens.colors.info,
        glass: designTokens.colors.glass,
        status: designTokens.colors.status,
        priority: designTokens.colors.priority,

        // Shadcn/ui theme compatibility
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },

      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      // Use design tokens for font families
      fontFamily: designTokens.typography.fontFamilies as any,

      // Use design tokens for spacing
      spacing: designTokens.spacing.spacing,

      animation: {
        // Component animations
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",

        // Entry animations
        "fade-in": "fadeIn 0.3s ease-out",
        "fade-in-up": "fadeInUp 0.3s ease-out",
        "fade-in-down": "fadeInDown 0.3s ease-out",
        "fade-in-left": "fadeInLeft 0.3s ease-out",
        "fade-in-right": "fadeInRight 0.3s ease-out",
        "slide-in-up": "slideInUp 0.3s ease-out",
        "slide-in-down": "slideInDown 0.3s ease-out",
        "slide-in-left": "slideInLeft 0.3s ease-out",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "scale-in": "scaleIn 0.2s ease-out",
        "bounce-in": "bounceIn 0.6s ease-out",

        // Exit animations
        "fade-out": "fadeOut 0.3s ease-in",
        "fade-out-up": "fadeOutUp 0.3s ease-in",
        "fade-out-down": "fadeOutDown 0.3s ease-in",
        "fade-out-left": "fadeOutLeft 0.3s ease-in",
        "fade-out-right": "fadeOutRight 0.3s ease-in",
        "slide-out-up": "slideOutUp 0.3s ease-in",
        "slide-out-down": "slideOutDown 0.3s ease-in",
        "slide-out-left": "slideOutLeft 0.3s ease-in",
        "slide-out-right": "slideOutRight 0.3s ease-in",
        "scale-out": "scaleOut 0.2s ease-in",
        "bounce-out": "bounceOut 0.6s ease-in",

        // Attention animations
        "bounce": "bounce 1s ease-in-out infinite",
        "pulse": "pulse 2s ease-in-out infinite",
        "shake": "shake 0.5s ease-in-out",
        "shake-x": "shakeX 0.5s ease-in-out",
        "shake-y": "shakeY 0.5s ease-in-out",
        "heartbeat": "heartbeat 1.3s ease-in-out infinite",
        "wobble": "wobble 1s ease-in-out",
        "glow": "glow 2s ease-in-out infinite",
        "float": "float 3s ease-in-out infinite",

        // Loading animations
        "spin": "spin 1s linear infinite",
        "ping": "ping 1s cubic-bezier(0, 0, 0.2, 1) infinite",
        "shimmer": "shimmer 1.5s ease-in-out infinite",
        "wave": "wave 2s linear infinite",
        "bounce-gentle": "bounce 1s ease-in-out infinite",
      },

      // Use design tokens for gradients
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'glass-gradient': designTokens.colors.gradients.glass,
        'hero-pattern': designTokens.colors.gradients.heroPattern,
        'gradient-primary': designTokens.colors.gradients.primary,
        'gradient-secondary': designTokens.colors.gradients.secondary,
        'gradient-success': designTokens.colors.gradients.success,
        'gradient-warning': designTokens.colors.gradients.warning,
        'gradient-error': designTokens.colors.gradients.error,
      },

      // Use design tokens for typography
      fontSize: designTokens.typography.fontSizes as any,
      fontWeight: designTokens.typography.fontWeights,
      lineHeight: designTokens.typography.lineHeights,
      letterSpacing: designTokens.typography.letterSpacings,

      // Breakpoints
      screens: {
        'xs': '475px',
      },
    },
  },

  plugins: [
    require("tailwindcss-animate"),
    // Glass morphism utilities plugin using design tokens
    function ({ addUtilities }: { addUtilities: (utilities: any) => void }) {
      const glassUtilities = {
        '.glass': {
          'backdrop-filter': 'blur(10px)',
          'background': designTokens.colors.glass.light,
          'border': `1px solid ${designTokens.colors.glass.border}`,
          'box-shadow': designTokens.shadows.glass.glass,
        },
        '.glass-dark': {
          'backdrop-filter': 'blur(10px)',
          'background': designTokens.colors.glass.dark,
          'border': `1px solid ${designTokens.colors.glass.borderLight}`,
          'box-shadow': designTokens.shadows.darkMode.glass,
        },
        '.glass-strong': {
          'backdrop-filter': 'blur(20px)',
          'background': designTokens.colors.glass.medium,
          'border': `1px solid ${designTokens.colors.glass.border}`,
          'box-shadow': designTokens.shadows.glass.glassStrong,
        },
        '.glass-subtle': {
          'backdrop-filter': 'blur(8px)',
          'background': designTokens.colors.glass.light,
          'border': `1px solid ${designTokens.colors.glass.borderLight}`,
          'box-shadow': designTokens.shadows.glass.glassSubtle,
        },
        '.glass-card': {
          'backdrop-filter': 'blur(16px)',
          'background': designTokens.colors.gradients.glass,
          'border': `1px solid ${designTokens.colors.glass.border}`,
          'box-shadow': designTokens.shadows.glass.glassCard,
        },
        '.glass-nav': {
          'backdrop-filter': 'blur(20px)',
          'background': designTokens.colors.glass.light,
          'border': `1px solid ${designTokens.colors.glass.borderLight}`,
          'box-shadow': designTokens.shadows.glass.glassNav,
        },
        '.glass-modal': {
          'backdrop-filter': 'blur(24px)',
          'background': designTokens.colors.glass.medium,
          'border': `1px solid ${designTokens.colors.glass.border}`,
          'box-shadow': designTokens.shadows.glass.glassModal,
        },
      };
      addUtilities(glassUtilities);
    },
    // Custom utilities using design tokens
    function ({ addUtilities }: { addUtilities: (utilities: any) => void }) {
      const customUtilities = {
        '.text-gradient': {
          'background': designTokens.colors.gradients.primary,
          'background-clip': 'text',
          '-webkit-background-clip': 'text',
          '-webkit-text-fill-color': 'transparent',
        },
        '.bg-pattern': {
          'background-image': designTokens.colors.gradients.heroPattern,
          'background-size': '20px 20px',
        },
        '.scrollbar-hide': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        '.scrollbar-thin': {
          '&::-webkit-scrollbar': {
            width: '6px',
            height: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(156, 163, 175, 0.5)',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'rgba(156, 163, 175, 0.8)',
          },
        },
        // Status utilities
        '.status-online': {
          'background-color': designTokens.colors.status.online,
          'box-shadow': designTokens.shadows.status.online,
        },
        '.status-offline': {
          'background-color': designTokens.colors.status.offline,
          'box-shadow': designTokens.shadows.status.offline,
        },
        '.status-busy': {
          'background-color': designTokens.colors.status.busy,
          'box-shadow': designTokens.shadows.status.busy,
        },
        // Priority utilities
        '.priority-high': {
          'color': designTokens.colors.priority.high,
          'background-color': `${designTokens.colors.priority.high}10`,
          'border-color': `${designTokens.colors.priority.high}20`,
        },
        '.priority-medium': {
          'color': designTokens.colors.priority.medium,
          'background-color': `${designTokens.colors.priority.medium}10`,
          'border-color': `${designTokens.colors.priority.medium}20`,
        },
        '.priority-low': {
          'color': designTokens.colors.priority.low,
          'background-color': `${designTokens.colors.priority.low}10`,
          'border-color': `${designTokens.colors.priority.low}20`,
        },
      };
      addUtilities(customUtilities);
    },
  ],
}

export default config