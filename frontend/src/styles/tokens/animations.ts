/**
 * Insight Flow Design Tokens - Animations
 * ระบบแอนิเมชันที่ใช้ในโปรเจกต์ Insight Flow
 */

// ระยะเวลาของแอนิเมชัน (Animation Durations)
export const durations = {
  instant: '0ms',
  fast: '150ms',
  normal: '300ms',
  slow: '500ms',
  slower: '750ms',
  slowest: '1000ms',
} as const;

// ฟังก์ชัน Timing สำหรับแอนิเมชัน (Timing Functions)
export const timingFunctions = {
  linear: 'linear',
  ease: 'ease',
  easeIn: 'ease-in',
  easeOut: 'ease-out',
  easeInOut: 'ease-in-out',
  // Custom timing functions
  easeOutCubic: 'cubic-bezier(0.215, 0.61, 0.355, 1)',
  easeInCubic: 'cubic-bezier(0.55, 0.055, 0.675, 0.19)',
  easeInOutCubic: 'cubic-bezier(0.645, 0.045, 0.355, 1)',
  easeOutQuart: 'cubic-bezier(0.165, 0.84, 0.44, 1)',
  easeInQuart: 'cubic-bezier(0.895, 0.03, 0.685, 0.22)',
  easeInOutQuart: 'cubic-bezier(0.77, 0, 0.175, 1)',
  easeOutQuint: 'cubic-bezier(0.23, 1, 0.32, 1)',
  easeInQuint: 'cubic-bezier(0.755, 0.05, 0.855, 0.06)',
  easeInOutQuint: 'cubic-bezier(0.86, 0, 0.07, 1)',
  easeOutSine: 'cubic-bezier(0.39, 0.575, 0.565, 1)',
  easeInSine: 'cubic-bezier(0.47, 0, 0.745, 0.715)',
  easeInOutSine: 'cubic-bezier(0.445, 0.05, 0.55, 0.95)',
  easeOutBack: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  easeInBack: 'cubic-bezier(0.6, -0.28, 0.735, 0.045)',
  easeInOutBack: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  easeOutCirc: 'cubic-bezier(0.075, 0.82, 0.165, 1)',
  easeInCirc: 'cubic-bezier(0.6, 0.04, 0.98, 0.335)',
  easeInOutCirc: 'cubic-bezier(0.785, 0.135, 0.15, 0.86)',
  easeOutExpo: 'cubic-bezier(0.19, 1, 0.22, 1)',
  easeInExpo: 'cubic-bezier(0.95, 0.05, 0.795, 0.035)',
  easeInOutExpo: 'cubic-bezier(1, 0, 0, 1)',
} as const;

// Keyframes สำหรับแอนิเมชัน (Animation Keyframes)
export const keyframes = {
  // Fade animations
  fadeIn: {
    '0%': { opacity: '0' },
    '100%': { opacity: '1' },
  },
  fadeOut: {
    '0%': { opacity: '1' },
    '100%': { opacity: '0' },
  },
  fadeInUp: {
    '0%': { opacity: '0', transform: 'translateY(20px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  },
  fadeInDown: {
    '0%': { opacity: '0', transform: 'translateY(-20px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  },
  fadeInLeft: {
    '0%': { opacity: '0', transform: 'translateX(-20px)' },
    '100%': { opacity: '1', transform: 'translateX(0)' },
  },
  fadeInRight: {
    '0%': { opacity: '0', transform: 'translateX(20px)' },
    '100%': { opacity: '1', transform: 'translateX(0)' },
  },
  fadeOutUp: {
    '0%': { opacity: '1', transform: 'translateY(0)' },
    '100%': { opacity: '0', transform: 'translateY(-20px)' },
  },
  fadeOutDown: {
    '0%': { opacity: '1', transform: 'translateY(0)' },
    '100%': { opacity: '0', transform: 'translateY(20px)' },
  },
  fadeOutLeft: {
    '0%': { opacity: '1', transform: 'translateX(0)' },
    '100%': { opacity: '0', transform: 'translateX(-20px)' },
  },
  fadeOutRight: {
    '0%': { opacity: '1', transform: 'translateX(0)' },
    '100%': { opacity: '0', transform: 'translateX(20px)' },
  },

  // Slide animations
  slideInUp: {
    '0%': { transform: 'translateY(100%)' },
    '100%': { transform: 'translateY(0)' },
  },
  slideInDown: {
    '0%': { transform: 'translateY(-100%)' },
    '100%': { transform: 'translateY(0)' },
  },
  slideInLeft: {
    '0%': { transform: 'translateX(-100%)' },
    '100%': { transform: 'translateX(0)' },
  },
  slideInRight: {
    '0%': { transform: 'translateX(100%)' },
    '100%': { transform: 'translateX(0)' },
  },
  slideOutUp: {
    '0%': { transform: 'translateY(0)' },
    '100%': { transform: 'translateY(-100%)' },
  },
  slideOutDown: {
    '0%': { transform: 'translateY(0)' },
    '100%': { transform: 'translateY(100%)' },
  },
  slideOutLeft: {
    '0%': { transform: 'translateX(0)' },
    '100%': { transform: 'translateX(-100%)' },
  },
  slideOutRight: {
    '0%': { transform: 'translateX(0)' },
    '100%': { transform: 'translateX(100%)' },
  },

  // Scale animations
  scaleIn: {
    '0%': { opacity: '0', transform: 'scale(0.9)' },
    '100%': { opacity: '1', transform: 'scale(1)' },
  },
  scaleOut: {
    '0%': { opacity: '1', transform: 'scale(1)' },
    '100%': { opacity: '0', transform: 'scale(0.9)' },
  },
  scaleInCenter: {
    '0%': { opacity: '0', transform: 'scale(0)' },
    '100%': { opacity: '1', transform: 'scale(1)' },
  },
  scaleOutCenter: {
    '0%': { opacity: '1', transform: 'scale(1)' },
    '100%': { opacity: '0', transform: 'scale(0)' },
  },

  // Rotate animations
  rotateIn: {
    '0%': { opacity: '0', transform: 'rotate(-200deg)' },
    '100%': { opacity: '1', transform: 'rotate(0deg)' },
  },
  rotateOut: {
    '0%': { opacity: '1', transform: 'rotate(0deg)' },
    '100%': { opacity: '0', transform: 'rotate(200deg)' },
  },

  // Bounce animations
  bounce: {
    '0%, 20%, 53%, 80%, 100%': { transform: 'translate3d(0, 0, 0)' },
    '40%, 43%': { transform: 'translate3d(0, -30px, 0)' },
    '70%': { transform: 'translate3d(0, -15px, 0)' },
    '90%': { transform: 'translate3d(0, -4px, 0)' },
  },
  bounceIn: {
    '0%': { opacity: '0', transform: 'scale(0.3)' },
    '50%': { opacity: '1', transform: 'scale(1.05)' },
    '70%': { transform: 'scale(0.9)' },
    '100%': { opacity: '1', transform: 'scale(1)' },
  },
  bounceOut: {
    '0%': { transform: 'scale(1)' },
    '20%': { transform: 'scale(0.9)' },
    '50%': { opacity: '1', transform: 'scale(1.1)' },
    '100%': { opacity: '0', transform: 'scale(0.3)' },
  },

  // Pulse animations
  pulse: {
    '0%': { transform: 'scale(1)' },
    '50%': { transform: 'scale(1.05)' },
    '100%': { transform: 'scale(1)' },
  },
  pulseGlow: {
    '0%': { boxShadow: '0 0 0 0 rgba(59, 130, 246, 0.7)' },
    '70%': { boxShadow: '0 0 0 10px rgba(59, 130, 246, 0)' },
    '100%': { boxShadow: '0 0 0 0 rgba(59, 130, 246, 0)' },
  },

  // Shake animations
  shake: {
    '0%, 100%': { transform: 'translateX(0)' },
    '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-10px)' },
    '20%, 40%, 60%, 80%': { transform: 'translateX(10px)' },
  },
  shakeX: {
    '0%, 100%': { transform: 'translateX(0)' },
    '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-2px)' },
    '20%, 40%, 60%, 80%': { transform: 'translateX(2px)' },
  },
  shakeY: {
    '0%, 100%': { transform: 'translateY(0)' },
    '10%, 30%, 50%, 70%, 90%': { transform: 'translateY(-2px)' },
    '20%, 40%, 60%, 80%': { transform: 'translateY(2px)' },
  },

  // Loading animations
  spin: {
    '0%': { transform: 'rotate(0deg)' },
    '100%': { transform: 'rotate(360deg)' },
  },
  ping: {
    '0%': { transform: 'scale(1)', opacity: '1' },
    '75%, 100%': { transform: 'scale(2)', opacity: '0' },
  },
  shimmer: {
    '0%': { transform: 'translateX(-100%)' },
    '100%': { transform: 'translateX(100%)' },
  },
  wave: {
    '0%': { transform: 'rotate(0deg)' },
    '10%': { transform: 'rotate(14deg)' },
    '20%': { transform: 'rotate(-8deg)' },
    '30%': { transform: 'rotate(14deg)' },
    '40%': { transform: 'rotate(-4deg)' },
    '50%': { transform: 'rotate(10deg)' },
    '60%': { transform: 'rotate(0deg)' },
    '100%': { transform: 'rotate(0deg)' },
  },

  // Special animations
  float: {
    '0%, 100%': { transform: 'translateY(0px)' },
    '50%': { transform: 'translateY(-10px)' },
  },
  glow: {
    '0%, 100%': { boxShadow: '0 0 5px rgba(59, 130, 246, 0.5)' },
    '50%': { boxShadow: '0 0 20px rgba(59, 130, 246, 0.8)' },
  },
  heartbeat: {
    '0%': { transform: 'scale(1)' },
    '14%': { transform: 'scale(1.3)' },
    '28%': { transform: 'scale(1)' },
    '42%': { transform: 'scale(1.3)' },
    '70%': { transform: 'scale(1)' },
  },
  wobble: {
    '0%': { transform: 'translateX(0%)' },
    '15%': { transform: 'translateX(-25%) rotate(-5deg)' },
    '30%': { transform: 'translateX(20%) rotate(3deg)' },
    '45%': { transform: 'translateX(-15%) rotate(-3deg)' },
    '60%': { transform: 'translateX(10%) rotate(2deg)' },
    '75%': { transform: 'translateX(-5%) rotate(-1deg)' },
    '100%': { transform: 'translateX(0%)' },
  },

  // Accordion animations
  accordionDown: {
    from: { height: '0' },
    to: { height: 'var(--radix-accordion-content-height)' },
  },
  accordionUp: {
    from: { height: 'var(--radix-accordion-content-height)' },
    to: { height: '0' },
  },

  // Progress animations
  progress: {
    '0%': { transform: 'translateX(-100%)' },
    '100%': { transform: 'translateX(0%)' },
  },
  progressCircular: {
    '0%': { transform: 'rotate(0deg)' },
    '100%': { transform: 'rotate(360deg)' },
  },
} as const;

// การตั้งค่าแอนิเมชันแบบสำเร็จ (Animation Presets)
export const animationPresets = {
  // Entry animations
  entry: {
    fadeIn: 'fadeIn 0.3s ease-out',
    fadeInUp: 'fadeInUp 0.3s ease-out',
    fadeInDown: 'fadeInDown 0.3s ease-out',
    fadeInLeft: 'fadeInLeft 0.3s ease-out',
    fadeInRight: 'fadeInRight 0.3s ease-out',
    slideInUp: 'slideInUp 0.3s ease-out',
    slideInDown: 'slideInDown 0.3s ease-out',
    slideInLeft: 'slideInLeft 0.3s ease-out',
    slideInRight: 'slideInRight 0.3s ease-out',
    scaleIn: 'scaleIn 0.2s ease-out',
    bounceIn: 'bounceIn 0.6s ease-out',
  },

  // Exit animations
  exit: {
    fadeOut: 'fadeOut 0.3s ease-in',
    fadeOutUp: 'fadeOutUp 0.3s ease-in',
    fadeOutDown: 'fadeOutDown 0.3s ease-in',
    fadeOutLeft: 'fadeOutLeft 0.3s ease-in',
    fadeOutRight: 'fadeOutRight 0.3s ease-in',
    slideOutUp: 'slideOutUp 0.3s ease-in',
    slideOutDown: 'slideOutDown 0.3s ease-in',
    slideOutLeft: 'slideOutLeft 0.3s ease-in',
    slideOutRight: 'slideOutRight 0.3s ease-in',
    scaleOut: 'scaleOut 0.2s ease-in',
    bounceOut: 'bounceOut 0.6s ease-in',
  },

  // Attention animations
  attention: {
    bounce: 'bounce 1s ease-in-out infinite',
    pulse: 'pulse 2s ease-in-out infinite',
    shake: 'shake 0.5s ease-in-out',
    shakeX: 'shakeX 0.5s ease-in-out',
    shakeY: 'shakeY 0.5s ease-in-out',
    heartbeat: 'heartbeat 1.3s ease-in-out infinite',
    wobble: 'wobble 1s ease-in-out',
    glow: 'glow 2s ease-in-out infinite',
    float: 'float 3s ease-in-out infinite',
  },

  // Loading animations
  loading: {
    spin: 'spin 1s linear infinite',
    ping: 'ping 1s cubic-bezier(0, 0, 0.2, 1) infinite',
    shimmer: 'shimmer 1.5s ease-in-out infinite',
    wave: 'wave 2s linear infinite',
    progress: 'progress 2s ease-in-out infinite',
    progressCircular: 'progressCircular 1s linear infinite',
  },

  // Interactive animations
  interactive: {
    hover: 'scaleIn 0.2s ease-out',
    active: 'scaleOut 0.1s ease-in',
    focus: 'glow 0.3s ease-out',
  },

  // Component animations
  component: {
    accordionDown: 'accordionDown 0.2s ease-out',
    accordionUp: 'accordionUp 0.2s ease-out',
    modal: 'fadeIn 0.3s ease-out, scaleIn 0.2s ease-out',
    dropdown: 'fadeInDown 0.2s ease-out',
    tooltip: 'fadeIn 0.2s ease-out',
    notification: 'slideInRight 0.3s ease-out',
  },
} as const;

// การตั้งค่าการเปลี่ยนแปลง (Transition Presets)
export const transitionPresets = {
  // Basic transitions
  basic: {
    all: 'all 0.3s ease',
    colors: 'color 0.3s ease, background-color 0.3s ease, border-color 0.3s ease',
    opacity: 'opacity 0.3s ease',
    transform: 'transform 0.3s ease',
    shadow: 'box-shadow 0.3s ease',
  },

  // Fast transitions
  fast: {
    all: 'all 0.15s ease',
    colors: 'color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease',
    opacity: 'opacity 0.15s ease',
    transform: 'transform 0.15s ease',
    shadow: 'box-shadow 0.15s ease',
  },

  // Slow transitions
  slow: {
    all: 'all 0.5s ease',
    colors: 'color 0.5s ease, background-color 0.5s ease, border-color 0.5s ease',
    opacity: 'opacity 0.5s ease',
    transform: 'transform 0.5s ease',
    shadow: 'box-shadow 0.5s ease',
  },

  // Component-specific transitions
  button: {
    default: 'all 0.2s ease',
    hover: 'transform 0.2s ease, box-shadow 0.2s ease',
    active: 'transform 0.1s ease',
  },
  input: {
    default: 'border-color 0.2s ease, box-shadow 0.2s ease',
    focus: 'border-color 0.2s ease, box-shadow 0.2s ease',
  },
  modal: {
    enter: 'opacity 0.3s ease, transform 0.3s ease',
    exit: 'opacity 0.2s ease, transform 0.2s ease',
  },
  dropdown: {
    enter: 'opacity 0.2s ease, transform 0.2s ease',
    exit: 'opacity 0.15s ease, transform 0.15s ease',
  },
  tooltip: {
    enter: 'opacity 0.2s ease, transform 0.2s ease',
    exit: 'opacity 0.15s ease, transform 0.15s ease',
  },
} as const;

// รวมทุกอย่าง
export const animations = {
  durations,
  timingFunctions,
  keyframes,
  animationPresets,
  transitionPresets,
} as const;

// ประเภทของแอนิเมชัน
export type AnimationToken = typeof animations;
export type Duration = keyof typeof durations;
export type TimingFunction = keyof typeof timingFunctions;
export type KeyframeName = keyof typeof keyframes;
export type AnimationPresetCategory = keyof typeof animationPresets;
export type TransitionPresetCategory = keyof typeof transitionPresets;