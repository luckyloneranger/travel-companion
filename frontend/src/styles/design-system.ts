/**
 * Travel Companion Design System
 *
 * Centralized design tokens for consistent UI across the application.
 * Based on the Journey UI design language with modern, warm aesthetics.
 */

// ============================================================================
// COLOR PALETTES
// ============================================================================

/**
 * Primary brand colors - Earth-tone theme
 */
export const brand = {
  primary: '#C97B5A',
  primaryDark: '#A66244',
  primaryLight: '#D4956F',
  secondary: '#8B9E6B',
  secondaryDark: '#728556',
  accent: '#D4A574',
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
    name: 'terracotta',
    gradientFrom: '#C97B5A',
    gradientTo: '#D4956F',
    bgColor: '#FCF8F5',
    borderColor: '#EDCDB8',
    textColor: '#A66244',
    accentColor: '#C97B5A',
  },
  {
    name: 'sage',
    gradientFrom: '#8B9E6B',
    gradientTo: '#A3B584',
    bgColor: '#F5F7F0',
    borderColor: '#C5D4AB',
    textColor: '#728556',
    accentColor: '#8B9E6B',
  },
  {
    name: 'sand',
    gradientFrom: '#D4A574',
    gradientTo: '#E0BB91',
    bgColor: '#FDF8F3',
    borderColor: '#E8D4BC',
    textColor: '#B8884F',
    accentColor: '#D4A574',
  },
  {
    name: 'clay',
    gradientFrom: '#B07878',
    gradientTo: '#C4918F',
    bgColor: '#FBF5F5',
    borderColor: '#DAC0C0',
    textColor: '#96615F',
    accentColor: '#B07878',
  },
  {
    name: 'stone',
    gradientFrom: '#8E8478',
    gradientTo: '#A39A8F',
    bgColor: '#F7F5F2',
    borderColor: '#D4CEC7',
    textColor: '#6E655B',
    accentColor: '#8E8478',
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
    name: 'soft-terracotta',
    gradientFrom: '#EDCDB8',
    gradientTo: '#F0D5C2',
    headerBg: 'linear-gradient(135deg, #FCF8F5 0%, #FDF5EF 100%)',
    textColor: '#A66244',
    accentColor: '#C97B5A',
    borderColor: '#E0B89E',
    iconBg: 'linear-gradient(135deg, #C97B5A, #D4956F)',
  },
  {
    name: 'soft-sage',
    gradientFrom: '#C5D4AB',
    gradientTo: '#D0DDB8',
    headerBg: 'linear-gradient(135deg, #F5F7F0 0%, #F0F4E8 100%)',
    textColor: '#728556',
    accentColor: '#8B9E6B',
    borderColor: '#B5C89A',
    iconBg: 'linear-gradient(135deg, #8B9E6B, #A3B584)',
  },
  {
    name: 'soft-sand',
    gradientFrom: '#E8D4BC',
    gradientTo: '#EDDCC8',
    headerBg: 'linear-gradient(135deg, #FDF8F3 0%, #FBF3EA 100%)',
    textColor: '#B8884F',
    accentColor: '#D4A574',
    borderColor: '#DEC8AE',
    iconBg: 'linear-gradient(135deg, #D4A574, #E0BB91)',
  },
  {
    name: 'soft-clay',
    gradientFrom: '#DAC0C0',
    gradientTo: '#E0CACA',
    headerBg: 'linear-gradient(135deg, #FBF5F5 0%, #F9F0F0 100%)',
    textColor: '#96615F',
    accentColor: '#B07878',
    borderColor: '#D0B2B2',
    iconBg: 'linear-gradient(135deg, #B07878, #C4918F)',
  },
  {
    name: 'soft-stone',
    gradientFrom: '#D4CEC7',
    gradientTo: '#DCD7D0',
    headerBg: 'linear-gradient(135deg, #F7F5F2 0%, #F3F0EC 100%)',
    textColor: '#6E655B',
    accentColor: '#8E8478',
    borderColor: '#C8C0B8',
    iconBg: 'linear-gradient(135deg, #8E8478, #A39A8F)',
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
  /** Main journey/trip header - terracotta */
  journey: {
    from: '#C97B5A',
    to: '#D4956F',
    css: 'linear-gradient(135deg, #C97B5A, #D4956F)',
  },
  /** Day plans section header - sage green */
  dayPlan: {
    from: '#8B9E6B',
    to: '#A3B584',
    css: 'linear-gradient(135deg, #8B9E6B, #A3B584)',
  },
  /** Statistics/metrics - stone */
  stats: {
    from: '#8E8478',
    to: '#A39A8F',
    css: 'linear-gradient(135deg, #8E8478, #A39A8F)',
  },
  /** Transport/travel - sand */
  transport: {
    from: '#D4A574',
    to: '#B8884F',
    css: 'linear-gradient(135deg, #D4A574, #B8884F)',
  },
  /** Interests/features - warm sand */
  accent: {
    from: '#D4A574',
    to: '#E0BB91',
    css: 'linear-gradient(135deg, #D4A574, #E0BB91)',
  },
  /** Pace/energy - clay */
  rose: {
    from: '#B07878',
    to: '#C4918F',
    css: 'linear-gradient(135deg, #B07878, #C4918F)',
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
  culture: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  museum: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  art: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },

  // Food & Dining
  food: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },
  breakfast: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },
  lunch: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  dinner: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },
  restaurant: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },
  cafe: { bg: '#FDF8F3', text: '#8E7656', border: '#E0D4C2', accent: '#B8975E', gradient: 'linear-gradient(135deg, #B8975E, #8E7656)' },

  // Nature & Outdoors
  nature: { bg: '#F5F7F0', text: '#728556', border: '#C5D4AB', accent: '#8B9E6B', gradient: 'linear-gradient(135deg, #8B9E6B, #728556)' },
  park: { bg: '#F5F7F0', text: '#728556', border: '#C5D4AB', accent: '#8B9E6B', gradient: 'linear-gradient(135deg, #8B9E6B, #728556)' },
  beach: { bg: '#F5F7F2', text: '#6B8A6B', border: '#B8D4B8', accent: '#7BA37B', gradient: 'linear-gradient(135deg, #7BA37B, #6B8A6B)' },

  // History & Architecture
  history: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
  landmark: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  architecture: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
  religious: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },

  // Entertainment & Lifestyle
  shopping: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },
  nightlife: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
  adventure: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  relaxation: { bg: '#F5F7F0', text: '#728556', border: '#C5D4AB', accent: '#8B9E6B', gradient: 'linear-gradient(135deg, #8B9E6B, #728556)' },
  entertainment: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },

  // Default fallback
  default: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
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
// SHADOWS — warm, modern, with depth
// ============================================================================

/**
 * Shadow scale with warm tones for elegant depth
 */
export const shadows = {
  none: 'none',
  xs: '0 1px 2px rgba(61, 50, 41, 0.04)',
  sm: '0 1px 3px rgba(61, 50, 41, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
  md: '0 4px 12px rgba(61, 50, 41, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
  lg: '0 8px 24px rgba(61, 50, 41, 0.1), 0 4px 8px rgba(0, 0, 0, 0.04)',
  xl: '0 16px 40px rgba(61, 50, 41, 0.12), 0 8px 16px rgba(0, 0, 0, 0.04)',
  /** Focus ring shadow */
  ring: '0 0 0 3px rgba(201, 123, 90, 0.15)',
  /** Glow effect for CTAs */
  glow: '0 8px 32px rgba(201, 123, 90, 0.2)',
} as const;

// ============================================================================
// CARD STYLES
// ============================================================================

/**
 * Card style presets for consistent look across components
 */
export const cardStyles = {
  /** Base card - soft background, subtle border */
  base: {
    className: 'bg-white rounded-2xl border border-gray-100/80',
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
    className: 'bg-white rounded-2xl border border-gray-100/80 cursor-pointer transition-all duration-300 ease-out',
    shadow: 'shadow-sm',
    hoverShadow: 'hover:shadow-lg hover:border-primary-200 hover:-translate-y-0.5',
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
    base: 'bg-primary-600 text-white font-semibold',
    hover: 'hover:bg-primary-700 hover:-translate-y-0.5',
    disabled: 'disabled:bg-gray-300 disabled:cursor-not-allowed disabled:translate-y-0',
    shadow: 'shadow-md hover:shadow-lg',
  },
  secondary: {
    base: 'bg-white text-gray-700 font-semibold border border-[#E8E0D4]',
    hover: 'hover:bg-[#F5F0E8] hover:border-[#D4CEC7] hover:-translate-y-0.5',
    disabled: 'disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed',
    shadow: 'shadow-sm hover:shadow',
  },
  ghost: {
    base: 'bg-transparent text-[#3D3229] font-medium',
    hover: 'hover:bg-[#F5F0E8] hover:text-gray-900',
    disabled: 'disabled:text-gray-300 disabled:cursor-not-allowed',
    shadow: '',
  },
  accent: {
    base: 'bg-[#8B9E6B] text-white font-semibold',
    hover: 'hover:bg-[#728556] hover:-translate-y-0.5',
    disabled: 'disabled:bg-gray-300 disabled:cursor-not-allowed',
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
    xl: 'font-display text-2xl font-bold text-gray-900',
    lg: 'font-display text-xl font-bold text-gray-900',
    md: 'font-display text-lg font-semibold text-gray-900',
    sm: 'font-display text-base font-semibold text-gray-900',
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
// TRANSITIONS
// ============================================================================

/**
 * Consistent transition durations
 */
export const transitions = {
  fast: 'transition-all duration-150 ease-out',
  normal: 'transition-all duration-200 ease-out',
  slow: 'transition-all duration-300 ease-out',
  spring: 'transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
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
