/**
 * Shared styles and constants for V6JourneyPlanView components
 */
import {
  MapPin,
  Sparkles,
  Train,
  Plane,
  Bus,
  Car,
  Sun,
  Utensils,
  Camera,
  Star,
} from 'lucide-react';
import type { ReactNode } from 'react';

// City color palette - using inline styles for reliable rendering
export const cityColorPalettes = [
  { 
    gradientFrom: '#7c3aed', gradientTo: '#9333ea', // violet-purple
    bgColor: '#f5f3ff', borderColor: '#ddd6fe', textColor: '#6d28d9', accentColor: '#7c3aed' 
  },
  { 
    gradientFrom: '#059669', gradientTo: '#0d9488', // emerald-teal
    bgColor: '#ecfdf5', borderColor: '#a7f3d0', textColor: '#047857', accentColor: '#059669' 
  },
  { 
    gradientFrom: '#f97316', gradientTo: '#f59e0b', // orange-amber
    bgColor: '#fff7ed', borderColor: '#fed7aa', textColor: '#c2410c', accentColor: '#f97316' 
  },
  { 
    gradientFrom: '#e11d48', gradientTo: '#ec4899', // rose-pink
    bgColor: '#fff1f2', borderColor: '#fecdd3', textColor: '#be123c', accentColor: '#e11d48' 
  },
  { 
    gradientFrom: '#0891b2', gradientTo: '#2563eb', // cyan-blue
    bgColor: '#ecfeff', borderColor: '#a5f3fc', textColor: '#0e7490', accentColor: '#0891b2' 
  },
  { 
    gradientFrom: '#4f46e5', gradientTo: '#7c3aed', // indigo-violet
    bgColor: '#eef2ff', borderColor: '#c7d2fe', textColor: '#4338ca', accentColor: '#4f46e5' 
  },
] as const;

export type CityColorPalette = (typeof cityColorPalettes)[number];

export const transportIcons: Record<string, ReactNode> = {
  flight: <Plane className="h-4 w-4" />,
  train: <Train className="h-4 w-4" />,
  bus: <Bus className="h-4 w-4" />,
  drive: <Car className="h-4 w-4" />,
  car: <Car className="h-4 w-4" />,
};

// Category styling with full color definitions for visual consistency
export const categoryStyles: Record<string, { bg: string; text: string; border: string; accent: string; gradient: string }> = {
  culture: { bg: '#f5f3ff', text: '#7c3aed', border: '#ddd6fe', accent: '#8b5cf6', gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' },
  food: { bg: '#fff7ed', text: '#ea580c', border: '#fed7aa', accent: '#f97316', gradient: 'linear-gradient(135deg, #f97316, #ea580c)' },
  breakfast: { bg: '#fef3c7', text: '#d97706', border: '#fde68a', accent: '#f59e0b', gradient: 'linear-gradient(135deg, #fbbf24, #f59e0b)' },
  lunch: { bg: '#ffedd5', text: '#c2410c', border: '#fed7aa', accent: '#f97316', gradient: 'linear-gradient(135deg, #fb923c, #f97316)' },
  dinner: { bg: '#fce7f3', text: '#be185d', border: '#fbcfe8', accent: '#ec4899', gradient: 'linear-gradient(135deg, #f472b6, #ec4899)' },
  nature: { bg: '#ecfdf5', text: '#059669', border: '#a7f3d0', accent: '#10b981', gradient: 'linear-gradient(135deg, #34d399, #10b981)' },
  history: { bg: '#fef3c7', text: '#b45309', border: '#fde68a', accent: '#f59e0b', gradient: 'linear-gradient(135deg, #fbbf24, #d97706)' },
  shopping: { bg: '#fdf2f8', text: '#db2777', border: '#fbcfe8', accent: '#ec4899', gradient: 'linear-gradient(135deg, #f472b6, #ec4899)' },
  nightlife: { bg: '#eef2ff', text: '#4f46e5', border: '#c7d2fe', accent: '#6366f1', gradient: 'linear-gradient(135deg, #818cf8, #6366f1)' },
  adventure: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca', accent: '#ef4444', gradient: 'linear-gradient(135deg, #f87171, #ef4444)' },
  landmark: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe', accent: '#3b82f6', gradient: 'linear-gradient(135deg, #60a5fa, #3b82f6)' },
  religious: { bg: '#fefce8', text: '#a16207', border: '#fef08a', accent: '#eab308', gradient: 'linear-gradient(135deg, #facc15, #eab308)' },
  museum: { bg: '#f5f3ff', text: '#7c3aed', border: '#ddd6fe', accent: '#8b5cf6', gradient: 'linear-gradient(135deg, #a78bfa, #8b5cf6)' },
  park: { bg: '#ecfdf5', text: '#047857', border: '#a7f3d0', accent: '#10b981', gradient: 'linear-gradient(135deg, #34d399, #059669)' },
  beach: { bg: '#ecfeff', text: '#0891b2', border: '#a5f3fc', accent: '#06b6d4', gradient: 'linear-gradient(135deg, #22d3ee, #06b6d4)' },
  cafe: { bg: '#fef3c7', text: '#92400e', border: '#fde68a', accent: '#d97706', gradient: 'linear-gradient(135deg, #fbbf24, #d97706)' },
  restaurant: { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa', accent: '#f97316', gradient: 'linear-gradient(135deg, #fb923c, #ea580c)' },
  default: { bg: '#f9fafb', text: '#4b5563', border: '#e5e7eb', accent: '#6b7280', gradient: 'linear-gradient(135deg, #9ca3af, #6b7280)' },
};

/** Check if activity is a meal */
export const isMealActivity = (category: string): boolean => {
  const mealCategories = ['breakfast', 'lunch', 'dinner', 'food', 'restaurant', 'cafe'];
  return mealCategories.includes(category?.toLowerCase());
};

/** Get appropriate icon for category */
export const getCategoryIcon = (category: string): ReactNode => {
  const icons: Record<string, ReactNode> = {
    food: <Utensils className="h-3.5 w-3.5" />,
    breakfast: <Sun className="h-3.5 w-3.5" />,
    lunch: <Utensils className="h-3.5 w-3.5" />,
    dinner: <Utensils className="h-3.5 w-3.5" />,
    restaurant: <Utensils className="h-3.5 w-3.5" />,
    cafe: <Utensils className="h-3.5 w-3.5" />,
    nature: <Sun className="h-3.5 w-3.5" />,
    park: <Sun className="h-3.5 w-3.5" />,
    landmark: <Camera className="h-3.5 w-3.5" />,
    museum: <Camera className="h-3.5 w-3.5" />,
    culture: <Star className="h-3.5 w-3.5" />,
    shopping: <Sparkles className="h-3.5 w-3.5" />,
  };
  return icons[category?.toLowerCase()] || <MapPin className="h-3.5 w-3.5" />;
};
