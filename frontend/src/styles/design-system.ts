/**
 * Travel Companion Design System
 * 
 * Centralized design tokens for consistent UI across the application.
 * Based on the Journey UI design language.
 */

// ============================================================================
// COLOR PALETTES
// ============================================================================

/**
 * Primary brand colors - Violet/Purple theme
 */
export const brand = {
  primary: '#7c3aed',      // violet-600
  primaryDark: '#6d28d9',  // violet-700
  primaryLight: '#8b5cf6', // violet-500
  secondary: '#059669',    // emerald-600
  secondaryDark: '#047857',// emerald-700
  accent: '#f97316',       // orange-500
} as const;

/**
 * Semantic colors for UI states
 */
export const semantic = {
  success: { main: '#10b981', light: '#ecfdf5', border: '#a7f3d0', text: '#047857' },
  warning: { main: '#f59e0b', light: '#fef3c7', border: '#fde68a', text: '#b45309' },
  error: { main: '#ef4444', light: '#fef2f2', border: '#fecaca', text: '#dc2626' },
  info: { main: '#3b82f6', light: '#eff6ff', border: '#bfdbfe', text: '#2563eb' },
} as const;

/**
 * Rotating color palettes for cities/days
 * Each palette includes gradient, background, border, text, and accent colors
 */
export const colorPalettes = [
  { 
    name: 'violet',
    gradientFrom: '#7c3aed', 
    gradientTo: '#9333ea',
    bgColor: '#f5f3ff', 
    borderColor: '#ddd6fe', 
    textColor: '#6d28d9', 
    accentColor: '#7c3aed',
  },
  { 
    name: 'emerald',
    gradientFrom: '#059669', 
    gradientTo: '#0d9488',
    bgColor: '#ecfdf5', 
    borderColor: '#a7f3d0', 
    textColor: '#047857', 
    accentColor: '#059669',
  },
  { 
    name: 'orange',
    gradientFrom: '#f97316', 
    gradientTo: '#f59e0b',
    bgColor: '#fff7ed', 
    borderColor: '#fed7aa', 
    textColor: '#c2410c', 
    accentColor: '#f97316',
  },
  { 
    name: 'rose',
    gradientFrom: '#e11d48', 
    gradientTo: '#ec4899',
    bgColor: '#fff1f2', 
    borderColor: '#fecdd3', 
    textColor: '#be123c', 
    accentColor: '#e11d48',
  },
  { 
    name: 'cyan',
    gradientFrom: '#0891b2', 
    gradientTo: '#2563eb',
    bgColor: '#ecfeff', 
    borderColor: '#a5f3fc', 
    textColor: '#0e7490', 
    accentColor: '#0891b2',
  },
  { 
    name: 'indigo',
    gradientFrom: '#4f46e5', 
    gradientTo: '#7c3aed',
    bgColor: '#eef2ff', 
    borderColor: '#c7d2fe', 
    textColor: '#4338ca', 
    accentColor: '#4f46e5',
  },
  { 
    name: 'red',
    gradientFrom: '#dc2626', 
    gradientTo: '#f97316',
    bgColor: '#fef2f2', 
    borderColor: '#fecaca', 
    textColor: '#b91c1c', 
    accentColor: '#dc2626',
  },
] as const;

export type ColorPalette = typeof colorPalettes[number];

/** Get palette by index (wraps around) */
export const getPalette = (index: number): ColorPalette => 
  colorPalettes[index % colorPalettes.length];

/**
 * Light/soft gradient palettes for day plans
 * Uses pastel tones and subtle gradients for a gentler look
 */
export const lightPalettes = [
  { 
    name: 'soft-violet',
    gradientFrom: '#ddd6fe',   // violet-200
    gradientTo: '#e9d5ff',     // purple-200
    headerBg: 'linear-gradient(135deg, #f5f3ff 0%, #faf5ff 100%)',
    textColor: '#6d28d9',      // violet-700
    accentColor: '#7c3aed',    // violet-600
    borderColor: '#c4b5fd',    // violet-300
    iconBg: 'linear-gradient(135deg, #a78bfa, #c084fc)',  // violet-400 to purple-400
  },
  { 
    name: 'soft-emerald',
    gradientFrom: '#a7f3d0',   // emerald-200
    gradientTo: '#99f6e4',     // teal-200
    headerBg: 'linear-gradient(135deg, #ecfdf5 0%, #f0fdfa 100%)',
    textColor: '#047857',      // emerald-700
    accentColor: '#059669',    // emerald-600
    borderColor: '#6ee7b7',    // emerald-300
    iconBg: 'linear-gradient(135deg, #34d399, #2dd4bf)',  // emerald-400 to teal-400
  },
  { 
    name: 'soft-amber',
    gradientFrom: '#fde68a',   // amber-200
    gradientTo: '#fed7aa',     // orange-200
    headerBg: 'linear-gradient(135deg, #fffbeb 0%, #fff7ed 100%)',
    textColor: '#b45309',      // amber-700
    accentColor: '#f59e0b',    // amber-500
    borderColor: '#fcd34d',    // amber-300
    iconBg: 'linear-gradient(135deg, #fbbf24, #fb923c)',  // amber-400 to orange-400
  },
  { 
    name: 'soft-rose',
    gradientFrom: '#fecdd3',   // rose-200
    gradientTo: '#fbcfe8',     // pink-200
    headerBg: 'linear-gradient(135deg, #fff1f2 0%, #fdf2f8 100%)',
    textColor: '#be123c',      // rose-700
    accentColor: '#e11d48',    // rose-600
    borderColor: '#fda4af',    // rose-300
    iconBg: 'linear-gradient(135deg, #fb7185, #f472b6)',  // rose-400 to pink-400
  },
  { 
    name: 'soft-sky',
    gradientFrom: '#bae6fd',   // sky-200
    gradientTo: '#a5f3fc',     // cyan-200
    headerBg: 'linear-gradient(135deg, #f0f9ff 0%, #ecfeff 100%)',
    textColor: '#0369a1',      // sky-700
    accentColor: '#0ea5e9',    // sky-500
    borderColor: '#7dd3fc',    // sky-300
    iconBg: 'linear-gradient(135deg, #38bdf8, #22d3ee)',  // sky-400 to cyan-400
  },
  { 
    name: 'soft-indigo',
    gradientFrom: '#c7d2fe',   // indigo-200
    gradientTo: '#ddd6fe',     // violet-200
    headerBg: 'linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%)',
    textColor: '#4338ca',      // indigo-700
    accentColor: '#6366f1',    // indigo-500
    borderColor: '#a5b4fc',    // indigo-300
    iconBg: 'linear-gradient(135deg, #818cf8, #a78bfa)',  // indigo-400 to violet-400
  },
  { 
    name: 'soft-slate',
    gradientFrom: '#e2e8f0',   // slate-200
    gradientTo: '#e5e7eb',     // gray-200
    headerBg: 'linear-gradient(135deg, #f8fafc 0%, #f9fafb 100%)',
    textColor: '#334155',      // slate-700
    accentColor: '#64748b',    // slate-500
    borderColor: '#cbd5e1',    // slate-300
    iconBg: 'linear-gradient(135deg, #94a3b8, #9ca3af)',  // slate-400 to gray-400
  },
] as const;

export type LightPalette = typeof lightPalettes[number];

/** Get light palette by index (wraps around) */
export const getLightPalette = (index: number): LightPalette => 
  lightPalettes[index % lightPalettes.length];

// ============================================================================
// HEADER GRADIENTS
// ============================================================================

/**
 * Predefined gradients for major UI sections
 */
export const headerGradients = {
  /** Main journey/trip header - violet-purple */
  journey: { 
    from: '#7c3aed', 
    to: '#9333ea',
    css: 'linear-gradient(135deg, #7c3aed, #9333ea)',
  },
  /** Day plans section header - emerald-teal */
  dayPlan: { 
    from: '#059669', 
    to: '#0d9488',
    css: 'linear-gradient(135deg, #059669, #0d9488)',
  },
  /** Statistics/metrics - blue-indigo */
  stats: { 
    from: '#3b82f6', 
    to: '#6366f1',
    css: 'linear-gradient(135deg, #3b82f6, #6366f1)',
  },
  /** Transport/travel - blue gradient */
  transport: {
    from: '#3b82f6',
    to: '#6366f1',
    css: 'linear-gradient(135deg, #3b82f6, #6366f1)',
  },
  /** Interests/features - orange-amber */
  accent: {
    from: '#f97316',
    to: '#f59e0b',
    css: 'linear-gradient(135deg, #f97316, #f59e0b)',
  },
  /** Pace/energy - rose-pink */
  rose: {
    from: '#e11d48',
    to: '#ec4899',
    css: 'linear-gradient(135deg, #e11d48, #ec4899)',
  },
} as const;

// ============================================================================
// CATEGORY STYLES
// ============================================================================

/**
 * Visual styles for activity categories
 * Each has bg (background), text, border, accent, and gradient
 */
export const categoryStyles: Record<string, {
  bg: string;
  text: string;
  border: string;
  accent: string;
  gradient: string;
}> = {
  // Culture & Arts
  culture: { bg: '#f5f3ff', text: '#7c3aed', border: '#ddd6fe', accent: '#8b5cf6', gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' },
  museum: { bg: '#f5f3ff', text: '#7c3aed', border: '#ddd6fe', accent: '#8b5cf6', gradient: 'linear-gradient(135deg, #a78bfa, #8b5cf6)' },
  art: { bg: '#fdf4ff', text: '#a21caf', border: '#f5d0fe', accent: '#d946ef', gradient: 'linear-gradient(135deg, #e879f9, #d946ef)' },
  
  // Food & Dining
  food: { bg: '#fff7ed', text: '#ea580c', border: '#fed7aa', accent: '#f97316', gradient: 'linear-gradient(135deg, #f97316, #ea580c)' },
  breakfast: { bg: '#fef3c7', text: '#d97706', border: '#fde68a', accent: '#f59e0b', gradient: 'linear-gradient(135deg, #fbbf24, #f59e0b)' },
  lunch: { bg: '#ffedd5', text: '#c2410c', border: '#fed7aa', accent: '#f97316', gradient: 'linear-gradient(135deg, #fb923c, #f97316)' },
  dinner: { bg: '#fce7f3', text: '#be185d', border: '#fbcfe8', accent: '#ec4899', gradient: 'linear-gradient(135deg, #f472b6, #ec4899)' },
  restaurant: { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa', accent: '#f97316', gradient: 'linear-gradient(135deg, #fb923c, #ea580c)' },
  cafe: { bg: '#fef3c7', text: '#92400e', border: '#fde68a', accent: '#d97706', gradient: 'linear-gradient(135deg, #fbbf24, #d97706)' },
  
  // Nature & Outdoors
  nature: { bg: '#ecfdf5', text: '#059669', border: '#a7f3d0', accent: '#10b981', gradient: 'linear-gradient(135deg, #34d399, #10b981)' },
  park: { bg: '#ecfdf5', text: '#047857', border: '#a7f3d0', accent: '#10b981', gradient: 'linear-gradient(135deg, #34d399, #059669)' },
  beach: { bg: '#ecfeff', text: '#0891b2', border: '#a5f3fc', accent: '#06b6d4', gradient: 'linear-gradient(135deg, #22d3ee, #06b6d4)' },
  
  // History & Architecture  
  history: { bg: '#fef3c7', text: '#b45309', border: '#fde68a', accent: '#f59e0b', gradient: 'linear-gradient(135deg, #fbbf24, #d97706)' },
  landmark: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe', accent: '#3b82f6', gradient: 'linear-gradient(135deg, #60a5fa, #3b82f6)' },
  architecture: { bg: '#f0fdf4', text: '#166534', border: '#bbf7d0', accent: '#22c55e', gradient: 'linear-gradient(135deg, #4ade80, #22c55e)' },
  religious: { bg: '#fefce8', text: '#a16207', border: '#fef08a', accent: '#eab308', gradient: 'linear-gradient(135deg, #facc15, #eab308)' },
  
  // Entertainment & Lifestyle
  shopping: { bg: '#fdf2f8', text: '#db2777', border: '#fbcfe8', accent: '#ec4899', gradient: 'linear-gradient(135deg, #f472b6, #ec4899)' },
  nightlife: { bg: '#eef2ff', text: '#4f46e5', border: '#c7d2fe', accent: '#6366f1', gradient: 'linear-gradient(135deg, #818cf8, #6366f1)' },
  adventure: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca', accent: '#ef4444', gradient: 'linear-gradient(135deg, #f87171, #ef4444)' },
  relaxation: { bg: '#f0f9ff', text: '#0369a1', border: '#bae6fd', accent: '#0ea5e9', gradient: 'linear-gradient(135deg, #38bdf8, #0ea5e9)' },
  entertainment: { bg: '#fdf4ff', text: '#a21caf', border: '#f5d0fe', accent: '#d946ef', gradient: 'linear-gradient(135deg, #e879f9, #d946ef)' },
  
  // Default fallback
  default: { bg: '#f9fafb', text: '#4b5563', border: '#e5e7eb', accent: '#6b7280', gradient: 'linear-gradient(135deg, #9ca3af, #6b7280)' },
};

/** Get category style with fallback to default */
export const getCategoryStyle = (category: string) => 
  categoryStyles[category?.toLowerCase()] || categoryStyles.default;

/** Check if activity is a meal */
export const isMealCategory = (category: string): boolean => {
  const mealCategories = ['breakfast', 'lunch', 'dinner', 'food', 'restaurant', 'cafe'];
  return mealCategories.includes(category?.toLowerCase());
};

// ============================================================================
// SHADOWS
// ============================================================================

/**
 * Shadow scale for consistent elevation
 */
export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
} as const;

// ============================================================================
// CARD STYLES
// ============================================================================

/**
 * Card style presets for consistent look across components
 */
export const cardStyles = {
  /** Base card - white bg, subtle border, rounded */
  base: {
    className: 'bg-white rounded-xl border border-gray-100',
    shadow: 'shadow-sm',
    hoverShadow: 'hover:shadow-md',
  },
  /** Elevated card - more shadow, rounded 2xl */
  elevated: {
    className: 'bg-white rounded-2xl',
    shadow: 'shadow-md',
    hoverShadow: 'hover:shadow-lg',
  },
  /** Featured card - for headers, prominent sections */
  featured: {
    className: 'bg-white rounded-2xl overflow-hidden',
    shadow: 'shadow-lg',
    hoverShadow: 'hover:shadow-xl',
  },
  /** Interactive card - for clickable items */
  interactive: {
    className: 'bg-white rounded-xl border border-gray-100 cursor-pointer transition-all duration-200',
    shadow: 'shadow-md',
    hoverShadow: 'hover:shadow-lg hover:border-gray-200',
  },
} as const;

// ============================================================================
// BUTTON STYLES
// ============================================================================

/**
 * Button variants with colors and states
 */
export const buttonStyles = {
  primary: {
    base: 'bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold',
    hover: 'hover:from-violet-700 hover:to-purple-700',
    disabled: 'disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed',
    shadow: 'shadow-md hover:shadow-lg',
  },
  secondary: {
    base: 'bg-white text-gray-700 font-semibold border border-gray-300',
    hover: 'hover:bg-gray-50 hover:border-gray-400',
    disabled: 'disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed',
    shadow: 'shadow-sm hover:shadow',
  },
  ghost: {
    base: 'bg-transparent text-gray-600 font-medium',
    hover: 'hover:bg-gray-100 hover:text-gray-900',
    disabled: 'disabled:text-gray-300 disabled:cursor-not-allowed',
    shadow: '',
  },
  accent: {
    base: 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-semibold',
    hover: 'hover:from-emerald-700 hover:to-teal-700',
    disabled: 'disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed',
    shadow: 'shadow-md hover:shadow-lg',
  },
} as const;

// ============================================================================
// SPACING & SIZING
// ============================================================================

/**
 * Consistent spacing for padding/margins
 */
export const spacing = {
  card: {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-5',
    xl: 'p-6',
  },
  section: {
    sm: 'py-4',
    md: 'py-6',
    lg: 'py-8',
  },
  gap: {
    xs: 'gap-1',
    sm: 'gap-2',
    md: 'gap-3',
    lg: 'gap-4',
    xl: 'gap-6',
  },
} as const;

/**
 * Badge/number indicator sizes
 */
export const badgeSizes = {
  sm: 'w-6 h-6 text-xs',
  md: 'w-8 h-8 text-sm',
  lg: 'w-11 h-11 text-lg',
  xl: 'w-14 h-14 text-2xl',
} as const;

// ============================================================================
// TYPOGRAPHY
// ============================================================================

/**
 * Text styles for consistent typography
 */
export const textStyles = {
  heading: {
    xl: 'text-2xl font-bold text-gray-900',
    lg: 'text-xl font-bold text-gray-900',
    md: 'text-lg font-semibold text-gray-900',
    sm: 'text-base font-semibold text-gray-900',
  },
  body: {
    lg: 'text-base text-gray-700',
    md: 'text-sm text-gray-600',
    sm: 'text-xs text-gray-500',
  },
  label: {
    lg: 'text-sm font-medium text-gray-700',
    md: 'text-xs font-medium text-gray-600',
    sm: 'text-xs font-medium text-gray-500 uppercase tracking-wide',
  },
} as const;

// ============================================================================
// GLASS MORPHISM
// ============================================================================

/**
 * Glass effect styles for overlays on gradients
 */
export const glass = {
  light: {
    bg: 'rgba(255, 255, 255, 0.15)',
    backdrop: 'blur(10px)',
    border: 'rgba(255, 255, 255, 0.2)',
  },
  medium: {
    bg: 'rgba(255, 255, 255, 0.25)',
    backdrop: 'blur(10px)',
    border: 'rgba(255, 255, 255, 0.3)',
  },
  dark: {
    bg: 'rgba(0, 0, 0, 0.1)',
    backdrop: 'blur(10px)',
    border: 'rgba(0, 0, 0, 0.1)',
  },
} as const;

// ============================================================================
// TRANSITIONS
// ============================================================================

/**
 * Consistent transition durations
 */
export const transitions = {
  fast: 'transition-all duration-150',
  normal: 'transition-all duration-200',
  slow: 'transition-all duration-300',
} as const;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Build a gradient CSS string from palette
 */
export const buildGradient = (palette: ColorPalette, direction = '135deg'): string =>
  `linear-gradient(${direction}, ${palette.gradientFrom}, ${palette.gradientTo})`;

/**
 * Build inline style for a gradient header
 */
export const gradientStyle = (gradient: { from: string; to: string }, direction = 'to right') => ({
  background: `linear-gradient(${direction}, ${gradient.from}, ${gradient.to})`,
});

/**
 * Build glass morphism style object
 */
export const glassStyle = (variant: keyof typeof glass = 'medium') => ({
  backgroundColor: glass[variant].bg,
  backdropFilter: glass[variant].backdrop,
});
