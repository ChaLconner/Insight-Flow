/**
 * Insight Flow Design Tokens - Spacing
 * ระบบระยะห่างที่ใช้ในโปรเจกต์ Insight Flow
 */

// ระบบระยะห่างแบบ 8px grid
export const spacing = {
  // ระยะห่างพื้นฐาน (Base Spacing)
  0: '0',
  px: '1px',
  0.5: '0.125rem', // 2px
  1: '0.25rem',   // 4px
  1.5: '0.375rem', // 6px
  2: '0.5rem',    // 8px
  2.5: '0.625rem', // 10px
  3: '0.75rem',   // 12px
  3.5: '0.875rem', // 14px
  4: '1rem',      // 16px
  4.5: '1.125rem', // 18px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  7: '1.75rem',   // 28px
  8: '2rem',      // 32px
  9: '2.25rem',   // 36px
  10: '2.5rem',   // 40px
  11: '2.75rem',  // 44px
  12: '3rem',     // 48px
  14: '3.5rem',   // 56px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  28: '7rem',     // 112px
  32: '8rem',     // 128px
  36: '9rem',     // 144px
  40: '10rem',    // 160px
  44: '11rem',    // 176px
  48: '12rem',    // 192px
  52: '13rem',    // 208px
  56: '14rem',    // 224px
  60: '15rem',    // 240px
  64: '16rem',    // 256px
  72: '18rem',    // 288px
  80: '20rem',    // 320px
  96: '24rem',    // 384px
  112: '28rem',   // 448px
  128: '32rem',   // 512px
  144: '36rem',   // 576px
  160: '40rem',   // 640px
  176: '44rem',   // 704px
  192: '48rem',   // 768px
  208: '52rem',   // 832px
  224: '56rem',   // 896px
  240: '60rem',   // 960px
  256: '64rem',   // 1024px
  288: '72rem',   // 1152px
  320: '80rem',   // 1280px
  384: '96rem',   // 1536px
} as const;

// ระยะห่างพิเศษ (Special Spacing)
export const specialSpacing = {
  // ระยะห่างสำหรับ container
  container: {
    padding: '2rem',
    maxWidth: '1400px',
  },
  // ระยะห่างสำหรับ sections
  section: {
    paddingY: '4rem',
    paddingX: '2rem',
  },
  // ระยะห่างสำหรับ cards
  card: {
    padding: '1.5rem',
    gap: '1rem',
  },
  // ระยะห่างสำหรับ form elements
  form: {
    gap: '1rem',
    fieldGap: '0.5rem',
  },
  // ระยะห่างสำหรับ navigation
  nav: {
    height: '4rem',
    paddingX: '1.5rem',
    gap: '1rem',
  },
  // ระยะห่างสำหรับ sidebar
  sidebar: {
    width: '16rem',
    padding: '1rem',
    gap: '0.5rem',
  },
} as const;

// รวมทุกอย่าง
export const spacingTokens = {
  spacing,
  specialSpacing,
} as const;

// ประเภทของระยะห่าง
export type SpacingToken = typeof spacingTokens;
export type SpacingValue = keyof typeof spacing;
export type SpecialSpacingKey = keyof typeof specialSpacing;