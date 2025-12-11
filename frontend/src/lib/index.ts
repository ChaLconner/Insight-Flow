// ===========================================
// Library Exports
// ===========================================

// Constants
export * from './constants';

// Utility Functions
export * from './utils';

// API Client
export * from './api-client';
export * from './api-endpoints';

// ===========================================
// Re-export Common Dependencies
// ===========================================

export { clsx } from 'clsx';
export { twMerge } from 'tailwind-merge';

// Date utilities
export { format, formatDistanceToNow, isValid, parseISO } from 'date-fns';

// Animation utilities
export { motion } from 'framer-motion';

// Icon library




// Zustand
export { create } from 'zustand';

// React Hook Form
export { useForm, useController, FormProvider } from 'react-hook-form';

// Zod validation
export { z } from 'zod';

// React Dropzone


// ===========================================
// Glassmorphism Theme Classes
// ===========================================

export const glassClasses = {
  base: 'backdrop-blur-lg bg-white/10 border border-white/20',
  dark: 'backdrop-blur-lg bg-black/10 border border-white/10',
  strong: 'backdrop-blur-xl bg-white/20 border border-white/30',
  subtle: 'backdrop-blur-md bg-white/5 border border-white/10',
  card: 'backdrop-blur-xl bg-gradient-to-br from-white/10 to-white/5 border border-white/20',
  nav: 'backdrop-blur-2xl bg-white/8 border border-white/10',
  modal: 'backdrop-blur-3xl bg-white/15 border border-white/25',
};

export const glassShadows = {
  soft: '0 8px 32px rgba(31, 38, 135, 0.37)',
  inset: 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
  strong: '0 16px 40px rgba(31, 38, 135, 0.5)',
};

export const statusColors = {
  todo: '#64748b',
  inProgress: '#3b82f6',
  inReview: '#f59e0b',
  done: '#22c55e',
  cancelled: '#ef4444',
  low: '#22c55e',
  medium: '#f59e0b',
  high: '#f97316',
  urgent: '#ef4444',
};

export const priorityIcons = {
  low: 'ArrowDown',
  medium: 'Minus',
  high: 'ArrowUp',
  urgent: 'AlertTriangle',
};