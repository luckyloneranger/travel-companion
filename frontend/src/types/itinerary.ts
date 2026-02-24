/**
 * TypeScript interfaces for the Travel Companion API
 * Core types shared across the application.
 */

export type Pace = 'relaxed' | 'moderate' | 'packed';

// ═══════════════════════════════════════════════════════════════
// UI CONSTANTS
// ═══════════════════════════════════════════════════════════════

// Available interest options
export const INTERESTS = [
  { id: 'art', label: 'Art & Museums', icon: '🎨' },
  { id: 'history', label: 'History', icon: '🏛️' },
  { id: 'food', label: 'Food & Dining', icon: '🍽️' },
  { id: 'nature', label: 'Nature', icon: '🌿' },
  { id: 'shopping', label: 'Shopping', icon: '🛍️' },
  { id: 'nightlife', label: 'Nightlife', icon: '🌙' },
  { id: 'architecture', label: 'Architecture', icon: '🏰' },
  { id: 'culture', label: 'Culture', icon: '🎭' },
  { id: 'adventure', label: 'Adventure', icon: '🎢' },
  { id: 'relaxation', label: 'Relaxation', icon: '🧘' },
] as const;
