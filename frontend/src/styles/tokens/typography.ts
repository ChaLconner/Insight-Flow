/**
 * Insight Flow Design Tokens - Typography
 * ระบบตัวอักษรที่ใช้ในโปรเจกต์ Insight Flow
 */

// ฟอนต์ที่ใช้
export const fontFamilies = {
  sans: [
    "Inter var",
    "Inter",
    "system-ui",
    "sans-serif",
  ],
  mono: [
    "JetBrains Mono",
    "Monaco",
    "Consolas",
    "Liberation Mono",
    "Courier New",
    "monospace",
  ],
  display: [
    "Inter var",
    "Inter",
    "system-ui",
    "sans-serif",
  ],
} as const;

// ขนาดตัวอักษร (Font Sizes)
export const fontSizes = {
  xs: ['0.75rem', { lineHeight: '1rem' }],
  sm: ['0.875rem', { lineHeight: '1.25rem' }],
  base: ['1rem', { lineHeight: '1.5rem' }],
  lg: ['1.125rem', { lineHeight: '1.75rem' }],
  xl: ['1.25rem', { lineHeight: '1.75rem' }],
  '2xl': ['1.5rem', { lineHeight: '2rem' }],
  '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
  '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
  '5xl': ['3rem', { lineHeight: '1' }],
  '6xl': ['3.75rem', { lineHeight: '1' }],
  '7xl': ['4.5rem', { lineHeight: '1' }],
  '8xl': ['6rem', { lineHeight: '1' }],
  '9xl': ['8rem', { lineHeight: '1' }],
} as const;

// น้ำหนักตัวอักษร (Font Weights)
export const fontWeights = {
  thin: '100',
  extralight: '200',
  light: '300',
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
  extrabold: '800',
  black: '900',
} as const;

// ความสูงบรรทัด (Line Heights)
export const lineHeights = {
  none: '1',
  tight: '1.25',
  snug: '1.375',
  normal: '1.5',
  relaxed: '1.625',
  loose: '2',
} as const;

// ระยะห่างระหว่างตัวอักษร (Letter Spacing)
export const letterSpacings = {
  tighter: '-0.05em',
  tight: '-0.025em',
  normal: '0em',
  wide: '0.025em',
  wider: '0.05em',
  widest: '0.1em',
} as const;

// ขนาดตัวอักษรสำหรับหัวข้อ (Heading Sizes)
export const headingSizes = {
  h1: {
    fontSize: '2.25rem',
    lineHeight: '2.5rem',
    fontWeight: '700',
    letterSpacing: '-0.025em',
  },
  h2: {
    fontSize: '1.875rem',
    lineHeight: '2.25rem',
    fontWeight: '600',
    letterSpacing: '-0.025em',
  },
  h3: {
    fontSize: '1.5rem',
    lineHeight: '2rem',
    fontWeight: '600',
    letterSpacing: '-0.025em',
  },
  h4: {
    fontSize: '1.25rem',
    lineHeight: '1.75rem',
    fontWeight: '600',
    letterSpacing: '-0.025em',
  },
  h5: {
    fontSize: '1.125rem',
    lineHeight: '1.75rem',
    fontWeight: '600',
    letterSpacing: '-0.025em',
  },
  h6: {
    fontSize: '1rem',
    lineHeight: '1.5rem',
    fontWeight: '600',
    letterSpacing: '-0.025em',
  },
} as const;

// ขนาดตัวอักษรสำหรับข้อความ (Text Sizes)
export const textSizes = {
  xs: {
    fontSize: '0.75rem',
    lineHeight: '1rem',
    fontWeight: '400',
  },
  sm: {
    fontSize: '0.875rem',
    lineHeight: '1.25rem',
    fontWeight: '400',
  },
  base: {
    fontSize: '1rem',
    lineHeight: '1.5rem',
    fontWeight: '400',
  },
  lg: {
    fontSize: '1.125rem',
    lineHeight: '1.75rem',
    fontWeight: '400',
  },
  xl: {
    fontSize: '1.25rem',
    lineHeight: '1.75rem',
    fontWeight: '400',
  },
  '2xl': {
    fontSize: '1.5rem',
    lineHeight: '2rem',
    fontWeight: '400',
  },
} as const;

// สไตล์ตัวอักษรพิเศษ (Special Typography)
export const specialTypography = {
  // ข้อความที่มี gradient
  gradient: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    backgroundClip: 'text',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  // ข้อความที่มีความโปร่งแสง
  muted: {
    opacity: 0.7,
  },
  // ข้อความที่มีความหนาแน่น
  dense: {
    lineHeight: '1.25',
    letterSpacing: '-0.025em',
  },
  // ข้อความที่มีระยะห่างมาก
  spacious: {
    lineHeight: '1.75',
    letterSpacing: '0.025em',
  },
} as const;

// ระดับการอ่าน (Reading Levels)
export const readingLevels = {
  // สำหรับหัวข้อหลัก
  display: {
    fontSize: '3rem',
    lineHeight: '1',
    fontWeight: '800',
    letterSpacing: '-0.025em',
  },
  // สำหรับหัวข้อรอง
  headline: {
    fontSize: '2.25rem',
    lineHeight: '2.5rem',
    fontWeight: '700',
    letterSpacing: '-0.025em',
  },
  // สำหรับหัวข้อย่อย
  subheadline: {
    fontSize: '1.5rem',
    lineHeight: '2rem',
    fontWeight: '600',
    letterSpacing: '-0.025em',
  },
  // สำหรับข้อความทั่วไป
  body: {
    fontSize: '1rem',
    lineHeight: '1.5rem',
    fontWeight: '400',
  },
  // สำหรับข้อความเล็ก
  caption: {
    fontSize: '0.875rem',
    lineHeight: '1.25rem',
    fontWeight: '400',
  },
  // สำหรับข้อความขนาดเล็กมาก
  label: {
    fontSize: '0.75rem',
    lineHeight: '1rem',
    fontWeight: '500',
  },
} as const;

// รวมทุกอย่าง
export const typography = {
  fontFamilies,
  fontSizes,
  fontWeights,
  lineHeights,
  letterSpacings,
  headingSizes,
  textSizes,
  specialTypography,
  readingLevels,
} as const;

// ประเภทของตัวอักษร
export type TypographyToken = typeof typography;
export type FontFamily = keyof typeof fontFamilies;
export type FontSize = keyof typeof fontSizes;
export type FontWeight = keyof typeof fontWeights;
export type LineHeight = keyof typeof lineHeights;
export type LetterSpacing = keyof typeof letterSpacings;
export type HeadingSize = keyof typeof headingSizes;
export type TextSize = keyof typeof textSizes;
export type ReadingLevel = keyof typeof readingLevels;